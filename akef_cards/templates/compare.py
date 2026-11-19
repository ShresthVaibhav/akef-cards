from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from akef.enka.build import Build
from akef_cards.draw import canvas_draw, class_badge, fit, font, icon, number, potential_mark, shorten, stars
from akef_cards.templates.parts import (
    boxed, element_badge, face_crop, fade, fit_name, gear_block, ink_bottom, palette, two_pass, weapon_block,
)
from akef_cards.templates.talents import draw_row
from akef_cards.templates.showcase import BG, CARD, ELEMENT, EXTRA_STATS, HAIR, MUTED, RARITY, SIGNAL, SLATE, TEXT

W = 2100
MID = W // 2
SIDE = 660
LOSE = (206, 204, 196)
TRACK = (230, 228, 221)
STAR_DIM = (200, 198, 190)


def _card(canvas, box):
    ImageDraw.Draw(canvas).rounded_rectangle(box, 18, fill=CARD, outline=HAIR, width=2)


P = palette(text=TEXT, dim=MUTED, accent=SIGNAL, on_accent=SLATE, line=HAIR, tile=SLATE, star_dim=STAR_DIM,
            pip=SLATE, pip_dim=HAIR, essence=(196, 136, 0), card=_card)
FLAT = ("hp", "atk", "defense", "strength", "agility", "intellect", "will")


def _rows(a: Build, b: Build):
    if a.stats is None or b.stats is None:
        return []
    rows = [("HP", "hp"), ("ATK", "atk"), ("DEF", "defense"), ("STR", "strength"), ("AGI", "agility"),
            ("INT", "intellect"), ("WILL", "will"), ("Crit Rate", "crit_rate"), ("Crit DMG", "crit_dmg"),
            ("Ult Gain", "ult_gain"), ("Healing Received", "treatment_received")]
    rows += [(name, field) for name, field in EXTRA_STATS
             if getattr(a.stats, field) > 1e-6 or getattr(b.stats, field) > 1e-6]
    out = []
    for name, field in rows:
        va, vb = getattr(a.stats, field), getattr(b.stats, field)
        if field in FLAT:
            ta, tb = f"{va:,}", f"{vb:,}"
        elif field == "arts_intensity":
            ta, tb = f"{va:.0f}", f"{vb:.0f}"
        else:
            ta, tb = a.stats.percent(field), b.stats.percent(field)
        tag = "MAIN" if a.stats.main_attribute == field else "SUB" if a.stats.sub_attribute == field else ""
        out.append((name, va, vb, ta, tb, tag))
    return out


def _player(canvas, d, build: Build, images, hide_uid, x, y, right):
    o = build.owner

    def put(text, f, yy, fill):
        w = d.textlength(text, font=f)
        d.text((x - w if right else x, yy), text, font=f, fill=fill)
        return w

    nf = font(40, "semibold")
    while d.textlength(o.name, font=nf) > SIDE - 40 and nf.size > 24:
        nf = font(nf.size - 2, "semibold")
    put(o.name, nf, y, TEXT)
    put(f"UID {o.uid}" + f"  ·  Authority {o.level}", font(19), y + 54, MUTED)
    w = put(f"Lv {build.level}   E{build.promotion}", number(38), y + 96, TEXT)
    mark = potential_mark(58, build.potential, SIGNAL, STAR_DIM)
    canvas.alpha_composite(mark, (int(x - w - 70) if right else int(x + w + 12), y + 88))
    if not build.talents:
        return
    done, total = build.talent_progress
    cw = put(f"{done}/{total}", number(22), y + 152, MUTED) + 14
    draw_row(canvas, build, images, x - cw if right else x + cw, y + 144, 42, tile=SLATE, text=TEXT, right=right)


