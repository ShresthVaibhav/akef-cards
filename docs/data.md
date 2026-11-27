---
title: Data
nav_order: 7
---

# Data

Builds, players, final stats and wiki pages are akef's, see its
[Enka and final stats docs](https://github.com/ShresthVaibhav/akef/blob/main/docs/enka.md) and
[how the stats are checked](https://github.com/ShresthVaibhav/akef/blob/main/docs/stats.md).

```py
build = profile.build("Arcane")       # or await cards.skport(card, "Arcane"), both are akef.enka.Build
build.stats.atk                       # 4802
build.gear[1].lines                   # [GearLine(name="Will", text="+84", level=3), ...]
```

What akef-cards adds are the shapes some cards are drawn from. The `skport_*` methods make them out of
akef's SKPORT models, and you can read them without drawing anything.

| | |
| --- | --- |
| `Live` | `sanity` and `meters` (each with `current`, `total`, `share`, `done`), `full_at`, `echoes`, `contract` |
| `Roster` | everyone owned with level, promotion, skills, weapon and gear, and how trained they are |
| `Monument` | `events`, each with `stages`, `cleared` (normal, agony), `fastest`, medal info. `monument.event(name)` |
| `Factory` | `regions` with `posts` (settlements), `areas` and `explored`, plus `cabins` |
| `Exploration` | `regions` and `areas`, each area with `kinds` (found, total), plus `found`, `total` and `kind_totals()` |
| `PullHistory` | six stars per banner with pity, luck and the time range |
| `Contracts`, `ContractDetail` | the contract summary, and runs with teams, buffs and enemies |

Splitting a roster into profile pages works like the card does it:

```py
from akef_cards.framing import pages

pages(player, "3x3")   # lists of 9
```
