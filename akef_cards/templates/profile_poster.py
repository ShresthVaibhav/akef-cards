from __future__ import annotations

import math

from PIL import Image, ImageDraw

from akef_cards.draw import canvas_draw, class_badge, cover, fit, font, number, shorten, stars
from akef.enka import Player, Rostered

from akef_cards.framing import GRIDS, pages as split_pages
from akef_cards.templates.profile import BOARD_W, medal_board, portrait_for
from akef_cards.templates.showcase import ELEMENT, RARITY, SIGNAL

WIDTH = {"4x2": 2240, "3x3": 1800}
SIDE = 500
PAPER = (236, 234, 226)
INK = (18, 18, 20)
SOFT_INK = (70, 64, 30)
PAD, GAP = 48, 24


def _clipped(size, cut):
    w, h = size
    mask = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (w * 2 - cut * 2, 0), (w * 2, cut * 2), (w * 2, h * 2), (0, h * 2)], fill=255)
    return mask.resize(size, Image.LANCZOS)


def _wrap(d, text, f, room, limit):
    rows, row = [], ""
    for word in text.split():
        test = f"{row} {word}".strip()
        if d.textlength(test, font=f) > room and row:
            rows.append(row)
            row = word
        else:
            row = test
    rows.append(row)
    return rows[:limit]


def _side(canvas, d, player: Player, images, h, hide_uid, compact=False):
    panel = Image.new("RGBA", (SIDE, h), SIGNAL)
    pd = ImageDraw.Draw(panel)
    for i in range(-h, SIDE, 90):
        pd.line([(i, h), (i + h, 0)], fill=(246, 192, 0), width=28)
    canvas.alpha_composite(panel)

    x, room = PAD, SIDE - PAD * 2
    top = 48 if compact else 60
    av = 128 if compact else 200
    avatar = images.get(player.avatar)
    d.rectangle((x - 6, top - 6, x + av + 6, top + av + 6), fill=INK)
    if avatar is not None:
        canvas.alpha_composite(cover(avatar, av, av, 0.2), (x, top))

    uid = "UID HIDDEN" if hide_uid else f"UID {player.uid}"
    if compact:
        tx = x + av + 24
        nf = number(56)
        while d.textlength(player.name, font=nf) > SIDE - PAD - tx and nf.size > 30:
            nf = number(nf.size - 4)
        d.text((tx - 2, top + 4), player.name, font=nf, fill=INK)
        d.text((tx, top + nf.size + 16), uid, font=font(20, "bold"), fill=INK)
        if player.region:
            d.text((tx, top + nf.size + 44), player.region.upper(), font=font(18, "semibold"), fill=SOFT_INK)
        y = top + av + 30
    else:
        y = top + av + 36
        nf = number(78)
        while d.textlength(player.name, font=nf) > room and nf.size > 40:
            nf = number(nf.size - 4)
        d.text((x - 3, y), player.name, font=nf, fill=INK)
        y += nf.size + 18
        d.text((x, y), uid, font=font(24, "bold"), fill=INK)
        if player.region:
            d.text((x, y + 32), player.region.upper(), font=font(20, "semibold"), fill=SOFT_INK)
        y += 82

    line = player.signature or player.mission
    if line:
        for row in _wrap(d, line, font(24), room, 1 if compact else 2):
            d.text((x, y), row, font=font(24), fill=INK)
            y += 32
        y += 18

    d.rectangle((x, y, SIDE - PAD, y + 4), fill=INK)
    y += 28
    facts = [("Authority", player.level), ("World level", player.world_level), ("Day", player.days),
             ("Operators", player.operators_owned), ("Weapons", player.weapons_owned), ("Files", player.files)]
    facts = [f for f in facts + list(player.regions) if f[1]]
    if compact:
        half = room // 2
        for i, (label, value) in enumerate(facts):
            r, c = divmod(i, 2)
            cx, cy = x + c * half, y + r * 72
            d.text((cx, cy), label.upper(), font=font(16, "bold"), fill=SOFT_INK)
            d.text((cx - 1, cy + 20), f"{value:,}", font=number(36), fill=INK)
        y += (len(facts) + 1) // 2 * 72
    else:
        for label, value in facts:
            d.text((x, y + 8), label.upper(), font=font(20, "bold"), fill=SOFT_INK)
            text = f"{value:,}"
            d.text((SIDE - PAD - d.textlength(text, font=number(40)), y), text, font=number(40), fill=INK)
            y += 54

    if player.medals:
        y += 20
        unit = room / BOARD_W
        y += medal_board(canvas, player.medals, images, x, y, unit, (26, 24, 18, 200))
    return y


