import asyncio
import io
import random

import pytest
from PIL import Image

import akef_cards
from akef_cards.templates import showcase

from tests.helpers import png_bytes, moving_gif, fake_clip, read_anim


def test_frame_timing():
    from akef_cards.animate import read_frames

    for format in ("GIF", "WEBP"):
        frames, times = read_frames(moving_gif(format=format), frame_step=1)
        assert len(frames) == 6 and times == [50] * 6
        frames, times = read_frames(moving_gif(format=format))
        assert len(frames) == 3 and times == [100] * 3
    frames, times = read_frames(moving_gif(7))
    assert len(frames) == 4 and times == [100, 100, 100, 50]
    frames, times = read_frames(moving_gif(10), max_frames=4)
    assert len(frames) == 4 and sum(times) == 500
    for tiny in (2, 3):
        frames, times = read_frames(moving_gif(tiny), frame_step=10)
        assert len(frames) == 2 and sum(times) == tiny * 50


def test_bad_animation(monkeypatch):
    from akef_cards import animate

    for bad, error in ((png_bytes(), "doesnt move"), (b"nope", "couldn't read")):
        with pytest.raises(akef_cards.CardError, match=error):
            animate.read_frames(bad)
    monkeypatch.setattr(animate, "MAX_TOTAL_PIXELS", 1000)
    with pytest.raises(akef_cards.CardError, match="too big"):
        animate.read_frames(moving_gif())


@pytest.mark.parametrize("template", [1, 2])
async def test_compose_matches_render(profile, template):
    from PIL import ImageChops
    from akef_cards import animate

    build = profile.build("Liino")
    draw, _, span = animate.LAYOUTS[template]
    black, white, real = (draw(build, {}, art=Image.new("RGBA", (span, showcase.H), c))
                          for c in ((0, 0, 0, 255), (255, 255, 255, 255), (180, 60, 120, 255)))
    mixed = ImageChops.add(black, ImageChops.multiply(ImageChops.subtract(white, black),
                                                      Image.new("RGB", black.size, (180, 60, 120))))
    assert max(high for _, high in ImageChops.difference(mixed, real).getextrema()) <= 3


@pytest.mark.parametrize("template", [1, 2])
@pytest.mark.parametrize("format, how", [("WEBP", "contain"), ("GIF", "cover")])
async def test_render_animated(profile, template, format, how):
    cards = akef_cards.Cards()

    async def no_images(urls):
        return {}

    cards.images.get = no_images
    out = await cards.render_animated(profile.build("Si"), moving_gif(), template=template, format=format, fit=how,
                                      width=500)
    assert out.name == f"card.{format.lower()}"
    with Image.open(out) as img:
        assert img.format == format and img.n_frames == 3 and img.width == 500
    every = await cards.render_animated(profile.build("Si"), moving_gif(), template=template, frame_step=1, width=500)
    with Image.open(every) as img:
        assert img.n_frames == 6


async def test_animated_art_rules(profile, tmp_path, monkeypatch):
    from akef_cards import images

    cards = akef_cards.Cards()
    build = profile.build("Si")
    file = tmp_path / "a.gif"
    file.write_bytes(moving_gif())
    with pytest.raises(akef_cards.CardError, match="allow_local"):
        await cards.render_animated(build, str(file))
    with pytest.raises(akef_cards.CardError, match="allow_remote"):
        await cards.render_animated(build, "https://example.com/a.gif")
    with pytest.raises(akef_cards.CardError, match="private address"):
        await cards.render_animated(build, "http://127.0.0.1/a.gif", allow_remote=True)
    monkeypatch.setattr(images, "MAX_ART_BYTES", 10)
    with pytest.raises(akef_cards.CardError, match="too big"):
        await cards.render_animated(build, file)
    for bad in ({"template": 3}, {"format": "MP4"}, {"fit": "stretch"}):
        with pytest.raises(ValueError):
            await cards.render_animated(build, moving_gif(), **bad)


@pytest.mark.parametrize("format", ["GIF", "WEBP"])
def test_small_anim_quality(format):
    from PIL import ImageChops
    from akef_cards.animate import encode

    frames = []
    for x in (0, 40, 80, 0, 0, 120):
        frame = Image.new("RGB", (200, 80), (240, 238, 232))
        frame.paste((200, 40, 40), (x, 20, x + 30, 50))
        frames.append(frame)
    times = [40, 50, 60, 70, 80, 90]
    with Image.open(io.BytesIO(encode(frames, times, format, 90))) as img:
        shown, clock = [], 0
        for i in range(img.n_frames):
            img.seek(i)
            got = img.convert("RGB")
            clock += img.info["duration"]
            shown.append((clock, got))
    assert clock == sum(times)
    start = 0
    for frame, took in zip(frames, times):
        got = next(g for end, g in shown if start + took / 2 < end)
        off = ImageChops.difference(frame, got).convert("L")
        assert sum(i * n for i, n in enumerate(off.histogram())) / (200 * 80) < 3
        start += took