def _stat(canvas, d, y, name, va, vb, ta, tb, tag=""):
    best = max(va, vb) or 1
    span, edge = 150, 130
    for value, text, side in ((va, ta, -1), (vb, tb, 1)):
        win = value > (vb if side < 0 else va)
        x = MID + side * edge
        far = x + side * span
        d.rounded_rectangle((min(x, far), y + 32, max(x, far), y + 37), 3, fill=TRACK)
        length = int(span * value / best)
        if length > 0:
            d.rounded_rectangle((min(x, x + side * length), y + 32, max(x, x + side * length), y + 37), 3,
                                fill=SIGNAL if win else LOSE)
        f = number(26)
        tw = d.textlength(text, font=f)
        d.text((x - tw if side < 0 else x, y - 1), text, font=f, fill=TEXT if win or va == vb else MUTED)
    lf = font(17, "semibold")
    color = SLATE if tag else MUTED
    mark = icon(name, 18, SIGNAL if tag == "MAIN" else color)
    gap = mark.width + 6 if mark is not None else 0
    pill = d.textlength(tag, font=font(12, "bold")) + 12 if tag else 0
    label = shorten(d, name, lf, 2 * edge - 30 - gap - pill)
    gx = MID - (d.textlength(label, font=lf) + gap + (pill + 6 if tag else 0)) / 2
    if mark is not None:
        canvas.alpha_composite(mark, (int(gx), y + 6))
    d.text((gx + gap, y + 4), label, font=lf, fill=color)
    if tag:
        px = gx + gap + d.textlength(label, font=lf) + 6
        d.rounded_rectangle((px, y + 6, px + pill, y + 24), 9, fill=SIGNAL if tag == "MAIN" else SLATE)
        d.text((px + 6, y + 7), tag, font=font(12, "bold"), fill=SLATE if tag == "MAIN" else BG)


