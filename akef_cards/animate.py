from __future__ import annotations

import io

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, UnidentifiedImageError

from akef_cards.draw import cover, fit
from akef_cards.errors import CardError
from akef_cards.templates import ingame, showcase

LAYOUTS = {1: (showcase.render, 0, 940), 2: (ingame.render, 540, 800)}
FITS = ("contain", "cover")
FORMATS = ("WEBP", "GIF")
MAX_FRAMES = 120
FRAME_STEP = 2
MAX_TOTAL_PIXELS = 150_000_000
GIF_SLACK = 6
CLEAR = 255


def read_frames(data: bytes, frame_step: int = FRAME_STEP,
                max_frames: int = MAX_FRAMES) -> tuple[list[Image.Image], list[int]]:
    try:
        with Image.open(io.BytesIO(data)) as img:
            count = getattr(img, "n_frames", 1)
            if count < 2:
                raise CardError("that art doesnt move, use render() for still pics")
            if img.width * img.height * count > MAX_TOTAL_PIXELS:
                raise CardError("animation is too big, try a smaller or shorter one")
            step = min(max(frame_step, -(-count // max_frames)), count - 1)
            frames, times = [], []
            for i in range(count):
                img.seek(i)
                frame = img.convert("RGBA")
                took = img.info.get("duration") or 100
                if i % step:
                    times[-1] += took
                else:
                    frames.append(frame)
                    times.append(took)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise CardError("couldn't read the animation, is it a gif or webp?") from exc
    return frames, times


def _panel(frame: Image.Image, size: tuple[int, int], how: str) -> Image.Image:
    flat = Image.new("RGBA", frame.size, (14, 15, 19, 255))
    flat.alpha_composite(frame)
    if how == "cover":
        return cover(flat, *size, 0.5).convert("RGB")
    small = cover(flat, size[0] // 8, size[1] // 8, 0.5).filter(ImageFilter.GaussianBlur(4))
    back = ImageEnhance.Brightness(small.resize(size, Image.BILINEAR)).enhance(0.55)
    front = fit(flat, *size)
    top = (size[1] - front.height) // 2
    fade = Image.new("L", front.size, 255)
    edge = min(40, front.height // 6)
    for y in range(edge):
        row = int(255 * y / edge)
        fade.paste(row, (0, y, front.width, y + 1))
        fade.paste(row, (0, front.height - 1 - y, front.width, front.height - y))
    back.paste(front, ((size[0] - front.width) // 2, top), fade)
    return back.convert("RGB")


def _only_changes(frames: list[Image.Image]) -> list[Image.Image]:
    shown = frames[0].convert("RGB")
    out = [frames[0]]
    for frame in frames[1:]:
        new = frame.convert("RGB")
        r, g, b = ImageChops.difference(new, shown).split()
        changed = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > GIF_SLACK else 0)
        shown.paste(new, (0, 0), changed)
        part = frame.copy()
        part.paste(CLEAR, (0, 0), ImageChops.invert(changed))
        out.append(part)
    return out


def _encode(frames: list[Image.Image], times: list[int], format: str, quality: int) -> bytes:
    out = io.BytesIO()
    if format == "WEBP":
        frames[0].save(out, "WEBP", save_all=True, append_images=frames[1:], duration=times, loop=0,
                       quality=quality, method=4, minimize_size=True)
    else:
        picks = frames[::max(1, len(frames) // 8)]
        strip = Image.new("RGB", (frames[0].width, frames[0].height * len(picks)))
        for i, frame in enumerate(picks):
            strip.paste(frame, (0, i * frames[0].height))
        palette = strip.quantize(CLEAR, method=Image.Quantize.MEDIANCUT)
        done = _only_changes([f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames])
        done[0].save(out, "GIF", save_all=True, append_images=done[1:], duration=times, loop=0, optimize=False,
                     disposal=1, transparency=CLEAR)
    return out.getvalue()


def render_card(build, data: bytes, images, *, template: int = 1, how: str, format: str, width: int,
                quality: int, frame_step: int = FRAME_STEP, hide_uid: bool = False) -> bytes:
    frames, times = read_frames(data, frame_step)
    draw, left, span = LAYOUTS[template]
    dark, light = (draw(build, images, art=Image.new("RGBA", (span, showcase.H), colour), hide_uid=hide_uid)
                   for colour in ((0, 0, 0, 255), (255, 255, 255, 255)))
    scale = min(1.0, width / dark.width)
    size = (round(dark.width * scale), round(dark.height * scale))
    area = (round(left * scale), 0, round((left + span) * scale), size[1])
    dark = dark.resize(size, Image.LANCZOS)
    light = light.resize(size, Image.LANCZOS)
    base = dark.crop(area)
    shows = ImageChops.subtract(light.crop(area), base)

    out = []
    for frame in frames:
        card = dark.copy()
        card.paste(ImageChops.add(base, ImageChops.multiply(shows, _panel(frame, base.size, how))), area[:2])
        out.append(card)
    return _encode(out, times, format, quality)
