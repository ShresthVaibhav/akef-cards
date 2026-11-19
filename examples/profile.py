import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

import akef_cards

sys.stdout.reconfigure(encoding="utf-8")


def save(image, path):
    try:
        image.save(path)
    except OSError:
        # windows won't overwrite a file that's open in a viewer
        path = path.with_stem(f"{path.stem}_{datetime.now():%H%M%S}")
        image.save(path)
    print(path)


async def main():
    uid = next((a for a in sys.argv[1:] if a.isdigit()), "4727743200")
    grid = "3x3" if "--3x3" in sys.argv else "4x2"
    template = 2 if "--dark" in sys.argv else 1
    out = Path("cards")
    out.mkdir(exist_ok=True)
    async with akef_cards.Cards() as cards:
        enka = await cards.enka(uid)
        for image in await cards.render_profile(enka.player, template=template, grid=grid):
            save(image, out / f"profile{template}_enka_{grid}.png")

        token = os.environ.get("SKPORT_TOKEN") or (Path.home() / ".skport_token").read_text().strip()
        import akef

        async with akef.Client(token) as client:
            player = cards.skport_player(await client.card())
        for i, image in enumerate(await cards.render_profile(player, template=template, grid=grid), 1):
            save(image, out / f"profile{template}_skport_{grid}_{i}.png")


asyncio.run(main())
