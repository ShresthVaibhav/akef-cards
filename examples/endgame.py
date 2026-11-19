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
        card = await client.card()
        monument = cards.skport_monument(card, await client.monument())
        (await cards.render_monument(monument)).save(OUT / "monument.png")

        # nothing passed = latest event, a name or a list works too
        (await cards.render_monument_event(monument, template=2)).save(OUT / "monument_latest.png")
        for i, image in enumerate(await cards.render_monument_event(monument, ["Searing Scars", 0])):
            image.save(OUT / f"monument_event_{i}.png")

        detail = cards.skport_contract_detail(card, await client.contract())
        (await cards.render_contract_detail(detail, template=2)).save(OUT / "contract_best_4.png")
        print("saved to", OUT)


asyncio.run(main())
