---
title: Errors
nav_order: 8
---

# Errors

Getting data can fail, drawing barely can unless you bring your own art. Most errors come from akef, see
[its errors](https://github.com/ShresthVaibhav/akef/blob/main/docs/errors.md).

| Error | When |
| --- | --- |
| `akef.PlayerNotFound` | Enka doesn't know the UID |
| `akef.ShowcaseEmpty` | the player has no operators in their showcase, or hid them |
| `akef.MissingGameData` | something from a new patch isn't in Enka's tables yet |
| `akef.GameDataError` | the saved game tables are broken, `await cards.update()` fixes it |
| `akef.UnknownCharacter` | `skport()` with an operator that isn't on the account |
| `akef.NetworkError` | couldn't reach Enka, Enka is rate limiting, or the game is in maintenance |
| `akef_cards.CardError` | `render_compare()` when nobody on the list is showcased on both accounts |
| `akef_cards.CardError` | custom art: url or text path without `allow_remote` / `allow_local`, private address, download failed, too many redirects, too big or not an image |
| `akef_cards.CardError` | animated cards: the file doesn't move, is too big or can't be read, or `fit_under()` can't get small enough |
| `ValueError` | a template, grid or wiki part that doesn't exist |
| `ValueError` | an unknown `fit` or `format` for animated cards, or an edit that leaves under 2 frames |

```py
try:
    profile = await cards.enka(uid)
except akef.PlayerNotFound:
    ...  # wrong UID
except akef.ShowcaseEmpty:
    ...  # ask them to put operators in their showcase
except akef.NetworkError:
    ...  # try again later
```
