# akef-cards

Image cards for Arknights: Endfield. Operator builds, profiles, pull history, endgame stuff and a few more,
plus animated operator cards from your own gif.

Operator and profile cards only need an Enka UID. Everything else reads your SKPORT account through
[akef](https://github.com/ShresthVaibhav/akef), this library just draws.

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

![operator card](images/operator_1.jpg)

## Docs

- [Getting started](getting-started.md): Enka UID or SKPORT account, your first card, using it in a bot
- [Cards](cards.md): every card, its templates and options, animated cards included
- [Data](data.md): what the cards are drawn from
- [Caching and game data](caching.md): what's kept where, and what happens after a patch
- [Errors](errors.md)

## Some cards

| | |
| --- | --- |
| ![operator dark](images/operator_2.jpg) | ![profile](images/profile_1.jpg) |
| ![pulls](images/pulls_2.jpg) | ![exploration](images/exploration_3.jpg) |
| ![monument event](images/monument_event_2.jpg) | ![contract detail](images/contract_detail_1.jpg) |

Every card with all its templates is in the
[README](https://github.com/ShresthVaibhav/akef-cards#every-card), runnable scripts are in
[examples](https://github.com/ShresthVaibhav/akef-cards/tree/main/examples) and there's a
[wiki](https://github.com/ShresthVaibhav/akef-cards/wiki) with bot recipes and a FAQ.
