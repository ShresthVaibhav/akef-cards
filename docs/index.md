---
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

<div markdown>

# akef<span>-cards</span>

Image cards for Arknights: Endfield. Operator builds, profiles, pulls, exploration and endgame, plus
animated operator cards from your own gif.

[Get started](getting-started.md){ .md-button .md-button--primary }
[Every card](cards/index.md){ .md-button }

</div>

![operator card](images/operator_2.jpg){ .no-zoom }

</div>

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

Operator, compare and profile cards only need an Enka UID. Everything else reads a SKPORT account through
[akef](https://github.com/ShresthVaibhav/akef), this library just draws.

## The cards

<div class="grid cards" markdown>

-   :material-account-star: **[Operator](cards/operator.md)**

    Final stats, skills, talents, weapon and gear. 2 templates, custom art too.

    ![](images/operator_1.jpg){ .no-zoom }

-   :material-movie-open: **[Animated operator](cards/animated.md)**

    Your gif as the art. Trim, speed up, bounce, keep it under upload limits.

    ![](images/animated_2.gif){ .no-zoom }

-   :material-scale-balance: **[Compare](cards/compare.md)**

    Two players' builds of the same operator side by side.

    ![](images/compare_2.jpg){ .no-zoom }

-   :material-card-account-details: **[Profile](cards/profile.md)**

    Player info, medals and the roster, 3 templates.

    ![](images/profile_3.jpg){ .no-zoom }

-   :material-heart-pulse: **[Live status](cards/live.md)**

    Sanity, dailies, weeklies, battle pass and more.

    ![](images/live_2.jpg){ .no-zoom }

-   :material-account-group: **[Roster](cards/roster.md)**

    Everyone you own and how trained they are.

    ![](images/roster.jpg){ .no-zoom }

-   :material-factory: **[Factory](cards/factory.md)**

    Regions, settlements and the Dijiang cabins.

    ![](images/factory_2.jpg){ .no-zoom }

-   :material-map-search: **[Exploration](cards/exploration.md)**

    All six collectible kinds per area, 3 templates.

    ![](images/exploration_3.jpg){ .no-zoom }

-   :material-dice-multiple: **[Pull history](cards/pulls.md)**

    Every 6-star, luck and current pity.

    ![](images/pulls_2.jpg){ .no-zoom }

-   :material-trophy: **[Monument](cards/monument.md)**

    Every event at once, or one event with your teams.

    ![](images/monument_event_2.jpg){ .no-zoom }

-   :material-sword-cross: **[Contingency Contract](cards/contract.md)**

    The running contract and your best 4 battles.

    ![](images/contract_detail_2.jpg){ .no-zoom }

-   :material-book-open-variant: **[Wiki](cards/wiki.md)**

    An operator's official wiki page as six cards.

    ![](images/wiki_2.jpg){ .no-zoom }

</div>

Runnable scripts are in [examples](https://github.com/ShresthVaibhav/akef-cards/tree/main/examples), bot recipes and a
FAQ in the [wiki](https://github.com/ShresthVaibhav/akef-cards/wiki).
