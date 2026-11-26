import math

from PIL import Image

from akef_cards.draw import brand, canvas_draw, cover, fit, font, number, shorten, stars
from akef_cards.roster import MAX_GEAR, MAX_SKILL, Roster, Trained
from akef_cards.templates.live_parts import bar, round_avatar
from akef_cards.templates.profile import _round_mask
from akef_cards.templates.showcase import BG, CARD, ELEMENT, HAIR, MUTED, RARITY, SIGNAL, SLATE, TEXT

W = 2000
PAD = 56
GAP = 24
ROW = 132
TRACK = (232, 230, 223)
DONE = (64, 170, 96)


def _header(canvas, d, r: Roster, images, hide_uid):
    av = 104
    avatar = images.get(r.avatar)
    d.ellipse((PAD - 5, 41, PAD + av + 5, 51 + av), fill=SIGNAL)
    if avatar is not None:
        canvas.alpha_composite(round_avatar(avatar, av), (PAD, 46))
    tx = PAD + av + 30
    d.text((tx, 44), r.name, font=number(56), fill=TEXT)
    uid = f"UID {r.uid}"
    d.text((tx, 112), f"{uid}  ·  {r.region}  ·  Authority {r.level}", font=font(24), fill=MUTED)
    average = sum(o.progress for o in r.operators) / len(r.operators) if r.operators else 0
    x = W - PAD
    for label, value in (("AVERAGE", f"{average:.0%}"), ("FULLY BUILT", str(r.maxed)), ("OPERATORS", str(len(r.operators)))):
        w = max(d.textlength(value, font=number(40)), d.textlength(label, font=font(16, "bold")))
        x -= w
        d.text((x, 96), label, font=font(16, "bold"), fill=MUTED)
        d.text((x - 1, 114), value, font=number(40), fill=TEXT)
        x -= 44
    d.text((W - PAD - d.textlength("ROSTER", font=font(20, "bold")), 56), "ROSTER", font=font(20, "bold"), fill=SIGNAL)


def _row(canvas, d, op: Trained, images, x, y, w):
    h = ROW - 14
    done = op.progress >= 0.999
    d.rounded_rectangle((x, y, x + w, y + h), 20, fill=CARD, outline=DONE if done else HAIR, width=2)

    size = h - 20
    rare = RARITY.get(op.rarity, MUTED)
    d.rounded_rectangle((x + 10, y + 10, x + 10 + size, y + 10 + size), 16, fill=SLATE)
    portrait = images.get(op.portrait)
    if portrait is not None:
        face = cover(portrait, size, size, 0.1)
        face.putalpha(_round_mask((size, size), 16))
        canvas.alpha_composite(face, (x + 10, y + 10))
    d.rounded_rectangle((x + 10, y + 10, x + 10 + size, y + 10 + size), 16, outline=rare, width=3)
    tint = ELEMENT.get(op.element)
    glyph = images.get(op.element_icon)
    if tint:
        ex, ey = x + 10 + size - 26, y + 10 + size - 26
        d.ellipse((ex, ey, ex + 30, ey + 30), fill=tint, outline=CARD, width=2)
        if glyph is not None:
            g = fit(glyph, 18, 18)
            canvas.alpha_composite(g, (ex + 15 - g.width // 2, ey + 15 - g.height // 2))

    tx = x + size + 28
    d.text((tx, y + 12), shorten(d, op.name, font(26, "semibold"), 220), font=font(26, "semibold"), fill=TEXT)
    stars(d, tx + 2, y + 50, op.rarity, 14, rare, gap=2)
    d.text((tx, y + 70), f"Lv {op.level}  E{op.promotion}  P{op.potential}", font=font(19), fill=MUTED)
    pct = f"{op.progress:.0%}"
    bar(d, tx, y + h - 22, 170, 10, op.progress, DONE if done else SIGNAL, TRACK)
    d.text((tx + 180, y + h - 31), pct, font=number(20), fill=DONE if done else TEXT)

    sx = tx + 250
    d.text((sx, y + 12), "SKILLS", font=font(14, "bold"), fill=MUTED)
    for i, level in enumerate(op.skills[:4]):
        bx = sx + i * 40
        full = level >= MAX_SKILL
        d.rounded_rectangle((bx, y + 34, bx + 34, y + 68), 9, fill=SIGNAL if full else (SLATE if level >= 9 else TRACK))
        text = str(level)
        d.text((bx + 17 - d.textlength(text, font=number(20)) / 2, y + 38), text, font=number(20),
               fill=SLATE if full else (BG if level >= 9 else TEXT))
    unlocked, total = op.talents
    d.text((sx, y + 80), f"Talents {unlocked}/{total}", font=font(17), fill=TEXT if unlocked >= total else MUTED)

    wx = sx + 180
    d.rounded_rectangle((wx, y + 14, wx + 64, y + 78), 14, fill=SLATE,
                        outline=RARITY.get(op.weapon_rarity, HAIR), width=2)
    weapon = images.get(op.weapon_icon)
    if weapon is not None:
        g = fit(weapon, 54, 54)
        canvas.alpha_composite(g, (wx + 32 - g.width // 2, y + 46 - g.height // 2))
    if op.weapon:
        d.text((wx, y + 84), f"Lv {op.weapon_level}  R{op.weapon_refine}", font=font(16), fill=MUTED)
    ix = wx + 78
    d.text((ix, y + 14), shorten(d, op.weapon or "No weapon", font(18, "semibold"), w - (ix - x) - 20),
           font=font(18, "semibold"), fill=TEXT)
    if op.essence:
        d.text((ix, y + 38), shorten(d, op.essence, font(16), 150), font=font(16), fill=RARITY.get(op.essence_rarity, MUTED))

    gx = ix
    for i, (icon, level, rarity) in enumerate(op.gear[:4]):
        cx = gx + i * 44
        d.rounded_rectangle((cx, y + 62, cx + 38, y + 100), 9, fill=SLATE, outline=RARITY.get(rarity, HAIR), width=2)
        img = images.get(icon)
        if img is not None:
            g = fit(img, 30, 30)
            canvas.alpha_composite(g, (cx + 19 - g.width // 2, y + 81 - g.height // 2))
        text = str(level)
        d.text((cx + 19 - d.textlength(text, font=font(13, "bold")) / 2, y + 102), text, font=font(13, "bold"),
               fill=DONE if level >= MAX_GEAR else MUTED)
    if not op.gear:
        d.text((gx, y + 70), "Nothing equipped", font=font(16), fill=MUTED)


def render(r: Roster, images, *, hide_uid: bool = False) -> Image.Image:
    cols = 2
    rows = max(1, math.ceil(len(r.operators) / cols))
    height = 200 + rows * ROW + 90
    canvas = Image.new("RGBA", (W, height), BG)
    d = canvas_draw(canvas)
    _header(canvas, d, r, images, hide_uid)
    cw = (W - PAD * 2 - GAP) // cols
    for i, op in enumerate(r.operators):
        c, row = divmod(i, rows)
        _row(canvas, d, op, images, PAD + c * (cw + GAP), 200 + row * ROW, cw)
    d.text((PAD, height - 50), "via skport", font=font(18), fill=MUTED)
    brand(d, W - PAD, height - 50, MUTED)
    return canvas.convert("RGB")
