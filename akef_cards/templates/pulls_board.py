from PIL import Image

from akef_cards.i18n import long_date, short_date
from akef_cards.draw import brand, canvas_draw, cover, fit, font, number, shorten
from akef_cards.gacha import Hit, PullHistory, Track
from akef_cards.templates.live_parts import bar, ring, round_avatar
from akef_cards.templates.profile import _round_mask
from akef_cards.templates.showcase import BG, CARD, ELEMENT, HAIR, MUTED, RARITY, SIGNAL, SLATE, TEXT

W = 1600
PAD = 56
GAP = 24
TRACK = (232, 230, 223)
LUCKY = (64, 170, 96)
UNLUCKY = (206, 64, 52)
ROW = 84
SHOWN = 10


def period(h: PullHistory) -> str:
    if h.after:
        return f"{long_date(h.after)} to {long_date(h.now)}"
    return f"all time · {long_date(h.now)}"


def _luck_color(hit: Hit):
    if hit.luck <= 0.5:
        return LUCKY
    if hit.luck >= 0.85:
        return UNLUCKY
    return SIGNAL


def _header(canvas, d, h: PullHistory, images, hide_uid):
    av = 104
    avatar = images.get(h.avatar)
    d.ellipse((PAD - 5, 41, PAD + av + 5, 51 + av), fill=SIGNAL)
    if avatar is not None:
        canvas.alpha_composite(round_avatar(avatar, av), (PAD, 46))
    tx = PAD + av + 30
    d.text((tx, 44), h.name, font=number(56), fill=TEXT)
    uid = f"UID {h.uid}"
    d.text((tx, 112), f"{uid}  ·  {h.region}  ·  Authority {h.level}", font=font(24), fill=MUTED)
    d.text((W - PAD - d.textlength("PULL HISTORY", font=font(20, "bold")), 56), "PULL HISTORY",
           font=font(20, "bold"), fill=SIGNAL)
    span = period(h)
    d.text((W - PAD - d.textlength(span, font=font(22)), 86), span, font=font(22), fill=MUTED)


def _stats(d, h: PullHistory, y):
    tiles = [
        ("OPERATOR PULLS", f"{h.total:,}", f"{h.free} free" if h.free else ""),
        ("6-STAR OPERATORS", str(len(h.operators)), f"{h.fives} five-stars"),
        ("PULLS PER 6-STAR", f"{h.average:.1f}" if h.operators else "-", "operators, free pulls left out"),
        ("WEAPON PULLS", f"{h.weapon_total:,}", f"{len(h.weapons)} six-stars · {h.weapon_fives} five-stars"),
    ]
    tw = (W - PAD * 2 - GAP * 3) // 4
    for i, (label, value, note) in enumerate(tiles):
        x = PAD + i * (tw + GAP)
        d.rounded_rectangle((x, y, x + tw, y + 128), 24, fill=CARD, outline=HAIR, width=2)
        d.text((x + 26, y + 20), label, font=font(17, "bold"), fill=MUTED)
        d.text((x + 24, y + 44), value, font=number(48), fill=TEXT)
        if note:
            d.text((x + 26, y + 98), note, font=font(17), fill=MUTED)
    return y + 128 + GAP


def _track(canvas, d, t: Track, x, y, w, h):
    d.rounded_rectangle((x, y, x + w, y + h), 24, fill=CARD, outline=HAIR, width=2)
    d.text((x + 26, y + 22), t.name.upper(), font=font(17, "bold"), fill=MUTED)
    d.text((x + 26, y + 46), shorten(d, t.banner, font(22, "semibold"), w - 52), font=font(22, "semibold"), fill=TEXT)
    size = 150
    gx, gy = x + 26, y + 92
    share = t.since / t.hard if t.hard else 0
    color = UNLUCKY if share >= 0.8 else SIGNAL
    canvas.alpha_composite(ring(size, share, color, TRACK, 16), (gx, gy))
    value = str(t.since)
    d.text((gx + size / 2 - d.textlength(value, font=number(46)) / 2, gy + 36), value, font=number(46), fill=TEXT)
    sub = f"/ {t.hard}"
    d.text((gx + size / 2 - d.textlength(sub, font=font(19)) / 2, gy + 92), sub, font=font(19), fill=MUTED)

    ix = gx + size + 28
    d.text((ix, gy + 4), "6-STAR GUARANTEED IN", font=font(15, "bold"), fill=MUTED)
    left = max(0, t.hard - t.since)
    d.text((ix, gy + 24), f"{left} pull{'s' if left != 1 else ''}", font=number(32), fill=TEXT)
    if t.featured_at:
        label = "SELECTOR AT" if t.name == "Standard" else "FEATURED AT"
        d.text((ix, gy + 82), f"{label} {t.featured_at}", font=font(15, "bold"), fill=MUTED)
        done = min(t.banner_pulls, t.featured_at)
        d.text((x + w - 26 - d.textlength(f"{done}/{t.featured_at}", font=font(18)), gy + 80), f"{done}/{t.featured_at}",
               font=font(18), fill=TEXT)
        bar(d, ix, gy + 110, x + w - 26 - ix, 12, done / t.featured_at, SLATE, TRACK)


