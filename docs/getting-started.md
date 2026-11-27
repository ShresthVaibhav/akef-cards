---
title: Getting started
nav_order: 2
---

# Getting started

```
pip install akef-cards    # pulls in akef, which gets all the data
```

Python 3.10 or newer.

## Two ways in

| | Enka UID | SKPORT account |
| --- | --- | --- |
| Needs | just the UID | the player's [akef](https://github.com/ShresthVaibhav/akef) token |
| Operators | the ones in the in-game showcase | every operator on the account |
| Cards | character (still or animated), compare, profile | everything except compare, like live status, roster, exploration, pulls and endgame |

## From a UID

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

## From a SKPORT account

```py
import akef

async with akef.Client(token) as client, akef_cards.Cards() as cards:
    card = await client.card()
    build = await cards.skport(card, "Arcane")
    image = await cards.render(build)
```

`skport()` takes a name (any case) or an operator from `card.chars`. Both sources give the same
`Build`, so every card and option below works the same for either.

## The first run

The first card downloads Enka's public game tables (a few MB) and saves them, later runs read
them from disk. Art and icons are cached on disk the same way. See [caching](caching.md).

## In a bot

Keep one `Cards` for the whole bot instead of making one per message, it holds akef's game data and
the [caches](caching.md). Use `render_bytes()` to get a file you can send straight away:

```py
cards = akef_cards.Cards()


async def on_card_command(uid, name):
    profile = await cards.enka(uid)
    build = profile.build(name)
    file = await cards.render_bytes(build, hidden=True)
    await send(file)
```

Drawing runs in a worker thread, so the bot keeps answering other messages while a card is made.
Full discord.py and Telegram examples are in [Using it in a bot](bots.md).

## Languages

Names follow the language you ask for: operators, weapons, skills, essences and gear sets from
Enka in all 14 of its languages, and whatever language the akef client asked SKPORT for. Stat
names (Enka) and elements, classes, weapon types, skill types and gear slots (SKPORT, in
Japanese, Korean and Traditional Chinese) are official translations too.

The rest of the card's labels are English until a translator fills them in, so asking for a
language that isn't complete yet warns about it:

```py
cards = akef_cards.Cards(lang="ja")   # UserWarning: card labels aren't translated into 'ja' yet, they'll be in English
```

Each label that's still missing is drawn in English and logged once on the `akef_cards` logger,
so you can see exactly what a card needed:

```
WARNING akef_cards: no de translation for 'Talents {}', drawing it in English
```

An unknown code (`lang="xx"`) warns and draws a fully English card.

Fonts for Japanese, Korean, Chinese, Thai, Russian and the Latin languages already ship with the
package, so names that come back from SKPORT in those languages still draw correctly.

### Looking for translators

Every piece of text on the cards lives in [`akef_cards/data/text.json`](../akef_cards/data/text.json).
Official names are already filled in: stat names from Enka in all 14 of its languages, and
elements, classes, weapon types, skill types and gear slots from SKPORT in Japanese, Korean and
Traditional Chinese. Everything else is still English in every language.

To add a language: translate its column, then add its code to `"_complete"` at the top of the file.
Strings with `{}` keep the `{}` where the value goes (`"Fastest clear {}"` becomes `"最速クリア {}"`).
Once a language is in `"_complete"`, `Cards(lang=...)` uses it for labels and Enka names.
Pull requests are very welcome.

Codes: `en`, `ja`, `ko`, `zh-tw`, `zh-cn`, `es`, `de`, `fr`, `id`, `pt`, `ru`, `th`, `it`, `vi`.
