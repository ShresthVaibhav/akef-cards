from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from akef.enka.build import Build
from akef_cards.draw import canvas_draw, class_badge, fit, font, icon, number, potential_mark, shorten, stars
from akef_cards.templates import showcase as base
from akef_cards.templates.compare import _rows
from akef_cards.templates.parts import element_badge, fade, fit_name, palette, shape, splash, two_pass
from akef_cards.templates.talents import draw_row
from akef_cards.templates.showcase import ELEMENT, MUTED, RARITY, SIGNAL



def _dark_card(canvas, box):
    shape(canvas, "rect", box, fill=(30, 32, 40, 235), outline=(56, 59, 70), radius=14)


DARK = palette(text=(240, 241, 245), dim=(150, 153, 164), accent=SIGNAL, line=(50, 53, 62), tile=(44, 47, 56),
               star_dim=(80, 83, 94), pip_dim=(62, 65, 76), card=_dark_card)


def _pairs(a: Build, b: Build):
    by_name = {s.name: s for s in b.skills}
    out = []
    for i, skill in enumerate(a.skills[:4]):
        other = by_name.get(skill.name) or (b.skills[i] if i < len(b.skills) else None)
        out.append((skill, skill.level, other.level if other else 0))
    return out


def _owner_line(build, hide_uid):
    o = build.owner
    return f"UID {o.uid}" + f"  ·  Authority {o.level}"


def _weapon_mini(canvas, d, build, images, x, y, w, p):
    wpn = build.weapon
    if wpn is None:
        d.text((x, y), "No weapon", font=font(20), fill=p["dim"])
        return y + 36
    canvas.alpha_composite(base._item_tile(images.get(wpn.icon), 72, RARITY.get(wpn.rarity, SIGNAL)), (x, y - 2))
    d.text((x + 84, y), shorten(d, wpn.name, font(23, "semibold"), w - 90), font=font(23, "semibold"), fill=p["text"])
    stars(d, x + 86, y + 32, wpn.rarity, 14, RARITY.get(wpn.rarity, SIGNAL), gap=3)
    meta = f"Lv {wpn.level} · Break {wpn.breakthrough} · Refine"
    d.text((x + 86, y + 52), meta, font=font(16), fill=p["dim"])
    canvas.alpha_composite(potential_mark(26, wpn.refine, p["star"], p["star_dim"]),
                           (int(x + 92 + d.textlength(meta, font=font(16))), y + 47))
    y += 84
    boosts = {t.name: t.points for t in (wpn.essence.terms if wpn.essence else [])}
    cw = w // 3
    own, extra = base._pip(w=13, h=16, fill=p["pip"]), base._pip(w=13, h=16)
    for i, skill in enumerate(wpn.skills[:3]):
        sx = x + i * cw
        value = f"{skill.value} {skill.stat}".strip() if skill.value else skill.name
        d.text((sx, y), shorten(d, value, font(16, "semibold"), cw - 10), font=font(16, "semibold"), fill=p["text"])
        boosted = min(skill.level, boosts.get(skill.name, 0))
        for k in range(skill.level):
            canvas.alpha_composite(own if k < skill.level - boosted else extra, (sx + k * 13, y + 24))
    y += 76
    gem = wpn.essence
    if gem:
        p["card"](canvas, (x, y - 6, x + w, y + 108))
        canvas.alpha_composite(base._item_tile(base._essence_image(images.get(gem.icon), images.get(gem.badge)), 54,
                                               base.ESSENCE), (x + 12, y + 1))
        d.text((x + 76, y + 2), "ESSENCE", font=font(12, "bold"), fill=p["dim"])
        d.text((x + 76, y + 18), shorten(d, gem.name, font(20, "semibold"), w - 92), font=font(20, "semibold"),
               fill=p["essence"])
        cw = (w - 24) // 3
        for i, term in enumerate(gem.terms[:3]):
            tx, ty = x + 12 + i * cw, y + 62
            d.text((tx, ty), shorten(d, term.name, font(14), cw - 14), font=font(14), fill=p["dim"])
            base._pips(canvas, tx + 12 * term.points, ty + 24, term.points, step=12)
            d.text((tx + 12 * term.points + 10, ty + 20), f"+{term.points}", font=number(17), fill=p["text"])
        y += 118
    return y


