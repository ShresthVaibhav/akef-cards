import pytest
from PIL import Image

import akef_cards


async def test_art_download_error(monkeypatch):
    from akef_cards import images

    monkeypatch.setattr(images, "_is_public", lambda host: True)
    with pytest.raises(akef_cards.CardError, match="pass the bytes"):
        await images.load_art("http://127.0.0.1:9/art.png", allow_remote=True)


async def test_art_opt_in(tmp_path):
    from akef_cards.images import load_art

    file = tmp_path / "art.png"
    Image.new("RGBA", (4, 4)).save(file)
    with pytest.raises(akef_cards.CardError, match="allow_local"):
        await load_art(str(file))
    with pytest.raises(akef_cards.CardError, match="allow_remote"):
        await load_art("HTTPS://example.com/art.png")
    with pytest.raises(akef_cards.CardError, match="allow_local"):
        await load_art(str(file), allow_remote=True)
    for art in (file, file.read_bytes()):
        assert (await load_art(art)).size == (4, 4)
    assert (await load_art(str(file), allow_local=True)).size == (4, 4)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/a.png", "http://localhost/a.png", "http://2130706433/a.png", "http://10.0.0.1/a.png",
    "http://192.168.1.1/a.png", "http://169.254.169.254/latest", "http://0.0.0.0/a.png",
    "http://[::1]/a.png", "http://[::ffff:127.0.0.1]/a.png",
])
async def test_art_private_ips(url):
    from akef_cards.images import load_art

    with pytest.raises(akef_cards.CardError, match="private address|InvalidUrl"):
        await load_art(url, allow_remote=True)


async def test_art_redirects_n_size(monkeypatch):
    from aiohttp import web
    from akef_cards import images

    async def hop(request):
        raise web.HTTPFound("http://10.0.0.1/secret.png")

    async def loop(request):
        raise web.HTTPFound("/loop")

    async def huge(request):
        return web.Response(body=b"x" * 2048)

    async def text(request):
        return web.Response(body=b"not a pic")

    app = web.Application()
    for route in (hop, loop, huge, text):
        app.router.add_get(f"/{route.__name__}", route)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 0).start()
    base = f"http://127.0.0.1:{runner.addresses[0][1]}"
    real = images._is_public
    monkeypatch.setattr(images, "_is_public", lambda host: host == "127.0.0.1" or real(host))
    monkeypatch.setattr(images, "MAX_ART_BYTES", 1024)
    try:
        for path, error in (("hop", "private address"), ("loop", "too many times"), ("huge", "too big"),
                            ("text", "is it an image")):
            with pytest.raises(akef_cards.CardError, match=error):
                await images.load_art(f"{base}/{path}", allow_remote=True)
    finally:
        await runner.cleanup()


async def test_custom_art_not_cached(profile, tmp_path):
    file = tmp_path / "art.png"
    Image.new("RGBA", (600, 900), (200, 80, 80, 255)).save(file)
    cards = akef_cards.Cards(images=akef_cards.ImageCache(tmp_path / "cache"))

    async def blank_images(urls):
        return {u: Image.new("RGBA", (64, 64)) for u in urls if u}

    cards.images.get = blank_images
    build = profile.build("Si")
    old = await cards.render(build, art=str(file), allow_local=True)
    Image.new("RGBA", (600, 900), (80, 80, 200, 255)).save(file)
    new = await cards.render(build, art=str(file), allow_local=True)
    assert old.tobytes() != new.tobytes()
    with pytest.raises(akef_cards.CardError, match="allow_local"):
        await cards.render(build, art=str(file))

    assert not cards._drawn._data
    await cards.render(build)
    assert len(cards._drawn._data) == 1
