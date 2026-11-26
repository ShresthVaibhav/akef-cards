import asyncio
import json
import os
import threading
import time
from pathlib import Path

import pytest
from PIL import Image

import akef
import akef_cards

from tests.helpers import DATA, pic_server, png_bytes


async def test_card_cache(profile, tmp_path):
    cards = akef_cards.Cards(images=akef_cards.ImageCache(tmp_path))
    si = profile.build("Si")
    si.art, si.element_icon, si.skills, si.talents, si.gear, si.weapon = "", "", [], [], [], None
    first = await cards.render(si)
    assert len(cards._drawn._data) == 1
    again = await cards.render(si)
    assert again.tobytes() == first.tobytes() and again is not first
    si.level = 80
    await cards.render(si)
    assert len(cards._drawn._data) == 2
    await cards.render(si, art=Image.new("RGBA", (10, 10)))
    assert len(cards._drawn._data) == 2


def test_cache_trim(tmp_path):
    import os
    import time

    from akef_cards.images import ImageCache

    cache = ImageCache(tmp_path, max_mb=0.003)
    urls = [f"https://example.com/{i}.png" for i in range(4)]
    now = time.time()
    for i, url in enumerate(urls):
        cache._file(url).write_bytes(b"x" * 1024)
        os.utime(cache._file(url), (now - 100 + i, now - 100 + i))
    os.utime(cache._file(urls[0]), (now, now))
    cache.trim(keep=[urls[1]])
    left = {u for u in urls if cache._file(u).exists()}
    assert left == {urls[0], urls[1], urls[3]}
    assert cache.size() <= 3 * 1024


async def test_cache_keys(tmp_path):
    from akef_cards.images import ImageCache

    cache = ImageCache(tmp_path)
    Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(cache._file("https://a.example/20260101/abc123.png"), "PNG")
    got = await cache.get(["https://b.example/20261105/abc123.png?expires=1"])
    assert list(got) == ["https://b.example/20261105/abc123.png?expires=1"]


async def test_render_bytes_all(tmp_path):
    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    cards = akef_cards.Cards(images=akef_cards.ImageCache(tmp_path))
    live = await cards.render_bytes(cards.skport_live(card))
    assert live.name == "live.png" and live.read(4)[1:] == b"PNG"
    roster = await cards.render_bytes(cards.skport_roster(card), format="JPEG")
    assert roster.name == "roster.jpeg"
    pages = await cards.render_bytes(cards.skport_player(card), grid="4x2")
    assert isinstance(pages, list) and pages[0].name == "profile1.png"
    with pytest.raises(TypeError):
        await cards.render_bytes("nope")


async def test_render_bytes_jpeg_and_wiki(profile, tmp_path):
    from akef.wiki import WikiPage, WikiSkill

    cards = akef_cards.Cards(images=akef_cards.ImageCache(tmp_path))
    for fmt in ("JPEG", "jpg"):
        file = await cards.render_bytes(profile.build("Si"), format=fmt)
        assert file.read(3) == b"\xff\xd8\xff"
    page = WikiPage("Arcane", "", "Quote.", "Bio.", [("Race", "Liberi")],
                    skills=[WikiSkill("Gloompurge", "Ultimate", "", "Boom.")])
    files = await cards.render_bytes(page, format="JPEG")
    assert len(files) == len(page.parts) and files[0].name == "wiki1.jpeg"


async def test_shared_download(tmp_path):
    from aiohttp import web

    hits, gate = [], asyncio.Event()

    async def pic(request):
        hits.append(request.path)
        await gate.wait()
        return web.Response(body=png_bytes())

    runner, base = await pic_server(pic)
    cache = akef_cards.ImageCache(tmp_path)
    url = f"{base}/a.png"
    try:
        tasks = [asyncio.create_task(cache.get([url])) for _ in range(20)]
        while not hits:
            await asyncio.sleep(0.01)
        tasks[0].cancel()
        await asyncio.sleep(0.01)
        gate.set()
        done = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await runner.cleanup()
    assert isinstance(done[0], asyncio.CancelledError)
    assert all(url in got for got in done[1:])
    assert hits == ["/a.png"]
    assert not cache._loading and cache._session is None
    assert [f.name for f in tmp_path.iterdir()] == ["a.png.img"]


