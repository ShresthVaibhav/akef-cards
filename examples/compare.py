import asyncio
import sys
from pathlib import Path

import akef_cards

sys.stdout.reconfigure(encoding="utf-8")

OUT = Path("cards")
OUT.mkdir(exist_ok=True)


async def main():
    # python compare.py <uid> <other uid> Yvonne Gilberta
    a, b = sys.argv[1:3] if len(sys.argv) > 2 else ("4727743200", "4727743200")
    names = sys.argv[3:] or ["Yvonne"]
    async with akef_cards.Cards() as cards:
        for template in (1, 2):
            for i, image in enumerate(await cards.render_compare(a, b, names, template=template)):
                image.save(OUT / f"compare{template}_{i}.png")
        print("saved to", OUT)


asyncio.run(main())
