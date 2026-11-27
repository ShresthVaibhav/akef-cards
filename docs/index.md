---
title: Home
nav_order: 1
---

# akef-cards

Image cards for Arknights: Endfield. Operator builds, profiles, pull history, exploration, endgame stuff and a
few more, plus animated operator cards from your own gif.
{: .fs-5 .fw-300 }

[Get started](getting-started.md){: .btn .btn-primary .mr-2 } [Every card](cards.md){: .btn .mr-2 } [GitHub](https://github.com/ShresthVaibhav/akef-cards){: .btn }

---

![operator card](images/operator_2.jpg)

## Install

```
pip install akef-cards
```

Python 3.10 or newer. It pulls in [akef](https://github.com/ShresthVaibhav/akef), which does all the data
side (SKPORT, Enka, final stats, the wiki). This library only draws, if you just want the numbers use akef.

## Quick start

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

Operator, compare and profile cards only need an Enka UID. Everything else reads a SKPORT account.

## What's in here

| Card | Templates | Needs |
| --- | --- | --- |
| [Operator](cards/operator.md) | 2 | Enka or SKPORT |
| [Animated operator](cards/animated.md) | 2 | Enka or SKPORT |
| [Compare](cards/compare.md) | 2 | Enka |
| [Profile](cards/profile.md) | 3 | Enka or SKPORT |
| [Live status](cards/live.md) | 2 | SKPORT |
| [Roster](cards/roster.md) | 1 | SKPORT |
| [Factory](cards/factory.md) | 2 | SKPORT |
| [Exploration](cards/exploration.md) | 3 | SKPORT |
| [Pull history](cards/pulls.md) | 2 | SKPORT |
| [Monument](cards/monument.md) | 1 overview, 2 event | SKPORT |
| [Contingency Contract](cards/contract.md) | 2 summary, 2 detail | SKPORT |
| [Wiki](cards/wiki.md) | 2 | SKPORT wiki |

## Some cards

| | |
| --- | --- |
| ![profile](images/profile_3.jpg) | ![pulls](images/pulls_2.jpg) |
| ![exploration](images/exploration_3.jpg) | ![monument event](images/monument_event_2.jpg) |

Runnable scripts are in [examples](https://github.com/ShresthVaibhav/akef-cards/tree/main/examples), bot recipes and a
FAQ in the [wiki](https://github.com/ShresthVaibhav/akef-cards/wiki).
