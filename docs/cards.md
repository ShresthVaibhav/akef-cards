# Cards

Every `render_*` method returns a Pillow image. All of them take `hidden=True` to blur the UID
number on the card.

## Character card

```py
image = await cards.render(build, template=1, art=None, hidden=False)
file = await cards.render_bytes(build, format="PNG")
```

One operator: splash art, element, level, promotion and potential, final stats, skills with
levels, talents, weapon with its skill values, essence with its points, and gear with every stat
line and its level.

| Option | |
| --- | --- |
| `template` | `1` light showcase, `2` dark in-game style with angled panels |
| `art` | your own art instead of the splash: a Pillow image, bytes, a `Path`, or a path / URL string |
| `allow_local` | needed for a path as a string, never turn it on for user input |
| `allow_remote` | needed for a URL, private and local addresses stay blocked |
| `hidden` | blur the UID number |

`render_bytes()` takes the same options plus `format` and gives a `BytesIO` with a file name set,
ready for discord.py and friends. It isn't only for operators: hand it a `Live`, `Roster`, `Factory`, `Exploration`,
`PullHistory`, `Contracts`, `ContractDetail` or `Monument` and you get that card as a file, a `Player` or `WikiPage`
and you get a list with one file a page. `format="JPEG"` works too, smaller files for bots. `render_compare_bytes()` and `render_monument_event_bytes()` do the
same for those two.

Sources: `cards.enka(uid).builds` or `cards.skport(card, name)`.

## Animated card

```py
card = await cards.render_animated(build, Path("art.gif"), format="WEBP", fit="contain", width=1000)
```

The operator card with a moving gif or webp as the art. Returns a `BytesIO` w/ a file name.

| Option | |
| --- | --- |
| `template` | `1` light (default), `2` dark in-game style |
| `format` | `"WEBP"` (default) or `"GIF"`, GIF is a lot bigger and only has 256 colours |
| `fit` | `"contain"` whole animation on a blurred backdrop, `"cover"` fill and crop |
| `width` | output width in px, never upscales the card |
| `quality` | webp quality |
| `frame_step` | `2` by default, drops every 2nd frame. `1` keeps them all, bigger and slower |
| `hidden`, `allow_local`, `allow_remote` | same as the still card |

If that still leaves over 120 frames it skips more. The loop stays the same length either way. Very big animations get a `CardError`.

## Compare card

```py
pages = await cards.render_compare(4727743200, 4727743200, "Yvonne")
pages = await cards.render_compare(uid_a, uid_b, ["Gilberta", "chr_0019_karin"], template=2, hidden=True)
```

| `template` | |
| --- | --- |
| `1` | light, loadouts down the sides with stats and skills in the middle |
| `2` | dark split: the art down the middle, each player's stat tiles, skills, weapon and gear on their half |

Two players' builds of the same operator side by side: level, promotion, potential and talents for
each, every stat with bars and the higher value marked, skill levels, weapon with essence, and gear.
Give it two UIDs (or two profiles from `cards.enka()`) and one operator or a list, by name or id.
You get one card per operator that both players showcase, the rest are skipped with a warning, and
if none are on both you get a `CardError`.

## Profile card

```py
pages = await cards.render_profile(player, template=1, grid="4x2")
```

Player name, avatar, signature, Authority and world level, days played, region levels, owned
counts, showcased medals and a grid of operators. Always returns a list of pages.

| Option | |
| --- | --- |
| `template` | `1` light, `2` dark with full-height portraits, `3` yellow poster with the player down the side |
| `grid` | `"4x2"` (8 a page) or `"3x3"` (9 a page) |

Sources:

```py
player = (await cards.enka(uid)).player       # the showcase, always one page
player = cards.skport_player(await client.card())   # every operator, split into pages
```

SKPORT profiles put the operators picked for the SKPORT profile first, then the rest by rarity,
level and potential. Enka has no half-body portraits, so each tile is cut from the operator's
splash around the face.

## Live status card

SKPORT only.

```py
live = cards.skport_live(await client.card())
image = await cards.render_live(live)
```

Sanity with time until full, daily activity, weekly routine, battle pass, credits with the next
refresh, the current War Echoes cycle with stars per stage, and the running Contingency Contract.
Times are worked out from SKPORT's own clock.

## Monument card

SKPORT only.

```py
monument = cards.skport_monument(await client.card(), await client.monument())
image = await cards.render_monument(monument)
```

One tile per event with its poster, medal, normal and Agony clears per stage and the fastest clear.
Events never played are greyed out. Stage times and teams are still on `monument.events` for your
own use.

## Monument event card

```py
image = await cards.render_monument_event(monument)                          # the latest event
image = await cards.render_monument_event(monument, "Marked by Dark Shadows", template=2)
images = await cards.render_monument_event(monument, ["Searing Scars", 0])  # a list in, a list out
```

One event in full: the poster as a banner, the rules, and each stage with its boss, clear time and
the team that cleared it as big portraits. Agony clears get a red frame and tag. With no event it
picks the running one, or the one that started last. `template` is `1` light or `2` dark.

## Factory card

SKPORT only.

```py
factory = cards.skport_factory(await client.card())
image = await cards.render_factory(factory, template=1)
```

Each region with its level, funds and how much is explored, every settlement with its officer,
level and stock, exploration per area, and the Dijiang cabins with their crew.

| Option | |
| --- | --- |
| `template` | `1` light, `2` dark |

## Pull history card

SKPORT only.

```py
pulls = await client.pulls()
history = await cards.skport_pulls(await client.card(), pulls)
image = await cards.render_pulls(history, template=1)

recent = await cards.skport_pulls(card, pulls, after=date(2026, 11, 1))
```

Totals, the pull each 6-star came on (green lucky, yellow normal, red near pity), and current pity
for limited, standard and the latest weapon banner. With `after=` the card only lists and counts
pulls from that date, pity is still worked out from the whole history you pass in.

| Option | |
| --- | --- |
| `template` | `1` light board, `2` yellow poster with your latest 6-star down the side |

## Contingency Contract card

SKPORT only.

```py
contracts = cards.skport_contract(await client.card())
image = await cards.render_contract(contracts, template=1)
```

The running contract with its banner art, best score, attempts, weekly, indicator and stage
missions, the medal (faded until it's earned) and the time left.

| Option | |
| --- | --- |
| `template` | `1` light board, `2` dark |


## Contract detail card

```py
detail = cards.skport_contract_detail(await client.card(), await client.contract())
image = await cards.render_contract_detail(detail, template=2)
```

Your current Contingency Contract on one card: a banner with the best risk, attempts and missions,
then your best 4 battles by risk, each with its team as big portraits, the time, wave and date.
Needs `client.contract()` from akef. `template` is `1` light or `2` dark.

## Exploration

```py
image = await cards.render_exploration(cards.skport_exploration(card), template=1, hidden=False)
```

Every area per region with puzzles, chests, gear chests, fragments, blackboxes and aurylenes.

| `template` | |
| --- | --- |
| `1` | to-do: unfinished areas get big boxes with a row per kind, fewest left first. Cleared ones stay compact |
| `2` | dark, a ring plus all six counts for every area |
| `3` | compact yellow poster, 3 areas a row. The top banner shows what each icon means, kinds w/ stuff left are blacked out |

All three show the six counts for every area. 1 and 2 also total them per region.
