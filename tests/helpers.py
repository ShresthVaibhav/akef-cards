import asyncio
import io
import json
from pathlib import Path

from PIL import Image

import akef
import akef_cards

DATA = Path(__file__).parent / "data"


async def pic_server(handler):
    from aiohttp import web

    app = web.Application()
    app.router.add_get("/{name}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 0).start()
    return runner, f"http://127.0.0.1:{runner.addresses[0][1]}"


def png_bytes():
    out = io.BytesIO()
    Image.new("RGBA", (8, 8), (1, 2, 3, 255)).save(out, format="PNG")
    return out.getvalue()


def skport_card():
    raw = json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))
    return akef.Card.model_validate(raw["data"]["detail"])


def moving_gif(frames=6, size=(160, 90), format="GIF"):
    shots = [Image.new("RGB", size, (40 * i, 200 - 30 * i, 90)) for i in range(frames)]
    out = io.BytesIO()
    shots[0].save(out, format, save_all=True, append_images=shots[1:], duration=50, loop=0)
    return out.getvalue()


def fake_clip(count=8, ms=50, size=(400, 200)):
    async def run(fn, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    frames = tuple(Image.new("RGB", size, (30 * i % 256, 90, 200 - 20 * i % 200)) for i in range(count))
    return akef_cards.AnimatedCard(frames, (ms,) * count, run)


def read_anim(data):
    with Image.open(data) as img:
        times = []
        for i in range(img.n_frames):
            img.seek(i)
            img.load()
            times.append(img.info.get("duration", 0))
        return img.size, times, img.info.get("loop")
