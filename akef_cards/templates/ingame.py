from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from akef.enka.build import Build
from akef_cards.draw import canvas_draw, class_badge, fit, font, number, shorten, stars
from akef_cards.templates.parts import (
    attributes, boxed, extra_stats, fade, fit_name, footer, glyph, gradient, ink_bottom, palette,
    potential_after, shape, skills_block, splash, two_pass, weapon_block,
)
from akef_cards.templates.talents import draw_tree
from akef_cards.templates.showcase import ELEMENT, RARITY, SIGNAL, _item_tile, _pip


def _cut(canvas, box, fill=(26, 28, 34, 235), outline=(72, 75, 86), cut=18, tab=SIGNAL):
    x0, y0, x1, y1 = box
    pts = [(x0, y0), (x1 - cut, y0), (x1, y0 + cut), (x1, y1), (x0 + cut, y1), (x0, y1 - cut)]
    shape(canvas, "poly", pts, fill=fill, outline=outline, width=2)
    if tab:
        ImageDraw.Draw(canvas).rectangle((x0, y0, x0 + 42, y0 + 4), fill=tab)


DIM = (140, 144, 154)


def _gear(canvas, d, build: Build, images, x, y, w):
    set_name, count = build.gear_set
    if set_name:
        _cut(canvas, (x, y, x + w, y + 48), cut=12, tab=None)
        d.text((x + 18, y + 11), shorten(d, set_name, font(21, "semibold"), w - 200), font=font(21, "semibold"),
               fill=(240, 240, 244))
        label = f"{count}/4 equipped"
        lw = d.textlength(label, font=font(15, "semibold"))
        d.text((x + w - 18 - lw, y + 15), label, font=font(15, "semibold"), fill=DIM)
        pip = _pip(w=11, h=14, s=4)
        for k in range(count):
            canvas.alpha_composite(pip, (int(x + w - 30 - lw - (count - k) * 12), y + 17))
        y += 62
    if not build.gear:
        d.text((x, y), "Nothing equipped", font=font(22), fill=DIM)
        return y + 40
    gap, ch = 14, 186
    cw = (w - gap) // 2
    lit, unlit = _pip(w=9, h=12, s=3), _pip(w=9, h=12, s=3, fill=(62, 65, 76))
    for i, piece in enumerate(build.gear[:4]):
        gx, gy = x + (i % 2) * (cw + gap), y + (i // 2) * (ch + gap)
        _cut(canvas, (gx, gy, gx + cw, gy + ch), cut=14)
        canvas.alpha_composite(_item_tile(images.get(piece.icon), 70, RARITY.get(piece.rarity, SIGNAL)), (gx + 14, gy + 14))
        d.text((gx + 98, gy + 20), piece.slot.upper(), font=font(14, "bold"), fill=DIM)
        d.text((gx + 98, gy + 38), f"DEF {piece.defense}", font=number(30), fill=(240, 240, 244))
        ly = gy + 100
        for line in piece.lines[:3]:
            pips = line.max_level * 10
            vx = gx + cw - 16 - pips - 10
            vw = d.textlength(line.text, font=number(18))
            off = glyph(canvas, line.name, 16, DIM, gx + 14, ly + 3)
            d.text((gx + 14 + off, ly + 1), shorten(d, line.name, font(15), vx - vw - gx - 30 - off), font=font(15), fill=DIM)
            d.text((vx - vw, ly - 1), line.text, font=number(18), fill=(240, 240, 244))
            for k in range(line.max_level):
                canvas.alpha_composite(lit if k < line.level else unlit, (gx + cw - 16 - pips + k * 10, ly + 5))
            ly += 28
    rows = (min(len(build.gear), 4) + 1) // 2
    return y + rows * (ch + gap) - gap


def render(build: Build, images, *, art=None, hide_uid=False) -> Image.Image:
    w = 2100
    tint = ELEMENT.get(build.element, (120, 120, 130))
    p = palette(text=(236, 237, 240), dim=(140, 144, 154), accent=SIGNAL, line=(50, 53, 62), tile=(44, 47, 56),
                 star_dim=(80, 83, 94), pip_dim=(62, 65, 76), card=_cut)

    def paint(h):
        h = max(h, 1200)
        canvas = gradient(w, h, (44, 46, 54), (15, 16, 20))
        streak = Image.new("RGBA", (w, h))
        ImageDraw.Draw(streak).polygon([(700, 0), (1100, 0), (700, h), (300, h)], fill=tint + (26,))
        canvas.alpha_composite(streak.filter(ImageFilter.GaussianBlur(60)))
        ghost = Image.new("RGBA", (h, 300))
        gf = number(260)
        gname = build.name.upper()
        gd_ = canvas_draw(ghost)
        while gd_.textlength(gname, font=gf) > h - 60 and gf.size > 100:
            gf = number(gf.size - 10)
        gd_.text((30, 0), gname, font=gf, fill=(255, 255, 255, 16))
        canvas.alpha_composite(ghost.rotate(90, expand=True), (560, 0))
        shot = splash(build, images, art, 800, h, 0.06)
        if shot is not None:
            canvas.alpha_composite(fade(shot, left=150, right=150), (540, 0))
        d = canvas_draw(canvas)

        x0, lw = 60, 460
        d.polygon([(x0, 56), (x0 + 150, 56), (x0 + 138, 84), (x0, 84)], fill=SIGNAL)
        d.text((x0 + 12, 58), "OPERATOR", font=font(20, "bold"), fill=(20, 20, 24))
        stars(d, x0 + 166, 60, build.rarity, 22, RARITY.get(build.rarity, SIGNAL), gap=4)
        nf = fit_name(d, build.name, 100, lw - 80)
        d.text((x0 - 4, 96), build.name, font=nf, fill=(255, 255, 255))
        potential_after(canvas, d, build, build.name, nf, x0, 96, SIGNAL, (84, 86, 96), k=0.8)
        y = 96 + max(nf.size + 14, ink_bottom(build.name, nf) + 12)
        badge = class_badge(build.profession, 36, (44, 47, 56), SIGNAL)
        off = 0
        if badge is not None:
            canvas.alpha_composite(badge, (x0, y - 6))
            off = badge.width + 12
        kind = shorten(d, f"{build.profession}  ·  {build.weapon_type}", font(21, "semibold"), lw - off)
        d.text((x0 + off, y), kind, font=font(21, "semibold"), fill=(200, 202, 210))
        y += 46
        chip = d.textlength(build.element, font=font(21, "bold")) + 64
        shape(canvas, "rect", (x0, y, x0 + chip, y + 44), fill=tint + (255,), radius=6)
        el = images.get(build.element_icon)
        if el is not None:
            g = fit(el, 28, 28)
            canvas.alpha_composite(g, (x0 + 10, y + 8))
        d.text((x0 + 46, y + 9), build.element, font=font(21, "bold"), fill=(255, 255, 255))
        lx = x0 + chip + 22
        d.text((lx, y - 10), "LV", font=font(18, "bold"), fill=(150, 152, 160))
        d.text((lx + 30, y - 22), str(build.level), font=number(60), fill=(255, 255, 255))
        d.text((lx + 42 + d.textlength(str(build.level), font=number(60)), y + 4), f"E{build.promotion}",
               font=number(32), fill=SIGNAL)
        y += 80
        if build.stats is not None:
            for name, value in (("HP", build.stats.hp), ("ATK", build.stats.atk), ("DEF", build.stats.defense)):
                _cut(canvas, (x0, y, x0 + lw, y + 74), cut=14)
                off = glyph(canvas, name, 22, (150, 152, 160), x0 + 20, y + 26)
                d.text((x0 + 20 + off, y + 24), name, font=font(20, "bold"), fill=(150, 152, 160))
                text = f"{value:,}"
                tx = x0 + lw - 22 - d.textlength(text, font=number(48))
                d.text((tx, y + 10), text, font=number(48), fill=(255, 255, 255))
                y += 86
            aw = lw // 2
            for i, (name, value, main, sub) in enumerate(attributes(build)):
                cx, cy = x0 + (i % 2) * aw, y + 6 + (i // 2) * 70
                c = SIGNAL if main else (230, 230, 236) if sub else (150, 152, 160)
                off = glyph(canvas, name, 40, c, cx, cy + 10)
                tag = "  MAIN" if main else "  SUB" if sub else ""
                d.text((cx + off, cy), name + tag, font=font(16, "bold"), fill=c)
                d.text((cx + off, cy + 22), f"{value:,}", font=number(34), fill=(255, 255, 255))
            y += 156
            for name, value in extra_stats(build):
                vw = d.textlength(value, font=number(21))
                off = glyph(canvas, name, 18, (150, 152, 160), x0, y + 3)
                label = shorten(d, name, font(19), lw - vw - 16 - off)
                d.text((x0 + off, y), label, font=font(19), fill=(150, 152, 160))
                d.text((x0 + lw - vw, y - 1), value, font=number(21), fill=(240, 240, 244))
                y += 33
        y += 20
        if build.talents:
            done, total = build.talent_progress
            rows = len(build.talents)
            box_h = 56 + rows * 52 - 18 + 22
            _cut(canvas, (x0, y, x0 + lw, y + box_h), cut=14)
            d.text((x0 + 18, y + 14), "TALENTS", font=font(16, "bold"), fill=(150, 152, 160))
            count = f"{done}/{total}"
            d.text((x0 + lw - 18 - d.textlength(count, font=number(20)), y + 11), count, font=number(20), fill=SIGNAL)
            draw_tree(canvas, build, images, x0 + 18, y + 50, lw - 36)
            y += box_h
        left_end = y + 20

        rx, rw = 1330, 710
        y = 60
        def head(c, dd, x, yy, ww, title):
            dd.rectangle((x, yy + 6, x + 6, yy + 24), fill=SIGNAL)
            dd.text((x + 16, yy + 2), title.upper(), font=font(20, "bold"), fill=(236, 237, 240))
            end = x + 30 + dd.textlength(title.upper(), font=font(20, "bold"))
            dd.line([(end, yy + 15), (x + ww, yy + 15)], fill=(60, 63, 72), width=2)
            return yy + 44
        y = boxed(canvas, _cut, rx, head(canvas, d, rx, y, rw, "Skills"), rw, 20,
                   lambda c, cd, xx, yy, ww: skills_block(c, cd, build, images, xx, yy, ww, p, cols=2)) + 24
        y = boxed(canvas, _cut, rx, head(canvas, d, rx, y, rw, "Weapon"), rw, 22,
                   lambda c, cd, xx, yy, ww: weapon_block(c, cd, build, images, xx, yy, ww, p)) + 24
        y = _gear(canvas, d, build, images, rx, head(canvas, d, rx, y, rw, "Gear"), rw) + 30
        bottom = max(y + 50, left_end + 30, 1200)
        footer(d, build, hide_uid, rx, rx + rw, bottom - 46, (120, 124, 134))
        corners = ((22, 22, 1, 1), (w - 22, 22, -1, 1), (22, bottom - 22, 1, -1), (w - 22, bottom - 22, -1, -1))
        for cx, cy, sx, sy in corners:
            d.line([(cx, cy), (cx + 40 * sx, cy)], fill=SIGNAL, width=3)
            d.line([(cx, cy), (cx, cy + 40 * sy)], fill=SIGNAL, width=3)
        return canvas, bottom

    return two_pass(paint)
