import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

import akef
import akef_cards

sys.stdout.reconfigure(encoding="utf-8")

TOKEN = os.environ.get("SKPORT_TOKEN") or (Path.home() / ".skport_token").read_text().strip()


async def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or ["Arcane"]
    out = Path("cards")
    out.mkdir(exist_ok=True)
    async with akef.Client(TOKEN) as client, akef_cards.Cards() as cards:
        card = await client.card()
        for name in names:
            build = await cards.skport(card, name)
            image = await cards.render(build, hidden="--hide" in sys.argv)
            path = out / f"skport_{name.lower().replace(' ', '_')}.png"
            try:
                image.save(path)
            except OSError:
                # windows won't overwrite a file that's open in a viewer
                path = path.with_stem(f"{path.stem}_{datetime.now():%H%M%S}")
                image.save(path)
            print(path)


asyncio.run(main())
