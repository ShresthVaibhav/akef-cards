import asyncio
import sys
import time

import akef_cards

sys.stdout.reconfigure(encoding="utf-8")


async def timed(label, call):
    start = time.perf_counter()
    result = await call
    print(f"{label}: {(time.perf_counter() - start) * 1000:.0f}ms")
    return result


async def main():
    async with akef_cards.Cards(cache_mb=50, kept_cards=16) as cards:
        profile = await timed("enka", cards.enka(4727743200))
        build = profile.builds[0]
        await timed("first card, downloads art", cards.render(build))
        await timed("same card again, from memory", cards.render(build))
        await timed("other template, art from disk", cards.render(build, template=2))
        print(f"image cache is {cards.images.size() / 1024 / 1024:.1f} MB")

        cards.clear_cache()
        await timed("after clear_cache", cards.render(build))

    async with akef_cards.Cards(cache=False) as cards:
        build = (await cards.enka(4727743200)).builds[0]
        await timed("cache off", cards.render(build))
        await timed("cache off again", cards.render(build))


asyncio.run(main())
