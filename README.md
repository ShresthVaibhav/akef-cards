# akef-cards

Image cards for Arknights: Endfield. Operator builds, profiles, pull history, endgame stuff and a few more.
Operator and profile cards only need an Enka UID, no login. The rest read your SKPORT account.

All the data side (SKPORT, Enka, final stats, the wiki) lives in [akef](https://github.com/ShresthVaibhav/akef).
This one only draws. If you just want the numbers, use akef on its own.

## Install

```
pip install akef-cards
```

Pulls in akef too. Python 3.10+. Longer docs in [`docs/`](https://github.com/ShresthVaibhav/akef-cards/blob/main/docs/README.md)
(also on [the docs site](https://shresthvaibhav.github.io/akef-cards/)), runnable scripts in
[`examples/`](https://github.com/ShresthVaibhav/akef-cards/tree/main/examples) and bot recipes plus a FAQ in the
[wiki](https://github.com/ShresthVaibhav/akef-cards/wiki).

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

Enka only sees the operators in the in-game showcase, max 4. Thats how enka works, not our fault. For the whole
roster use a SKPORT token:

```py
import akef

async with akef.Client(token) as client, akef_cards.Cards() as cards:
    card = await client.card()
    build = await cards.skport(card, "Arcane")
    image = await cards.render(build)
```

## Every card

Each `render_*` gives back a Pillow image, or a list when theres more than one page. `template=` picks the look.

| Card | Call | Templates | Needs |
| --- | --- | --- | --- |
| Operator | `render(build)` | 1 light, 2 dark in-game | enka or skport |
| Compare | `render_compare(uid_a, uid_b, "Yvonne")` | 1 landscape, 2 dark split | enka |
| Profile | `render_profile(player)` | 1 light, 2 dark, 3 yellow poster | enka or skport |
| Roster | `render_roster(roster)` | 1 | skport |
| Pull history | `render_pulls(history)` | 1 board, 2 poster | skport |
| Live status | `render_live(live)` | 1 light, 2 dark | skport |
| Monument | `render_monument(monument)` | 1 | skport |
| Monument event | `render_monument_event(monument)` | 1 light, 2 dark | skport |
| Factory | `render_factory(factory)` | 1 light, 2 dark | skport |
| Exploration | `render_exploration(exploration)` | 1 to-do, 2 dark rings, 3 yellow poster | skport |
| Contingency Contract | `render_contract(contracts)` | 1 light, 2 dark | skport |
| Contract detail | `render_contract_detail(detail)` | 1 light, 2 dark | skport |
| Wiki | `render_wiki_pages(page)` | 1 light, 2 dark | skport wiki |

## Operator

```py
image = await cards.render(build)                # light
image = await cards.render(build, template=2)    # dark, game menu style
```

Stats are checked against the in-game screen and they match, rounding and all. Enka's site gives Gilberta's ult
gain a talent bonus the game doesnt, so for her we go with the game.

<details>
<summary>Template 1</summary>

![operator light](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/operator_1.jpg)
</details>

<details>
<summary>Template 2</summary>

![operator dark](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/operator_2.jpg)
</details>

### Custom art

Dont like the default splash? Pass `art=` with your own. A file path, a url, raw bytes or a Pillow image all
work, on both templates. On template 1 the art takes the whole left side, no circles behind it.

```py
image = await cards.render(build, art=Path("my_art.png"))
image = await cards.render(build, art="my_art.png", allow_local=True)
image = await cards.render(build, art="https://example.com/art.png", allow_remote=True)
image = await cards.render(build, art=attachment_bytes, template=2)   # from a bot upload
image = await cards.render(build, art=pillow_image)                   # edit it first if you want
```

Text urls and paths are off by default, so a bot cant be tricked into opening your files by whatever someone
types. Dont turn on `allow_local` for user input, or wrap their text in `Path()`. With `allow_remote` private
and local addresses are still blocked, downloads stop at 15 MB and 3 redirects, and proxy env vars arent used.
Art over 40 megapixels is rejected.

Custom art is never saved to the disk cache. Some image hosts block scripts, if a url fails download it
yourself and pass the bytes. [`custom_art.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/custom_art.py) makes the ones below.

<details>
<summary>Custom art examples</summary>

![gilberta custom art, template 1](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/art_pigeonfight99_1.jpg)
![gilberta custom art, template 2](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/art_pigeonfight99_2.jpg)

art by pigeonfight99

![gilberta custom art, template 1](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/art_kisaragi_pana_1.jpg)
![gilberta custom art, template 2](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/art_kisaragi_pana_2.jpg)

art by kisaragi_pana
</details>

### Animated art

Give it a gif or animated webp and the art moves, everything else stays put. Works on both templates,
`template=2` for the dark one.

```py
card = await cards.render_animated(build, Path("art.gif"))          # BytesIO named card.webp
card = await cards.render_animated(build, attachment_bytes, format="GIF")
```

WEBP is the default, its much smaller and looks better than GIF. `fit="contain"` (default) shows the whole
animation with a blurred copy filling the rest, `fit="cover"` fills the panel and crops. `width=` sets the output
width (1000 by default). Every 2nd frame is dropped to keep it small, same speed, just a bit less smooth.
`frame_step=1` keeps them all. Text urls and paths need `allow_remote` / `allow_local` same as `art=`. Takes a few
seconds and isnt cached. Bad or still files give a `CardError`.

For more control, `animated_card()` gives you a card you can trim, speed up, reverse, bounce, loop or shrink
to a size limit before exporting, see [animated card docs](https://github.com/ShresthVaibhav/akef-cards/blob/main/docs/cards.md#animated-card).

```py
card = await cards.animated_card(build, Path("art.gif"), fit="auto")
await card.speed(1.25).bounce().save("card.webp")
small = await card.fit_under(1.0)    # under 1 MB
```

[`animated.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/animated.py)

<details>
<summary>Animated, template 1 and 2</summary>

![animated operator light](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/animated_1.webp)
![animated operator dark](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/animated_2.gif)
</details>

## Compare

Two UIDs and an operator, or a list of them. One card per operator that both players are showing. If only one
of them has it, its skipped with a warning.

```py
pages = await cards.render_compare(uid_a, uid_b, "Yvonne")
pages = await cards.render_compare(uid_a, uid_b, ["Gilberta", "Yvonne"], template=2)
```

<details>
<summary>Template 1</summary>

![compare landscape](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/compare_1.jpg)
</details>

<details>
<summary>Template 2</summary>

![compare split](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/compare_2.jpg)
</details>

## Profile

```py
[image] = await cards.render_profile(profile.player)                        # enka, always one page
pages = await cards.render_profile(cards.skport_player(card), grid="3x3")   # skport, whole roster so many pages
```

SKPORT gives the full roster, so a big account becomes a few images with 8 or 9 operators each. Enka is one page
since it only has the showcase.

<details>
<summary>Template 1</summary>

![profile light](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/profile_1.jpg)
</details>

<details>
<summary>Template 2</summary>

![profile dark](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/profile_2.jpg)
</details>

<details>
<summary>Template 3</summary>

![profile poster](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/profile_3.jpg)
</details>

## SKPORT cards

```py
card = await client.card()

image = await cards.render_live(cards.skport_live(card), template=2)
image = await cards.render_roster(cards.skport_roster(card))
image = await cards.render_factory(cards.skport_factory(card))
image = await cards.render_pulls(await cards.skport_pulls(card, await client.pulls()))
image = await cards.render_pulls(await cards.skport_pulls(card, pulls, after=date(2026, 10, 1)))  # just a period
```

<details>
<summary>Live status</summary>

![live light](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/live_1.jpg)
![live dark](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/live_2.jpg)
</details>

<details>
<summary>Roster</summary>

![roster](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/roster.jpg)
</details>

<details>
<summary>Factory</summary>

![factory light](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/factory_1.jpg)
![factory dark](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/factory_2.jpg)
</details>

<details>
<summary>Pull history</summary>

![pulls board](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/pulls_1.jpg)
![pulls poster](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/pulls_2.jpg)
</details>

## Exploration

Its own card, with all six kinds counted per area. Template 1 gives unfinished areas the most room, 2 puts a ring on every
area, 3 is a poster with your overall number.

```py
exploration = cards.skport_exploration(card)
image = await cards.render_exploration(exploration, template=1)
```

<details>
<summary>Template 1, to-do</summary>

![exploration to-do](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/exploration_1.jpg)
</details>

<details>
<summary>Template 2, rings</summary>

![exploration rings](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/exploration_2.jpg)
</details>

<details>
<summary>Template 3, poster</summary>

![exploration poster](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/exploration_3.jpg)
</details>

## Monument

The overview shows every event at once. The event card goes deep on one: each stage, the clear time and the team
you used, as big portraits so you can flex. Agony clears get a red frame.

```py
monument = cards.skport_monument(card, await client.monument())
overview = await cards.render_monument(monument)

latest = await cards.render_monument_event(monument)                         # newest event
one = await cards.render_monument_event(monument, "Marked by Dark Shadows")
many = await cards.render_monument_event(monument, ["Searing Scars", 0])     # list in, list out
```

<details>
<summary>Overview</summary>

![monument](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/monument.jpg)
</details>

<details>
<summary>Event, light and dark</summary>

![monument event light](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/monument_event_1.jpg)
![monument event dark](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/monument_event_2.jpg)
</details>

## Contingency Contract

A summary card, and a detail one with your best 4 battles and the teams you ran.

```py
image = await cards.render_contract(cards.skport_contract(card))

detail = cards.skport_contract_detail(card, await client.contract())
image = await cards.render_contract_detail(detail, template=2)
```

<details>
<summary>Summary</summary>

![contract light](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/contract_1.jpg)
![contract dark](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/contract_2.jpg)
</details>

<details>
<summary>Detail</summary>

![contract detail light](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/contract_detail_1.jpg)
![contract detail dark](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/contract_detail_2.jpg)
</details>

## Wiki

An operator's page from SKPORT's official wiki, split in six cards: overview, skills, talents, growth, profile
and lore.

```py
from akef import WikiPart

ops = await client.wiki("operators")
item = await client.wiki_item(next(o for o in ops if o.name == "Arcane").id)
page = cards.wiki(item, await client.wiki_index())          # same as akef.wiki_page(...)
pages = await cards.render_wiki_pages(page)                                    # all six
pages = await cards.render_wiki_pages(page, [WikiPart.SKILLS, WikiPart.LORE])  # just these
image = await cards.render_wiki(page, "talents", template=2)                   # one
```

`wiki_index()` is one more round of requests that names the materials and weapons a page links to. Talents,
growth and profile need it, the other three dont.

<details>
<summary>Overview, light and dark</summary>

![wiki light](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/wiki_1.jpg)
![wiki dark](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/wiki_2.jpg)
</details>

<details>
<summary>Talents</summary>

![wiki talents](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/wiki_talents.jpg)
</details>

## Options

| Option | Where | What it does |
| --- | --- | --- |
| `template=` | every card with more than one look | picks the look |
| `hidden=True` | every card | blurs the UID |
| `art=` | operator card | your own art instead of the splash: image, bytes, path or url |
| `grid="3x3"` | profile | 9 operators a page instead of 8 |
| `lang=` | `Cards(lang="ja")` | names in that language |

`render_bytes()` gives a `BytesIO` with a file name, ready to send if youre making a bot, and works for every card. Every `Build` also has
the plain numbers: `build.stats.atk`, `build.gear[0].lines`, `build.skills` and so on. Those come from akef,
see its [Enka and final stats docs](https://github.com/ShresthVaibhav/akef/blob/main/docs/enka.md).

<details>
<summary>hidden=True</summary>

![hidden uid](https://raw.githubusercontent.com/ShresthVaibhav/akef-cards/main/docs/images/hidden.jpg)
</details>

## Caching

On by default, nothing to set up.

| What | Where | How long |
| --- | --- | --- |
| splash art and icons | disk, survives restarts | until the folder hits 15 MB, oldest used go first |
| finished cards | memory | last 8 |
| enka player data | memory | enka's own ttl |
| game data tables | disk | until a patch needs new ones |

Images are saved by their file name, not the link, so when SKPORT moves a link it still hits the cache. Art you
pass with `art=` is never saved, and animated cards arent cached at all.
Cards that need the same image at once share one download.

```py
cards = akef_cards.Cards(cache_mb=100, kept_cards=32)   # more room
cards = akef_cards.Cards(cache_mb=None)                 # no size limit
cards = akef_cards.Cards(cache=False)                   # always fetch and draw fresh
cards = akef_cards.Cards(max_renders=3)                 # draw/export max 3 at once, off by default
cards.clear_cache()
```

## Game data

Final stats are worked out by akef from Enka's public game data. The first card downloads the tables and keeps
them on disk, after a patch they refresh by themselves when something new shows up. If enka didnt add it yet
either you get `akef.MissingGameData`. Refresh by hand with `await cards.update()`. Details in
[akef's docs](https://github.com/ShresthVaibhav/akef/blob/main/docs/enka.md#game-data).

## Every method

<details>
<summary>All of them in one table</summary>

| Method | Does |
| --- | --- |
| `enka(uid)` | Enka profile: showcased builds plus `player` for the profile card |
| `skport(card, name, stats=True)` | a build for any operator on a SKPORT card |
| `skport_player(card)` | profile data with the whole roster |
| `skport_live(card)` | sanity, dailies, weeklies, battle pass, echoes, contract |
| `skport_roster(card)` | everyone you own with their training |
| `skport_factory(card)` | regions, settlements and Dijiang |
| `skport_exploration(card)` | every area with what youve found |
| `skport_pulls(card, pulls, after=None)` | pull history ready to draw |
| `skport_monument(card, monument)` | monument events and clears |
| `skport_contract(card)` | contract summary |
| `skport_contract_detail(card, detail)` | contract runs and teams |
| `wiki(item, index=None)` | a readable wiki page |
| `render(build, template, art, hidden)` | operator card |
| `render_animated(build, art, template, ...)` | operator card with moving art, gives a file |
| `animated_card(build, art, template, ...)` | same card as an `AnimatedCard` you can edit and export |
| `animation_info(art)` | size, frames, length and suggested fit of an animation |
| `render_bytes(card, format="PNG", ...)` | any card as a file for bots, `render_compare_bytes()` and `render_monument_event_bytes()` for those two |
| `render_compare(a, b, names, template)` | two players side by side |
| `render_profile(player, template, grid)` | profile pages |
| `render_live(live, template)` | live status |
| `render_roster(roster)` | roster board |
| `render_factory(factory, template)` | factory |
| `render_exploration(exploration, template)` | exploration |
| `render_pulls(history, template)` | pull history |
| `render_monument(monument)` | every monument event |
| `render_monument_event(monument, event, template)` | one event, or a list |
| `render_contract(contracts, template)` | contract summary |
| `render_contract_detail(detail, template)` | best 4 contract runs |
| `render_wiki(page, part, template)` | one wiki card |
| `render_wiki_pages(page, parts, template)` | several wiki cards |
| `update()` | refresh game data |
| `clear_cache()` | forget cached cards and Enka answers |

Every `render_*` takes `hidden=True` too, except the wiki ones, theres no UID on those.
</details>

## Languages

Names follow Enka's 14 languages. Our own labels are English for now, anything not translated is drawn in English
and logged so you can see whats missing. Translators welcome, see [Languages](https://github.com/ShresthVaibhav/akef-cards/blob/main/docs/getting-started.md#languages).

## Examples

| Script | Shows |
| --- | --- |
| [`enka_uid.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/enka_uid.py) | every showcased operator from a UID |
| [`skport.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/skport.py) | operator cards from a SKPORT account |
| [`profile.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/profile.py) | profile from enka and from skport |
| [`compare.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/compare.py) | two players side by side |
| [`endgame.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/endgame.py) | monument and contract cards |
| [`wiki.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/wiki.py) | all six wiki cards |
| [`every_card.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/every_card.py) | every card in every template |
| [`caching.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/caching.py) | how fast the cache makes things |
| [`custom_art.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/custom_art.py) | Gilberta with fan art from a path, bytes or pillow image |
| [`animated.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/animated.py) | operator card with your gif as the art |
| [`options.py`](https://github.com/ShresthVaibhav/akef-cards/blob/main/examples/options.py) | hidden uid, bytes for bots, languages |

Scripts that need SKPORT read the token from `SKPORT_TOKEN` or `~/.skport_token`.

## Running the tests

```
pip install -e .[dev]
pytest
```

They run offline on saved data in `tests/data`, split by card type.

## License

MIT. Ships [Barlow](https://github.com/jpt/barlow), [Fira Sans](https://github.com/mozilla/Fira),
[Noto Sans JP, KR, TC, SC](https://github.com/notofonts/noto-cjk) and [Noto Sans Thai](https://github.com/notofonts/thai)
under the SIL Open Font License (see `akef_cards/fonts/`). Game data and art come from
[Enka.Network](https://enka.network) and the game itself, big thanks to enka fr. Gilberta fan art in the custom
art example by pigeonfight99 and kisaragi_pana, it belongs to them and isnt covered by the MIT license.

Not affiliated with Hypergryph or Gryphline.