def _gear_icons(canvas, d, build, images, x, y, w, p, lines=False):
    set_name, count = build.gear_set
    if set_name:
        label = shorten(d, set_name, font(17, "semibold"), w - 80)
        d.text((x, y), label, font=font(17, "semibold"), fill=p["text"])
        sx = x + d.textlength(label, font=font(17, "semibold")) + 10
        for k in range(count):
            canvas.alpha_composite(base._pip(w=10, h=13, s=3), (int(sx + k * 12), y + 4))
        y += 30
    tw = (w - 3 * 8) // 4
    th = 192 if lines else 62
    lit, dim = base._pip(w=12, h=15), base._pip(w=12, h=15, fill=p["pip_dim"])
    for i, piece in enumerate(build.gear[:4]):
        gx = x + i * (tw + 8)
        p["card"](canvas, (gx, y, gx + tw, y + th))
        canvas.alpha_composite(base._item_tile(images.get(piece.icon), 42, RARITY.get(piece.rarity, SIGNAL)),
                               (gx + 9, y + 10))
        d.text((gx + 58, y + 8), shorten(d, piece.slot.upper(), font(11, "bold"), tw - 64), font=font(11, "bold"), fill=p["dim"])
        d.text((gx + 58, y + 24), f"DEF {piece.defense}", font=number(20), fill=p["text"])
        if lines:
            ly = y + 66
            for line in piece.lines[:3]:
                mark = icon(line.name, 15, p["dim"])
                off = 0
                if mark is not None:
                    canvas.alpha_composite(mark, (gx + 10, ly + 3))
                    off = mark.width + 5
                room = tw - off - 20
                f = font(16) if d.textlength(line.name, font=font(16)) <= room else font(14)
                d.text((gx + 10 + off, ly + (0 if f.size == 16 else 2)), shorten(d, line.name, f, room), font=f, fill=p["dim"])
                for m in range(line.max_level):
                    canvas.alpha_composite(lit if m < line.level else dim, (gx + 10 + off + m * 12, ly + 21))
                vw = d.textlength(line.text, font=number(18))
                d.text((gx + tw - 10 - vw, ly + 16), line.text, font=number(18), fill=p["text"])
                ly += 40
    return y + th


def _label(canvas, d, cx, y, name, room, fill, size=16):
    f = font(size, "semibold")
    mark = icon(name, size, fill)
    gap = mark.width + 6 if mark is not None else 0
    text = shorten(d, name, f, room - gap)
    gx = cx - (d.textlength(text, font=f) + gap) / 2
    if mark is not None:
        canvas.alpha_composite(mark, (int(gx), int(y + 3)))
    d.text((gx + gap, y + 1), text, font=f, fill=fill)


