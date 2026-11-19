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
    # draws every card in every template, handy to pick the look you like
    async with akef.Client(TOKEN) as client, akef_cards.Cards() as cards:
        card = await client.card()
        jobs = {
            "operator": (cards.render, await cards.skport(card, card.chars[0]), (1, 2)),
            "live": (cards.render_live, cards.skport_live(card), (1, 2)),
            "roster": (cards.render_roster, cards.skport_roster(card), (None,)),
            "factory": (cards.render_factory, cards.skport_factory(card), (1, 2)),
            "contract": (cards.render_contract, cards.skport_contract(card), (1, 2)),
            "pulls": (cards.render_pulls, await cards.skport_pulls(card, await client.pulls()), (1, 2)),
        }
        for name, (draw, data, templates) in jobs.items():
            for t in templates:
                image = await (draw(data) if t is None else draw(data, template=t))
                image.save(OUT / f"{name}{t or ''}.png")
                print("drew", name, t or "")
        for t in (1, 2, 3):
            for i, page in enumerate(await cards.render_profile(cards.skport_player(card), template=t), 1):
                page.save(OUT / f"profile{t}_{i}.png")
        print("all in", OUT)


asyncio.run(main())
