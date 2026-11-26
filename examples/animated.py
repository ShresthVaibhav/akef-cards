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
        print(await cards.animation_info(art))
        gilberta = (await cards.enka(4727743200)).build("Gilberta")

        card = await cards.animated_card(gilberta, art, fit="auto")
        await card.save(OUT / "animated.webp")
        await card.save(OUT / "animated.gif")
        await card.speed(0.75).hold(0.8).save(OUT / "slow.webp")
        await card.bounce().save(OUT / "bounce.webp")
        card.still(0.5).save(OUT / "thumb.png")

        small = await card.fit_under(0.5)
        (OUT / "small.webp").write_bytes(small.getvalue())
        print("small one used", small.settings)
        print("all in", OUT)


asyncio.run(main())