def _skills(canvas, d, a: Build, b: Build, images, x0, x1, y):
    by_name = {s.name: s for s in b.skills}
    skills = a.skills[:4]
    cw = (x1 - x0) // max(len(skills), 1)
    for i, skill in enumerate(skills):
        other = by_name.get(skill.name) or (b.skills[i] if i < len(b.skills) else None)
        lb = other.level if other else 0
        cx = x0 + i * cw + cw // 2
        d.rounded_rectangle((cx - 26, y, cx + 26, y + 52), 11, fill=SLATE)
        g = images.get(skill.icon)
        if g is not None:
            g = fit(g, 38, 38)
            canvas.alpha_composite(g, (cx - g.width // 2, y + 26 - g.height // 2))
        kind = shorten(d, skill.kind, font(13), cw - 8)
        d.text((cx - d.textlength(kind, font=font(13)) / 2, y + 58), kind, font=font(13), fill=MUTED)
        f = number(26)
        for level, other_level, way in ((skill.level, lb, -1), (lb, skill.level, 1)):
            text = str(level)
            tw = d.textlength(text, font=f)
            x = cx - 12 - tw if way < 0 else cx + 12
            win = level > other_level
            if win:
                d.rounded_rectangle((x - 7, y + 80, x + tw + 7, y + 112), 8, fill=SIGNAL)
            d.text((x, y + 81), text, font=f, fill=SLATE if win else (TEXT if level == other_level else MUTED))
        d.text((cx - d.textlength(":", font=f) / 2, y + 80), ":", font=f, fill=MUTED)
    return y + 120


def _head(d, x0, x1, y, title):
    f = font(17, "semibold")
    text = title.upper()
    tw = d.textlength(text, font=f)
    mid = (x0 + x1) / 2
    d.line([(x0, y + 11), (mid - tw / 2 - 16, y + 11)], fill=HAIR, width=2)
    d.line([(mid + tw / 2 + 16, y + 11), (x1, y + 11)], fill=HAIR, width=2)
    d.text((mid - tw / 2, y), text, font=f, fill=MUTED)
    return y + 40


def _dark_card(canvas, box):
    ImageDraw.Draw(canvas).rounded_rectangle(box, 22, fill=SLATE)


WEAPON = palette(text=(245, 245, 245), dim=(170, 172, 180), accent=SIGNAL, on_accent=SLATE, line=(52, 55, 62),
                 tile=(44, 47, 56), star_dim=(78, 81, 90), pip=(236, 236, 240), pip_dim=(62, 65, 76), card=_dark_card)


def _loadout(canvas, d, build, images, x, y):
    y = boxed(canvas, _dark_card, x, y, SIDE, 22,
              lambda c, cd, xx, yy, ww: weapon_block(c, cd, build, images, xx, yy, ww, WEAPON))
    return gear_block(canvas, d, build, images, x, y + 22, SIDE, P, cols=2)


def render(a: Build, b: Build, images, *, hide_uid=False) -> Image.Image:
    tint = ELEMENT.get(a.element, MUTED)
    left, right = 50, W - 50

    def paint(h):
        canvas = Image.new("RGBA", (W, h), BG + (255,))
        glow = Image.new("RGBA", (W, 560))
        ImageDraw.Draw(glow).ellipse((MID - 330, -200, MID + 330, 420), fill=tint + (70,))
        canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60)))
        art = face_crop(a, images, 640, 330)
        if art is not None:
            canvas.alpha_composite(fade(art, left=90, right=90, bottom=70), (MID - 320, 0))
        d = canvas_draw(canvas)

        _player(canvas, d, a, images, hide_uid, left, 50, False)
        _player(canvas, d, b, images, hide_uid, right, 50, True)

        nf = fit_name(d, a.name, 64, 600)
        ny = 318
        d.text((MID - d.textlength(a.name, font=nf) / 2, ny), a.name, font=nf, fill=TEXT)
        y = ny + max(nf.size + 14, ink_bottom(a.name, nf) + 10)
        kf = font(19, "semibold")
        kind = shorten(d, f"{a.profession}  ·  {a.weapon_type}  ·  {a.element}", kf, 440)
        el = element_badge(a, images, 32, CARD)
        badge = class_badge(a.profession, 32, SLATE)
        bw = el.width + 8 + (badge.width + 12 if badge is not None else 4)
        span = bw + a.rarity * 22 + 14 + d.textlength(kind, font=kf)
        sx = MID - span / 2
        canvas.alpha_composite(el, (int(sx), y - 4))
        if badge is not None:
            canvas.alpha_composite(badge, (int(sx + el.width + 8), y - 4))
        stars(d, sx + bw, y + 3, a.rarity, 18, RARITY.get(a.rarity, SIGNAL), gap=4)
        d.text((sx + bw + a.rarity * 22 + 14, y), kind, font=kf, fill=MUTED)
        top = y + 44

        x0, x1 = left + SIDE + 30, right - SIDE - 30
        y = top
        rows = _rows(a, b)
        if rows:
            y = _head(d, x0, x1, y, "Stats")
            ahead = sum(r[1] > r[2] for r in rows)
            behind = sum(r[2] > r[1] for r in rows)
            for count, side in ((ahead, -1), (behind, 1)):
                text = f"ahead in {count}"
                tw = d.textlength(text, font=font(16))
                d.text((MID - 130 - tw if side < 0 else MID + 130, y - 6), text, font=font(16), fill=MUTED)
            y += 26
            for row in rows:
                _stat(canvas, d, y, *row)
                y += 39
            y += 6
        if a.skills:
            y = _skills(canvas, d, a, b, images, x0, x1, _head(d, x0, x1, y, "Skills"))
        ends = [y, _loadout(canvas, d, a, images, left, 258), _loadout(canvas, d, b, images, right - SIDE, 258)]
        y = max(ends) + 20
        d.text((right - d.textlength("akef", font=font(18, "semibold")), y), "akef", font=font(18, "semibold"), fill=MUTED)
        return canvas, y + 40

    return two_pass(paint)
