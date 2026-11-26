import asyncio
import logging
import sys
from pathlib import Path

import akef_cards

sys.stdout.reconfigure(encoding="utf-8")

OUT = Path("cards")
OUT.mkdir(exist_ok=True)
logging.basicConfig(level=logging.WARNING, format="%(message)s")


async def main():
    async with akef_cards.Cards() as cards:
        build = (await cards.enka(4727743200)).builds[0]

        # blurs the uid, nice for screenshots
        (await cards.render(build, hidden=True)).save(OUT / "hidden.png")

        # for bots: a BytesIO with a file name
        file = await cards.render_bytes(build, format="PNG")
        print("ready to send:", file.name, len(file.getvalue()), "bytes")

    # names follow the language, labels that arent translated yet stay english and get logged
    async with akef_cards.Cards(lang="ja") as cards:
        build = (await cards.enka(4727743200)).builds[0]
        (await cards.render(build, template=2)).save(OUT / "japanese.png")
        print("saved to", OUT)


asyncio.run(main())
