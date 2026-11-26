import asyncio
import sys
from pathlib import Path

from PIL import Image, ImageOps

import akef_cards

sys.stdout.reconfigure(encoding="utf-8")

OUT = Path("cards")
OUT.mkdir(exist_ok=True)
ART = Path(__file__).parent / "art"

# art by pigeonfight99 and kisaragi_pana
PIGEON = ART / "gilberta_by_pigeonfight99.jpg"
PANA = ART / "gilberta_by_kisaragi_pana.jpg"


async def main():
    async with akef_cards.Cards() as cards:
        gilberta = (await cards.enka(4727743200)).build("Gilberta")

        # python custom_art.py my_art.png  (or a url)
        if len(sys.argv) > 1:
            card = await cards.render(gilberta, art=sys.argv[1], allow_local=True, allow_remote=True)
            card.save(OUT / "custom_art.png")
            print("saved", OUT / "custom_art.png")
            return

        # a Path just works, strings need allow_local / allow_remote
        for template in (1, 2):
            (await cards.render(gilberta, art=PIGEON, template=template)).save(OUT / f"pigeonfight99_{template}.png")

        data = PANA.read_bytes()
        for template in (1, 2):
            (await cards.render(gilberta, art=data, template=template)).save(OUT / f"kisaragi_pana_{template}.png")

        # a pillow image, so you can edit it first. here its mirrored
        mirrored = ImageOps.mirror(Image.open(PANA))
        (await cards.render(gilberta, art=mirrored)).save(OUT / "kisaragi_pana_mirrored.png")

        print("saved to", OUT)


asyncio.run(main())