def _skill_icon(canvas, d, images, skill, x, y, size, tile):
    d.rounded_rectangle((x, y, x + size, y + size), size // 5, fill=tile)
    g = images.get(skill.icon)
    if g is not None:
        g = fit(g, int(size * 0.72), int(size * 0.72))
        canvas.alpha_composite(g, (x + size // 2 - g.width // 2, y + size // 2 - g.height // 2))


def _footer(d, w, y, p):
    d.text((w - 40 - d.textlength("akef", font=font(16, "semibold")), y), "akef", font=font(16, "semibold"), fill=p["dim"])



def render_split(a: Build, b: Build, images, *, hide_uid=False) -> Image.Image:
    w, side = 2000, 620
    tint = ELEMENT.get(a.element, MUTED)
    p = DARK

    def panel(canvas, d, build, rival, x, y):
        o = build.owner
        d.text((x, y), shorten(d, o.name, font(36, "semibold"), side), font=font(36, "semibold"), fill=p["text"])
        d.text((x, y + 48), _owner_line(build, hide_uid), font=font(16), fill=p["dim"])
        lv = f"Lv {build.level}   E{build.promotion}"
        d.text((x, y + 78), lv, font=number(32), fill=p["text"])
        canvas.alpha_composite(potential_mark(46, build.potential, SIGNAL, p["star_dim"]),
                               (int(x + d.textlength(lv, font=number(32)) + 10), y + 72))
        done, total = build.talent_progress
        talents = f"Talents {done}/{total}"
        d.text((x + side - d.textlength(talents, font=font(16, "semibold")), y + 100), talents, font=font(16, "semibold"),
               fill=p["dim"])
        draw_row(canvas, build, images, x + side, y + 42, 44, tile=(36, 38, 48), text=p["text"], right=True)
        y += 140
        mine = {r[0]: r for r in _rows(build, rival)}
        cw = (side - 20) // 2
        for i, (name, va, vb, ta, _, tag) in enumerate(mine.values()):
            cx, cy = x + (i % 2) * (cw + 20), y + (i // 2) * 52
            win = va > vb
            shape(canvas, "rect", (cx, cy, cx + cw, cy + 44), fill=(38, 40, 50, 220) if not win else SIGNAL + (40,),
                  outline=SIGNAL if win else None, width=2, radius=10)
            mark = icon(name, 16, SIGNAL if tag == "MAIN" else p["text"] if tag else p["dim"])
            off = 0
            if mark is not None:
                canvas.alpha_composite(mark, (cx + 12, cy + 14))
                off = mark.width + 6
            tw = d.textlength(ta, font=number(22))
            label = shorten(d, name, font(15), cw - tw - off - 36)
            d.text((cx + 12 + off, cy + 12), label, font=font(15), fill=p["text"] if tag else p["dim"])
            if tag:
                px = cx + 12 + off + d.textlength(label, font=font(15)) + 6
                pw = d.textlength(tag, font=font(11, "bold")) + 10
                shape(canvas, "rect", (px, cy + 13, px + pw, cy + 30), fill=(SIGNAL if tag == "MAIN" else (70, 73, 84)) + (255,),
                      radius=8)
                d.text((px + 5, cy + 14), tag, font=font(11, "bold"), fill=(16, 16, 20) if tag == "MAIN" else (240, 240, 244))
            d.text((cx + cw - 12 - tw, cy + 8), ta, font=number(22), fill=SIGNAL if win else p["text"])
        y += 52 * ((len(mine) + 1) // 2) + 6
        for i, (skill, la, lb) in enumerate(_pairs(build, rival)):
            sx = x + i * (side // 4)
            _skill_icon(canvas, d, images, skill, sx, y, 44, p["tile"])
            win = la > lb
            d.text((sx + 54, y + 6), str(la), font=number(26), fill=SIGNAL if win else p["text"])
        y += 64
        y = _weapon_mini(canvas, d, build, images, x, y, side, p) + 10
        return _gear_icons(canvas, d, build, images, x, y, side, p, lines=True)

    def paint(h):
        h = max(h, 900)
        canvas = Image.new("RGBA", (w, h), (16, 17, 21, 255))
        glow = Image.new("RGBA", (w, h))
        ImageDraw.Draw(glow).ellipse((w / 2 - 330, h * 0.1, w / 2 + 330, h * 0.9), fill=tint + (80,))
        canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
        art = splash(a, images, None, 660, h, 0.05)
        if art is not None:
            canvas.alpha_composite(fade(art, left=110, right=110, bottom=260), ((w - 660) // 2, 0))
        d = canvas_draw(canvas)
        nf = fit_name(d, a.name.upper(), 72, 640)
        floor = Image.new("RGBA", (660, 300))
        fd = ImageDraw.Draw(floor)
        for i in range(300):
            fd.line([(0, i), (660, i)], fill=(16, 17, 21, int(230 * (i / 300) ** 1.3)))
        canvas.alpha_composite(fade(floor, left=120, right=120), ((w - 660) // 2, h - 300))
        ny = h - nf.size - 70
        d.text((w / 2 - d.textlength(a.name.upper(), font=nf) / 2, ny), a.name.upper(), font=nf, fill=(255, 255, 255))
        el = element_badge(a, images, 34)
        badge = class_badge(a.profession, 34, (16, 17, 21))
        bw = el.width + 8 + (badge.width + 12 if badge is not None else 4)
        marks = bw + a.rarity * 30 - 4
        canvas.alpha_composite(el, (int(w / 2 - marks / 2), ny - 40))
        if badge is not None:
            canvas.alpha_composite(badge, (int(w / 2 - marks / 2 + el.width + 8), ny - 40))
        stars(d, w / 2 - marks / 2 + bw, ny - 34, a.rarity, 26, RARITY.get(a.rarity, SIGNAL), gap=4)
        ends = [panel(canvas, d, a, b, 40, 40), panel(canvas, d, b, a, w - 40 - side, 40)]
        bottom = max(max(ends) + 50, 900)
        _footer(d, w, bottom - 40, p)
        return canvas, bottom

    return two_pass(paint)


STYLES = {2: render_split}