async def test_download_retry(tmp_path):
    from aiohttp import web

    hits = []

    async def flaky(request):
        hits.append(1)
        return web.Response(status=500) if len(hits) == 1 else web.Response(body=png_bytes())

    runner, base = await pic_server(flaky)
    cache = akef_cards.ImageCache(tmp_path)
    try:
        assert await cache.get([f"{base}/a.png"]) == {}
        assert len(await cache.get([f"{base}/a.png"])) == 1
    finally:
        await runner.cleanup()


def test_failed_save(tmp_path, monkeypatch):
    cache = akef_cards.ImageCache(tmp_path)
    file = tmp_path / "a.img"
    cache._save(file, b"old")

    def nope(*args):
        raise PermissionError

    monkeypatch.setattr("os.replace", nope)
    cache._save(file, b"new")
    assert file.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [file]


def test_trim_missing_files(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    cache = akef_cards.ImageCache(tmp_path, max_mb=0)
    for i in range(300):
        (tmp_path / f"{i}.img").write_bytes(b"x" * 100)
    real = Path.glob
    monkeypatch.setattr(Path, "glob", lambda self, p: [*real(self, p), self / "ghost.img"])
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda _: (cache.trim(), cache.size()), range(16)))
    monkeypatch.undo()
    assert not list(tmp_path.glob("*.img"))


@pytest.mark.parametrize("limit, most", [(None, 6), (1, 1), (2, 2)])
async def test_render_limit(limit, most):
    cards = akef_cards.Cards(max_renders=limit)
    lock, running, peak = threading.Lock(), [0], [0]

    def slow(images):
        with lock:
            running[0] += 1
            peak[0] = max(peak[0], running[0])
        time.sleep(0.15)
        with lock:
            running[0] -= 1
        return Image.new("RGBA", (1, 1))

    await asyncio.gather(*(cards._draw(None, [], slow) for _ in range(6)))
    assert peak[0] == most


async def test_cancel_keeps_slot():
    cards = akef_cards.Cards(max_renders=1)
    started, finish, order = threading.Event(), threading.Event(), []

    def first(images):
        started.set()
        finish.wait(5)
        order.append("first")
        return Image.new("RGBA", (1, 1))

    def second(images):
        order.append("second")
        return Image.new("RGBA", (1, 1))

    one = asyncio.create_task(cards._draw(None, [], first))
    assert await asyncio.to_thread(started.wait, 5)
    one.cancel()
    two = asyncio.create_task(cards._draw(None, [], second))
    await asyncio.sleep(0.2)
    assert order == []
    finish.set()
    await two
    assert order == ["first", "second"]


def test_bad_render_limit():
    with pytest.raises(ValueError):
        akef_cards.Cards(max_renders=0)


async def test_disk_in_threads(tmp_path, monkeypatch):
    from aiohttp import web

    async def pic(request):
        return web.Response(body=png_bytes())

    main, calls = threading.get_ident(), []

    def watch(owner, name):
        real = getattr(owner, name)

        def spy(*args, **kwargs):
            calls.append((name, threading.get_ident() == main))
            return real(*args, **kwargs)

        monkeypatch.setattr(owner, name, spy)

    watch(Path, "read_bytes")
    watch(akef_cards.ImageCache, "_save")
    watch(os, "utime")
    runner, base = await pic_server(pic)
    try:
        for _ in range(2):
            assert len(await akef_cards.ImageCache(tmp_path).get([f"{base}/a.png"])) == 1
    finally:
        await runner.cleanup()
    assert {name for name, _ in calls} == {"read_bytes", "_save", "utime"}
    assert not any(on_main for _, on_main in calls)