def _hit_row(canvas, d, hit: Hit, images, x, y, w):
    d.rounded_rectangle((x, y, x + w, y + ROW - 10), 18, fill=CARD, outline=HAIR, width=2)
    size = ROW - 26
    icon = images.get(hit.icon)
    d.rounded_rectangle((x + 8, y + 8, x + 8 + size, y + 8 + size), 14, fill=SLATE)
    if icon is not None:
        art = cover(icon, size, size, 0.1) if icon.width == icon.height or hit.element else fit(icon, size - 6, size - 6)
        if art.size == (size, size):
            art.putalpha(_round_mask((size, size), 14))
        canvas.alpha_composite(art, (x + 8 + (size - art.width) // 2, y + 8 + (size - art.height) // 2))
    d.rounded_rectangle((x + 8, y + 8, x + 8 + size, y + 8 + size), 14, outline=RARITY[6], width=2)
    tint = ELEMENT.get(hit.element)
    if tint:
        d.ellipse((x + size - 6, y + size - 6, x + size + 10, y + size + 10), fill=tint, outline=CARD, width=2)

    tx = x + size + 26
    pill = f"{hit.pity}"
    pw = max(56, d.textlength(pill, font=number(26)) + 28)
    d.text((tx, y + 10), shorten(d, hit.name, font(24, "semibold"), w - (tx - x) - pw - 30), font=font(24, "semibold"),
           fill=TEXT)
    when = short_date(hit.when)
    sub = "  ·  ".join(s for s in (when, hit.banner) if s)
    d.text((tx, y + 42), shorten(d, sub, font(17), w - (tx - x) - pw - 30), font=font(17), fill=MUTED)
    color = _luck_color(hit)
    px = x + w - 16 - pw
    d.rounded_rectangle((px, y + 18, px + pw, y + 56), 19, fill=color)
    d.text((px + pw / 2 - d.textlength(pill, font=number(26)) / 2, y + 20), pill, font=number(26),
           fill=CARD if color != SIGNAL else SLATE)


def _column(canvas, d, title, hits, images, x, y, w):
    d.text((x, y), title, font=font(17, "bold"), fill=MUTED)
    note = "pull it came on"
    d.text((x + w - d.textlength(note, font=font(16)), y + 1), note, font=font(16), fill=MUTED)
    y += 32
    if not hits:
        d.text((x, y + 10), "none yet", font=font(22), fill=MUTED)
    for hit in hits[:SHOWN]:
        _hit_row(canvas, d, hit, images, x, y, w)
        y += ROW
    if len(hits) > SHOWN:
        d.text((x, y + 4), f"+{len(hits) - SHOWN} older", font=font(18), fill=MUTED)


def render(h: PullHistory, images, *, hide_uid: bool = False) -> Image.Image:
    tracks = h.tracks[:3]
    rows = min(SHOWN, max(len(h.operators), len(h.weapons), 1))
    more = 30 if max(len(h.operators), len(h.weapons)) > SHOWN else 0
    height = 200 + 152 + (290 + GAP if tracks else 0) + 40 + rows * ROW + more + 90
    canvas = Image.new("RGBA", (W, height), BG)
    d = canvas_draw(canvas)
    _header(canvas, d, h, images, hide_uid)
    y = _stats(d, h, 200)
    if tracks:
        tw = (W - PAD * 2 - GAP * (len(tracks) - 1)) // len(tracks)
        for i, t in enumerate(tracks):
            _track(canvas, d, t, PAD + i * (tw + GAP), y, tw, 290)
        y += 290 + GAP + 16
    cw = (W - PAD * 2 - GAP) // 2
    _column(canvas, d, "6-STAR OPERATORS", h.operators, images, PAD, y, cw)
    _column(canvas, d, "6-STAR WEAPONS", h.weapons, images, PAD + cw + GAP, y, cw)
    legend = [("lucky", LUCKY), ("normal", SIGNAL), ("near pity", UNLUCKY)]
    lx = PAD
    for text, color in legend:
        d.rounded_rectangle((lx, height - 48, lx + 18, height - 30), 5, fill=color)
        d.text((lx + 26, height - 51), text, font=font(17), fill=MUTED)
        lx += 40 + d.textlength(text, font=font(17)) + 20
    brand(d, W - PAD, height - 50, MUTED)
    return canvas.convert("RGB")
