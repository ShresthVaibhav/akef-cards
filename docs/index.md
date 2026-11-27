---
hide:
  - toc
---

# akef-cards

Image cards for Arknights: Endfield. Operator builds, profiles, pull history, exploration, endgame stuff, and
animated operator cards if you've got a gif you like.

![operator card](images/operator_2.jpg)

```
pip install akef-cards
```

```py
import asyncio
import akef_cards


async def main():
    async with akef_cards.Cards() as cards:
        profile = await cards.enka(4727743200)
        for build in profile.builds:
            image = await cards.render(build)
            image.save(f"{build.name}.png")


asyncio.run(main())
```

Operator, compare and profile cards work with just an Enka UID. The rest read a SKPORT account, that part is
[akef](https://github.com/ShresthVaibhav/akef), this one only draws. Start with [Getting started](getting-started.md)
or jump to a card below.

## Cards

<div class="gallery" markdown>

[![](images/operator_1.jpg){ .no-zoom }<br>Operator](cards/operator.md)
[![](images/animated_2.gif){ .no-zoom }<br>Animated operator](cards/animated.md)
[![](images/compare_2.jpg){ .no-zoom }<br>Compare](cards/compare.md)
[![](images/profile_3.jpg){ .no-zoom }<br>Profile](cards/profile.md)
[![](images/live_2.jpg){ .no-zoom }<br>Live status](cards/live.md)
[![](images/roster.jpg){ .no-zoom }<br>Roster](cards/roster.md)
[![](images/factory_2.jpg){ .no-zoom }<br>Factory](cards/factory.md)
[![](images/exploration_3.jpg){ .no-zoom }<br>Exploration](cards/exploration.md)
[![](images/pulls_2.jpg){ .no-zoom }<br>Pull history](cards/pulls.md)
[![](images/monument_event_2.jpg){ .no-zoom }<br>Monument](cards/monument.md)
[![](images/contract_detail_2.jpg){ .no-zoom }<br>Contingency Contract](cards/contract.md)
[![](images/wiki_2.jpg){ .no-zoom }<br>Wiki](cards/wiki.md)

</div>

Scripts for all of these are in [examples](https://github.com/ShresthVaibhav/akef-cards/tree/main/examples), bot
recipes and a FAQ are in the [wiki](https://github.com/ShresthVaibhav/akef-cards/wiki).