def test_clip_edits():
    card = fake_clip()
    cut = card.trim(0.075, 0.275)
    assert cut.times == (25, 50, 50, 50, 25) and cut.frames == card.frames[1:6]
    assert card.speed(2).duration == 0.2 and card.speed(0.5).duration == 0.8
    assert card.reverse().frames == card.frames[::-1]
    bounced = card.bounce()
    assert bounced.frame_count == 14 and bounced.frames[8] is card.frames[6] and bounced.frames[-1] is card.frames[1]
    assert card._halved().times == (100,) * 4
    assert card.hold(1).times[-1] == 1050 and card.hold(1, "start").times[0] == 1050
    assert card.resize(300).size == (300, 150) and card.resize(900).size == (400, 200)
    assert card.still(0.12).tobytes() == card.frames[2].tobytes()
    assert card.still(99).tobytes() == card.frames[-1].tobytes()
    assert card.frame_count == 8 and card.times == (50,) * 8 and card.width is None


@pytest.mark.parametrize("bad", [
    lambda c: c.trim(0.3, 0.2), lambda c: c.trim(9), lambda c: c.trim(0, 0.04), lambda c: c.speed(0),
])
def test_clip_bad_edits(bad):
    with pytest.raises(ValueError):
        bad(fake_clip())


@pytest.mark.parametrize("format", ["WEBP", "GIF"])
async def test_clip_export(format, tmp_path):
    card = fake_clip().resize(300)
    size, times, loop = read_anim(await card.to_bytes(format))
    assert size == (300, 150) and sum(times) == 400 and loop == 0
    once = read_anim(await card.loops(1).to_bytes(format))[2]
    thrice = read_anim(await card.loops(3).to_bytes(format))[2]
    assert (once, thrice) == ((None, 2) if format == "GIF" else (1, 3))
    size, times, _ = read_anim(await fake_clip(40, 40).speed(5).to_bytes(format))
    assert min(times) >= 20 and abs(sum(times) - 320) <= 10
    path = await card.save(tmp_path / f"a.{format.lower()}")
    assert read_anim(path)[0] == (300, 150)
    with pytest.raises(ValueError):
        await card.save(tmp_path / "a.mp4")


async def test_parallel_exports():
    card = fake_clip(12)
    alone = [(await card.to_bytes(f)).getvalue() for f in ("WEBP", "GIF")]
    together = await asyncio.gather(*(card.to_bytes(f) for f in ("WEBP", "GIF") * 4))
    assert [t.getvalue() for t in together] == alone * 4


async def test_fit_under():
    rng = random.Random(1)
    noisy = [Image.frombytes("RGB", (800, 400), rng.randbytes(800 * 400 * 3)) for _ in range(20)]
    card = fake_clip().__class__(tuple(noisy), (40,) * 20, fake_clip().run)
    full = len((await card.to_bytes()).getvalue())
    limit = full * 0.4 / 1_000_000
    out = await card.fit_under(limit, min_width=200)
    assert len(out.getvalue()) <= limit * 1_000_000
    assert out.settings["frames"] < 20 or out.settings["width"] < 800
    assert read_anim(out)[0][0] == out.settings["width"]
    with pytest.raises(akef_cards.CardError, match="smallest was"):
        await card.fit_under(0.0001, min_width=700)


async def test_animated_card_and_info(profile):
    cards = akef_cards.Cards()

    async def no_images(urls):
        return {}

    cards.images.get = no_images
    info = await cards.animation_info(moving_gif(6, (370, 498)))
    assert (info.width, info.height, info.frames, info.duration, info.fit) == (370, 498, 6, 0.3, "cover")
    assert (await cards.animation_info(moving_gif(4, (498, 281)))).fit == "contain"
    card = await cards.animated_card(profile.build("Si"), moving_gif(), fit="auto", width=400, frame_step=1)
    assert isinstance(card, akef_cards.AnimatedCard) and card.frame_count == 6 and card.size[0] == 400
    for bad in ({"fit": "nope"}, {"template": 9}):
        with pytest.raises(ValueError):
            await cards.animated_card(profile.build("Si"), moving_gif(), **bad)


def test_focus():
    from akef_cards.animate import _panel

    wide = Image.new("RGBA", (300, 100), (255, 0, 0, 255))
    wide.paste((0, 0, 255, 255), (150, 0, 300, 100))
    left = _panel(wide, (100, 100), "cover", (0, 0.5))
    right = _panel(wide, (100, 100), "cover", (1, 0.5))
    assert left.getpixel((50, 50))[0] > 200 and right.getpixel((50, 50))[2] > 200
