import asyncio
import sys
from pathlib import Path

import akef_cards

OUT = Path("cards")
OUT.mkdir(exist_ok=True)


async def main():
    if len(sys.argv) < 2:
        sys.exit("give me a gif or animated webp")
    art = Path(sys.argv[1])

    async with akef_cards.Cards() as cards:
        gilberta = (await cards.enka(4727743200)).build("Gilberta")
        for format in ("WEBP", "GIF"):
            card = await cards.render_animated(gilberta, art, format=format)
            (OUT / card.name).write_bytes(card.getvalue())
            print("saved", OUT / card.name)


asyncio.run(main())
