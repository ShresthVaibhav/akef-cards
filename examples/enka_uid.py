import asyncio
import sys
from datetime import datetime
from pathlib import Path

import akef_cards

sys.stdout.reconfigure(encoding="utf-8")


async def main():
    uid = sys.argv[1] if len(sys.argv) > 1 else "4727743200"
    out = Path("cards")
    out.mkdir(exist_ok=True)
    async with akef_cards.Cards() as cards:
        profile = await cards.enka(uid)
        print(f"{profile.owner.name} · AL {profile.owner.level} · {len(profile.builds)} operators")
        for build in profile.builds:
            image = await cards.render(build)
            path = out / f"enka_{build.name.lower().replace(' ', '_')}.png"
            try:
                image.save(path)
            except OSError:
                # windows wont overwrite a file thats open in a viewer
                path = path.with_stem(f"{path.stem}_{datetime.now():%H%M%S}")
                image.save(path)
            s = build.stats
            print(f"  {build.name:<10} HP {s.hp:,}  ATK {s.atk:,}  -> {path}")


asyncio.run(main())
