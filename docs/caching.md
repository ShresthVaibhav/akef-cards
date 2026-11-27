---
title: Caching and game data
nav_order: 6
---

# Caching and game data

Three things are kept so cards come out fast, two in memory and one on disk.

## Finished cards (memory)

The last 8 cards drawn are kept. Asking for a card with the same data and options again returns
it straight away instead of drawing it, which takes a few hundred ms otherwise. Any change in the
data, the template or `hidden` draws a fresh one.

Not kept: cards where an icon failed to download (so a network blip doesn't stick), and cards with
custom `art=`, any kind. The art is loaded fresh each time, icons still come from the cache. Animated cards
are never kept either, hold on to the `AnimatedCard` if you want more exports from the same one.

## Render limit

Off by default, so only Python's own thread pool limits how many cards draw at once. For a busy bot you can
set a lower one, the rest wait their turn:

```py
cards = akef_cards.Cards(max_renders=3)
```

It's per `Cards` and covers drawing and animated card exports, not downloads or loading custom art. It lowers how much runs at
once, it doesn't make a card draw faster.

## Enka players (memory)

`cards.enka(uid)` goes through `akef.Enka`, which reuses Enka's answer for as long as Enka's own `ttl` says, usually a minute or
so. Enka asks API users to respect it, and asking sooner just returns the same data. Two calls for
the same UID at the same time share one request.

```py
cards = akef_cards.Cards(kept_cards=32)   # keep more cards, roughly 9 MB each
cards = akef_cards.Cards(cache=False)     # always fetch and draw
cards.clear_cache()
```

Both live inside one `Cards`, so keep it around for the whole bot.

## Art and icons (disk)

Downloaded once and kept in `%LOCALAPPDATA%\akef\images` on Windows or `~/.cache/akef/images`
elsewhere. Set `AKEF_CARDS_CACHE` to put it somewhere else. Splashes bigger than 1800 px are
saved at 1800 px, no card draws them larger and they load about twice as fast.

The folder is held to 15 MB by default. When it goes over, the files used longest ago are
deleted first, and anything the card being drawn needs is never removed. A splash is about 1.7 MB and
an icon about 40 KB, so 15 MB keeps roughly 6 splashes plus a few hundred icons. Raise it for a
bot that shows many different operators:

```py
cards = akef_cards.Cards(cache_mb=100)    # keep up to 100 MB of art and icons
cards = akef_cards.Cards(cache_mb=None)   # no limit
```

The last 200 images are also kept in memory, so a busy bot doesn't read them from disk again.
Art you pass with `art=` is never cached.

Cards that need the same image at the same time share one download. Files are written to a temp file first
then renamed, so nothing reads half an image, and disk reads and writes run in threads so a slow drive
doesn't freeze your bot.

## Game data (disk)

Final stats need Enka's public game tables. akef downloads them on the first card and keeps them in
`%LOCALAPPDATA%\akef\enka` or `~/.cache/akef/enka` (or `AKEF_DATA`). After a patch they refresh by
themselves when something new shows up, otherwise you get `akef.MissingGameData`. More in
[akef's docs](https://github.com/ShresthVaibhav/akef/blob/main/docs/enka.md#game-data).

To refresh by hand:

```py
changed = await cards.update()
```
