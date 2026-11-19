import asyncio
import os
import sys
from pathlib import Path

import akef
import akef_cards

sys.stdout.reconfigure(encoding="utf-8")

TOKEN = os.environ.get("SKPORT_TOKEN") or (Path.home() / ".skport_token").read_text().strip()
OUT = Path("cards")
OUT.mkdir(exist_ok=True)


async def main():
    async with akef.Client(TOKEN) as client, akef_cards.Cards() as cards:
        ops = await client.wiki("operators")
        item = await client.wiki_item(next(o for o in ops if o.name == "Gilberta").id)
        page = cards.wiki(item, await client.wiki_index())
        for part, image in zip(page.parts, await cards.render_wiki_pages(page, template=2)):
            image.save(OUT / f"wiki_{part.value}.png")
            print("drew", part.value)


asyncio.run(main())