def _tile(canvas, d, op: Rostered, images, x, y, tw, art_h):
    tint = ELEMENT.get(op.element, (120, 120, 120))
    art = Image.new("RGBA", (tw, art_h), tuple(int(PAPER[i] + (tint[i] - PAPER[i]) * 0.45) for i in range(3)) + (255,))
    portrait = portrait_for(op, images, tw, art_h, 0.08)
    if portrait is not None:
        art.alpha_composite(portrait)
    art.putalpha(_clipped((tw, art_h), 46))
    canvas.alpha_composite(art, (x, y))
    d.rectangle((x, y, x + 8, y + art_h), fill=tint)

    glyph = images.get(op.element_icon)
    if glyph is not None:
        d.rectangle((x + 8, y, x + 52, y + 44), fill=tint)
        g = fit(glyph, 28, 28)
        canvas.alpha_composite(g, (x + 30 - g.width // 2, y + 22 - g.height // 2))
    badge = class_badge(op.profession, 44, INK)
    if badge is not None:
        canvas.alpha_composite(badge, (x + 52, y))

    by = y + art_h
    d.rectangle((x, by, x + tw, by + 96), fill=INK)
    rare = RARITY.get(op.rarity, SIGNAL)
    d.rectangle((x, by, x + tw, by + 5), fill=rare)
    room = tw - 32 - op.rarity * 16
    d.text((x + 16, by + 16), shorten(d, op.name.upper(), font(28, "bold"), room), font=font(28, "bold"), fill=(245, 245, 245))
    tag = f"LV {op.level}"
    tw_tag = d.textlength(tag, font=font(20, "bold")) + 20
    d.rectangle((x + 16, by + 56, x + 16 + tw_tag, by + 84), fill=SIGNAL)
    d.text((x + 26, by + 58), tag, font=font(20, "bold"), fill=INK)
    extra = "  ".join(t for t in (f"E{op.promotion}" if op.promotion is not None else "", f"P{op.potential}") if t)
    d.text((x + 28 + tw_tag, by + 58), extra, font=font(20, "semibold"), fill=(170, 170, 176))
    stars(d, x + tw - 14 - op.rarity * 16, by + 18, op.rarity, 14, rare, gap=2)


def render(player: Player, images, *, grid: str = "4x2", page: int = 0, hide_uid: bool = False) -> Image.Image:
    pages = split_pages(player, grid)
    cols, _ = GRIDS[grid]
    chunk = pages[page]
    w = WIDTH[grid]
    gx = SIDE + PAD
    tw = (w - gx - PAD - GAP * (cols - 1)) // cols
    art_h = int(tw * 1.1)
    th = art_h + 96
    rows = max(1, math.ceil(len(chunk) / cols))
    grid_h = 160 + rows * th + (rows - 1) * GAP + 80

    probe = Image.new("RGBA", (SIDE, 3000))
    side_h = _side(probe, canvas_draw(probe), player, {}, 3000, hide_uid) + 60
    compact = side_h > grid_h
    if compact:
        side_h = _side(probe, canvas_draw(probe), player, {}, 3000, hide_uid, compact=True) + 60
    h = max(grid_h, side_h)

    canvas = Image.new("RGBA", (w, h), PAPER)
    d = canvas_draw(canvas)
    _side(canvas, d, player, images, h, hide_uid, compact)

    d.text((gx, 52), "ROSTER", font=font(64, "bold"), fill=INK)
    sub = f"{len(chunk)} operators" + (f"  ·  page {page + 1} of {len(pages)}" if len(pages) > 1 else "")
    d.text((gx + 4, 132), sub.upper(), font=font(20, "bold"), fill=(120, 116, 100))
    d.rectangle((w - PAD - 120, 64, w - PAD, 72), fill=INK)
    d.rectangle((w - PAD - 120, 82, w - PAD - 50, 90), fill=SIGNAL)
    for i, op in enumerate(chunk):
        r, c = divmod(i, cols)
        _tile(canvas, d, op, images, gx + c * (tw + GAP), 180 + r * (th + GAP), tw, art_h)

    source = "enka.network" if player.source == "enka" else "skport"
    d.text((gx, h - 52), f"VIA {source.upper()}", font=font(18, "bold"), fill=(120, 116, 100))
    d.text((w - PAD - d.textlength("AKEF", font=font(18, "bold")), h - 52), "AKEF", font=font(18, "bold"), fill=INK)
    return canvas.convert("RGB")
