# API reference

Everything is on `akef_cards.Cards` unless said otherwise. Methods marked async need `await`.

## Cards

```
Cards(*, data=None, images=None, lang="en", cache=True, kept_cards=8, cache_mb=15, max_renders=None)
```

| Argument | |
| --- | --- |
| `data` | an `akef.enka.GameData`, made for you if left out |
| `images` | an `ImageCache`, made for you if left out |
| `lang` | one of Enka's 14 language codes, see [Languages](getting-started.md#languages) |
| `cache` | `False` turns off the card and Enka caches |
| `kept_cards` | how many finished cards to keep in memory |
| `cache_mb` | disk cache size for art and icons, `None` for no limit |
| `max_renders` | max cards drawing at once, `None` (default) leaves it to Python's thread pool |

Use it as `async with akef_cards.Cards() as cards:` or keep one around for a bot.

### Getting data

| Method | Gives |
| --- | --- |
| async `enka(uid)` | `EnkaProfile` with `.builds`, `.build(name)` and `.player` |
| async `skport(card, character, stats=True)` | a `Build` for any operator on a SKPORT card |
| `skport_player(card)` | `Player` with the whole roster |
| `skport_live(card)` | `Live` |
| `skport_roster(card)` | `Roster` |
| `skport_factory(card)` | `Factory` |
| `skport_exploration(card)` | `Exploration` |
| async `skport_pulls(card, pulls, after=None)` | `PullHistory` |
| `skport_monument(card, monument)` | `Monument` |
| `skport_contract(card)` | `Contracts` |
| `skport_contract_detail(card, detail)` | `ContractDetail` |
| `wiki(item, index=None)` | `WikiPage` |

### Drawing

All async. Every one takes `hidden=True` except the wiki ones.

| Method | Templates | Gives |
| --- | --- | --- |
| `render(build, template=1, art=None, allow_remote=False, allow_local=False)` | 1, 2 | image |
| `render_compare(first, second, characters, template=1)` | 1, 2 | list of images |
| `render_profile(player, template=1, grid="4x2")` | 1, 2, 3 | list of images |
| `render_live(live, template=1)` | 1, 2 | image |
| `render_roster(roster)` | | image |
| `render_factory(factory, template=1)` | 1, 2 | image |
| `render_exploration(exploration, template=1)` | 1, 2, 3 | image |
| `render_pulls(history, template=1)` | 1, 2 | image |
| `render_monument(monument)` | | image |
| `render_monument_event(monument, event=None, template=1)` | 1, 2 | image, or a list for a list |
| `render_contract(contracts, template=1)` | 1, 2 | image |
| `render_contract_detail(detail, template=1)` | 1, 2 | image |
| `render_wiki(page, part="overview", template=1)` | 1, 2 | image |
| `render_wiki_pages(page, parts=None, template=1)` | 1, 2 | list of images |

### Files

| Method | Gives |
| --- | --- |
| async `render_bytes(data, format="PNG", **options)` | `BytesIO` with a name, a list for profiles and wiki pages |
| async `render_compare_bytes(first, second, characters, format="PNG", **options)` | list of `BytesIO` |
| async `render_monument_event_bytes(monument, event=None, format="PNG", **options)` | `BytesIO` or a list |

### Animated

| Method | Gives |
| --- | --- |
| async `animation_info(art, template=1, allow_remote=False, allow_local=False)` | `AnimationInfo` |
| async `animated_card(build, art, template=1, hidden=False, fit="contain", focus=(0.5, 0.5), width=1000, frame_step=2, allow_remote=False, allow_local=False)` | `AnimatedCard` |
| async `render_animated(build, art, format="WEBP", quality=80, **options)` | `BytesIO` |

### Other

| Method | |
| --- | --- |
| `clear_cache()` | forget cached cards and Enka answers |
| async `update()` | refresh game data, `True` if anything changed |

## AnimatedCard

Frozen, every edit returns a new one. See [Animated operator](cards/animated.md).

| | |
| --- | --- |
| `frame_count`, `duration`, `size` | what you've got, duration in seconds |
| `trim(start=0, end=None)` | keep that part |
| `speed(factor)` | faster or slower |
| `reverse()`, `bounce()` | play backwards, forward then back |
| `hold(seconds, at="end")` | freeze on the first or last frame |
| `loops(count)` | `0` forever |
| `resize(width)` | never upscales |
| `still(at=0)` | Pillow image |
| async `to_bytes(format="WEBP", quality=80)` | `BytesIO` |
| async `save(path, quality=80)` | `Path` |
| async `fit_under(max_mb, format="WEBP", min_width=500)` | `BytesIO` with `.settings` |

## AnimationInfo

`width`, `height`, `frames`, `duration` (seconds) and `fit` (what `fit="auto"` would pick).

## ImageCache

```
ImageCache(path=None, *, timeout=40, max_mb=15, kept_in_memory=200)
```

The disk cache for art and icons, see [Caching](caching.md). `size()` gives its size in bytes, `clear()` empties it.

## CardError

`akef_cards.CardError` is raised for card problems: bad or blocked custom art, animations that can't be used, and
compares with nobody in common. See [Errors](errors.md).

## Data classes

`Live`, `Meter`, `Roster`, `Factory`, `Exploration`, `PullHistory`, `Monument`, `Event`, `Stage`, `Contracts`
and `ContractDetail` are all importable from `akef_cards`, see [Data](data.md).
