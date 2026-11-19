from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from akef.enka.build import Build
from akef_cards.framing import splash_focus
from akef_cards.i18n import t as tr
from akef_cards.templates.talents import draw_row, row_width
from akef_cards.draw import _runs, body_x, canvas_draw, class_badge, stand, icon, potential_mark, stat_label, cover, fit, font, number, shorten, stars

W, H = 2000, 1490
BG = (242, 241, 236)
SLATE = (26, 28, 33)
TEXT = (30, 32, 37)
MUTED = (128, 130, 137)
HAIR = (214, 212, 205)
SIGNAL = (255, 200, 0)
ESSENCE = (232, 176, 20)
CARD = (252, 251, 248)
RARITY = {6: (240, 128, 40), 5: (232, 176, 20), 4: (150, 104, 228), 3: (72, 150, 226)}
ELEMENT = {
    "Physical": (120, 126, 138),
    "Heat": (232, 98, 66),
    "Cryo": (66, 168, 220),
    "Electric": (154, 104, 236),
    "Nature": (98, 176, 82),
}
ELEMENT_DMG = {"Physical": "physical_dmg", "Heat": "heat_dmg", "Cryo": "cryo_dmg", "Electric": "electric_dmg",
               "Nature": "nature_dmg"}
EXTRA_STATS = (
    ("Physical DMG", "physical_dmg"), ("Heat DMG", "heat_dmg"), ("Electric DMG", "electric_dmg"),
    ("Cryo DMG", "cryo_dmg"), ("Nature DMG", "nature_dmg"), ("Treatment", "treatment_bonus"),
    ("Arts Intensity", "arts_intensity"), ("Stagger DMG", "stagger_dmg"), ("Basic ATK DMG", "basic_attack_dmg"),
    ("Battle Skill DMG", "battle_skill_dmg"), ("Combo Skill DMG", "combo_skill_dmg"), ("Ultimate DMG", "ultimate_dmg"),
)


def _soft(color, amount):
    return tuple(int(BG[i] + (color[i] - BG[i]) * amount) for i in range(3))


def _item_tile(img, size, rarity):
    s = 4
    big = size * s
    tile = Image.new("RGBA", (big, big))
    td = ImageDraw.Draw(tile)
    top, low = (44, 47, 55), tuple(int(a + (b - a) * 0.55) for a, b in zip((44, 47, 55), rarity))
    for row in range(big):
        k = (row / big) ** 1.6
        td.line([(0, row), (big, row)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, low)) + (255,))
    mask = Image.new("L", (big, big))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), 16 * s, fill=255)
    tile.putalpha(mask)
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, big - 1, big - 1), 16 * s, outline=(255, 255, 255, 40), width=2 * s)
    tile = tile.resize((size, size), Image.LANCZOS)
    if img is not None:
        img = img.convert("RGBA")
        box = img.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
        glyph = fit(img.crop(box) if box else img, int(size * 0.68), int(size * 0.68))
        alpha = glyph.getchannel("A")
        cols = list(alpha.resize((glyph.width, 1), Image.BOX).tobytes())
        rows = list(alpha.resize((1, glyph.height), Image.BOX).tobytes())
        mx = sum(i * v for i, v in enumerate(cols)) / (sum(cols) or 1)
        my = sum(i * v for i, v in enumerate(rows)) / (sum(rows) or 1)
        cx = (glyph.width / 2 + mx) / 2
        cy = (glyph.height / 2 + my) / 2
        tile.alpha_composite(glyph, (int(size / 2 - cx), int(size / 2 - cy)))
    return tile


def _tile(canvas, img, x, y, size, radius=14, ring=None, dim=False, fill=SLATE):
    d = canvas_draw(canvas)
    d.rounded_rectangle((x, y, x + size, y + size), radius, fill=fill)
    if ring:
        d.rounded_rectangle((x, y, x + size, y + size), radius, outline=ring, width=3)
    if img is not None:
        icon = fit(img, int(size * 0.78), int(size * 0.78))
        if dim:
            icon.putalpha(icon.getchannel("A").point(lambda a: a // 3))
        canvas.alpha_composite(icon, (int(x + (size - icon.width) / 2), int(y + (size - icon.height) / 2)))


def _label(d, x, y, text, color=MUTED, size=18):
    d.text((x, y), text.upper(), font=font(size, "semibold"), fill=color)


def _fade_edges(img, edge=110):
    fade = Image.new("L", img.size, 255)
    fd = ImageDraw.Draw(fade)
    for i in range(edge):
        v = int(255 * i / edge)
        fd.line([(i, 0), (i, img.height)], fill=v)
        fd.line([(img.width - 1 - i, 0), (img.width - 1 - i, img.height)], fill=v)
    top = Image.new("L", img.size, 255)
    td = ImageDraw.Draw(top)
    for i in range(edge):
        td.line([(0, i), (img.width, i)], fill=int(255 * i / edge))
    img.putalpha(ImageChops.multiply(ImageChops.multiply(fade, top), img.getchannel("A")))
    return img


ART_W = 960


def _frame_splash(source, focus):
    cx, top, bottom = focus
    size = source.width
    height = (bottom - top) * size
    width = height * ART_W / H
    left = cx * size - width / 2
    window = source.convert("RGBA").crop((int(left), int(top * size), int(left + width), int(bottom * size)))
    img = window.resize((ART_W, H), Image.LANCZOS)

    side = Image.new("L", img.size, 255)
    sd = ImageDraw.Draw(side)
    for i in range(170):
        sd.line([(ART_W - 170 + i, 0), (ART_W - 170 + i, H)], fill=int(255 * (1 - i / 170)))
    ends = Image.new("L", img.size, 255)
    ed = ImageDraw.Draw(ends)
    for i in range(120):
        v = int(255 * i / 120)
        ed.line([(0, H - 1 - i), (ART_W, H - 1 - i)], fill=v)
        ed.line([(0, i), (ART_W, i)], fill=v)
    img.putalpha(ImageChops.multiply(img.getchannel("A"), ImageChops.multiply(side, ends)))
    return img


def _hero(canvas, build: Build, images, art):
    if art is not None:
        img = cover(art, 940, H)
        mask = Image.new("L", img.size, 255)
        md = ImageDraw.Draw(mask)
        for i in range(160):
            md.line([(img.width - 160 + i, 0), (img.width - 160 + i, H)], fill=int(255 * (1 - i / 160)))
        img.putalpha(ImageChops.multiply(img.getchannel("A"), mask))
        canvas.alpha_composite(img, (0, 0))
        return

    tint = ELEMENT.get(build.element, MUTED)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    cx, cy, r = 470, 600, 470
    ld.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*_soft(tint, 0.42), 255))
    for i, ring in enumerate((r + 40, r + 90, r + 150)):
        ld.ellipse((cx - ring, cy - ring, cx + ring, cy + ring), outline=(*tint, 46 - i * 12), width=2)
    ld.ellipse((cx - r + 70, cy - r + 70, cx + r - 70, cy + r - 70), outline=(255, 255, 255, 90), width=2)
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.8)))

    ghost = Image.new("RGBA", (H, 360), (0, 0, 0, 0))
    gd = canvas_draw(ghost)
    f = number(320)
    name = build.name.upper()
    while gd.textlength(name, font=f) > H - 80 and f.size > 120:
        f = number(f.size - 10)
    gd.text((40, 0), name, font=f, fill=(*tint, 24))
    turned = ghost.rotate(90, expand=True)
    canvas.alpha_composite(turned, (6, (H - turned.height) // 2))

    source = images.get(build.art)
    if source is None:
        return
    focus = splash_focus(build)
    if focus is not None:
        canvas.alpha_composite(_frame_splash(source, focus), (0, 0))
        return
    figure = stand(source, H - 50, 1500)
    img = Image.new("RGBA", (980, H))
    img.paste(figure, (470 - body_x(figure), H - figure.height), figure)
    img = _fade_edges(img)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.paste((*SLATE, 70), (0, 0), img.getchannel("A"))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(22)), (26, 10))
    canvas.alpha_composite(img, (0, 0))


def _talent_dock(canvas, build: Build, images):
    stars_w = build.rarity * 26
    count_w = 90
    size = 46
    width = 40 + stars_w + 40 + row_width(build, size, 8) + count_w
    x, y = 40, H - 104
    dock = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(dock).rounded_rectangle((x, y, x + width, y + 72), 36, fill=(*SLATE, 232))
    canvas.alpha_composite(dock)
    d = canvas_draw(canvas)
    stars(d, x + 26, y + 25, build.rarity, 22, RARITY.get(build.rarity, SIGNAL))
    tx = x + 26 + stars_w + 26
    d.line([(tx - 14, y + 18), (tx - 14, y + 54)], fill=(70, 73, 80), width=2)
    tw = draw_row(canvas, build, images, tx, y + 36 - size // 2, size, tile=(40, 43, 50), text=BG, gap=8)
    done, total = build.talent_progress
    d.text((tx + tw + 14, y + 18), f"{done}/{total}", font=number(30), fill=BG)


def _headline(canvas, d, build: Build, images, x0, width):
    tint = ELEMENT.get(build.element, MUTED)
    badge = class_badge(build.profession, 40, SLATE)
    lx = x0
    if badge is not None:
        canvas.alpha_composite(badge, (x0, 60))
        lx += badge.width + 12
    _label(d, lx, 70, f"{build.profession}  ·  {build.weapon_type}")
    nf = number(136)
    while d.textlength(build.name, font=nf) + nf.size > width:
        nf = number(nf.size - 4)
    d.text((x0 - 6, 84), build.name, font=nf, fill=TEXT)
    size = int(nf.size * 0.82)
    name_w = d.textlength(build.name, font=nf)
    if name_w + size + 20 <= width:
        mark = potential_mark(size, build.potential, SIGNAL, (196, 194, 186))
        canvas.alpha_composite(mark, (int(x0 + name_w + 14), int(84 + nf.size * 0.62 - size / 2)))
    # cjk glyphs sit lower than latin ones at the same size, so measure what was drawn
    bottom = max(f.getbbox(chunk)[3] for chunk, f in _runs(tr(build.name), nf))
    y = 84 + max(nf.size + 8, bottom) + 14
    glyph = images.get(build.element_icon)
    if glyph is None:
        d.ellipse((x0, y + 9, x0 + 16, y + 25), fill=tint)
        tx = x0 + 28
    else:
        d.ellipse((x0, y - 2, x0 + 38, y + 36), fill=tint)
        glyph = fit(glyph, 26, 26)
        canvas.alpha_composite(glyph, (x0 + 19 - glyph.width // 2, y + 17 - glyph.height // 2))
        tx = x0 + 50
    d.text((tx, y), build.element, font=font(28, "semibold"), fill=TEXT)
    meta = f"Lv {build.level}    E{build.promotion}"
    mx = tx + 32 + d.textlength(build.element, font=font(28, "semibold"))
    d.text((mx, y), meta, font=font(28), fill=MUTED)
    d.rounded_rectangle((x0, y + 52, x0 + 72, y + 58), 3, fill=SIGNAL)
    return y + 96


def _stats(d, build: Build, x0, width, y):
    stats = build.stats
    for i, (name, value) in enumerate((("HP", stats.hp), ("ATK", stats.atk), ("DEF", stats.defense))):
        cx = x0 + i * 310
        stat_label(d, cx, y, name, font(18, "semibold"), MUTED, size=24)
        d.text((cx - 3, y + 16), f"{value:,}", font=number(84), fill=TEXT)
    y += 128
    attrs = (("STR", "strength"), ("AGI", "agility"), ("INT", "intellect"), ("WILL", "will"))
    peak = max(getattr(stats, f) for _, f in attrs) or 1
    col = width // 4
    for i, (name, field) in enumerate(attrs):
        cx = x0 + i * col
        value = getattr(stats, field)
        main, sub = stats.main_attribute == field, stats.sub_attribute == field
        mark = icon(name, 46, SIGNAL if main else (TEXT if sub else MUTED))
        tx = cx
        if mark is not None:
            d.canvas.alpha_composite(mark, (cx, y + 14))
            tx = cx + mark.width + 12
        d.text((tx, y), name, font=font(18, "semibold"), fill=TEXT if main or sub else MUTED)
        if main or sub:
            tag = "MAIN" if main else "SUB"
            gx = tx + d.textlength(name, font=font(18, "semibold")) + 10
            tw = d.textlength(tag, font=font(14, "bold"))
            d.rounded_rectangle((gx, y + 1, gx + tw + 14, y + 21), 10, fill=SIGNAL if main else SLATE)
            d.text((gx + 7, y + 2), tag, font=font(14, "bold"), fill=SLATE if main else BG)
        d.text((tx, y + 20), f"{value:,}", font=number(46), fill=TEXT)
        d.rounded_rectangle((cx, y + 76, cx + col - 30, y + 80), 2, fill=HAIR)
        filled = int((col - 30) * value / peak)
        d.rounded_rectangle((cx, y + 76, cx + max(filled, 6), y + 80), 2, fill=SIGNAL if main else SLATE)
    y += 108

    extras = [("Crit Rate", "crit_rate"), ("Crit DMG", "crit_dmg"), ("Ult Gain", "ult_gain"),
              ("Healing Received", "treatment_received")]
    own = ELEMENT_DMG.get(build.element)
    for name, field in EXTRA_STATS:
        if getattr(stats, field) > 1e-6:
            extras.insert(4 if field == own else len(extras), (name, field))
    extras = extras[:6]
    col = (width - 60) // 2
    for i, (name, field) in enumerate(extras):
        cx = x0 + (i % 2) * (col + 60)
        cy = y + (i // 2) * 44
        value = f"{stats.arts_intensity:.0f}" if field == "arts_intensity" else stats.percent(field)
        vw = d.textlength(value, font=number(27))
        glyph = icon(name, 24, MUTED)
        nx = cx
        if glyph is not None:
            d.canvas.alpha_composite(glyph, (cx, cy + 3))
            nx += glyph.width + 10
        d.text((nx, cy), shorten(d, name, font(24), col - vw - 16 - (nx - cx)), font=font(24), fill=MUTED)
        d.text((cx + col - vw, cy - 2), value, font=number(27), fill=TEXT)
        d.line([(cx, cy + 34), (cx + col, cy + 34)], fill=HAIR, width=1)
    return y + ((len(extras) + 1) // 2) * 44 + 26


def _wrap(d, text, f, room, limit):
    lines = [""]
    for word in text.replace("-", "- ").split(" "):
        trial = f"{lines[-1]} {word}".strip().replace("- ", "-")
        if d.textlength(trial, font=f) <= room:
            lines[-1] = trial
            continue
        if lines[-1]:
            lines.append("")
        for ch in word:
            if lines[-1] and d.textlength(lines[-1] + ch, font=f) > room:
                lines.append("")
            lines[-1] += ch
    if len(lines) > limit:
        lines = lines[:limit - 1] + [" ".join(lines[limit - 1:])]
    lines[-1] = shorten(d, lines[-1], f, room)
    return lines


def _skills(canvas, d, build: Build, images, x0, width, y):
    _label(d, x0, y, "Skills")
    col = width // 4
    for i, skill in enumerate(build.skills[:4]):
        cx = x0 + i * col
        _tile(canvas, images.get(skill.icon), cx, y + 32, 64, radius=14)
        lvl = str(skill.level)
        bw = d.textlength(lvl, font=number(20)) + 14
        d.rounded_rectangle((cx + 64 - bw + 6, y + 80, cx + 70, y + 102), 11, fill=SIGNAL)
        d.text((cx + 64 - bw + 13, y + 79), lvl, font=number(20), fill=SLATE)
        room = col - 96
        name = tr(skill.name)
        for size in (21, 19, 17, 15):
            f = font(size, "semibold")
            if all(d.textlength(w, font=f) <= room for w in name.replace("-", "- ").split(" ")):
                break
        else:
            f = font(21, "semibold")
        lines = _wrap(d, name, f, room, 2)
        top = y + 32 if len(lines) == 2 else y + 44
        for j, line in enumerate(lines):
            d.text((cx + 80, top + j * 24), line, font=f, fill=TEXT)
        d.text((cx + 80, top + len(lines) * 24 + 2), shorten(d, skill.kind, font(17), room), font=font(17), fill=MUTED)
    return y + 128


def _essence_image(capsule, badge):
    if capsule is None or badge is None:
        return capsule or badge
    capsule = capsule.convert("RGBA")
    px = capsule.load()
    xs = ys = n = 0
    for y in range(0, capsule.height, 2):
        for x in range(0, capsule.width, 2):
            r, g, b, a = px[x, y]
            if a > 200 and r + g + b < 200:
                xs, ys, n = xs + x, ys + y, n + 1
    cx, cy = (xs / n, ys / n) if n else (capsule.width * 0.55, capsule.height * 0.44)
    size = int(capsule.width * 0.68)
    badge = badge.convert("RGBA").resize((size, size), Image.LANCZOS)
    out = capsule.copy()
    out.alpha_composite(badge, (int(cx - size / 2), int(cy - size / 2)))
    return out


def _pip(w=14, h=17, s=4, fill=SIGNAL):
    big = Image.new("RGBA", (w * s, h * s))
    d = ImageDraw.Draw(big)
    r = 3.2 * s
    a, b = (r + s, h * s - r - s), (w * s - r - s, r + s)
    d.line([a, b], fill=fill, width=int(r * 2))
    for cx, cy in (a, b):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)
    return big.resize((w, h), Image.LANCZOS)


def _pips(canvas, end, y, count, step=15):
    pip = _pip()
    start = end - count * step
    for i in range(count):
        canvas.alpha_composite(pip, (int(start + i * step), int(y)))
    return start


def _weapon(canvas, d, build: Build, images, x0, right, y):
    w = build.weapon
    box_h = 222 if w and (w.skills or w.essence) else 128
    soft = (170, 172, 180)
    d.rounded_rectangle((x0, y, right, y + box_h), 22, fill=SLATE)
    if w is None:
        d.text((x0 + 30, y + 44), "No weapon", font=font(28, "semibold"), fill=BG)
        return y + box_h + 26
    gx = right - 320 if w.essence else right
    canvas.alpha_composite(_item_tile(images.get(w.icon), 112, RARITY.get(w.rarity, SIGNAL)), (x0 + 18, y + 8))
    d.text((x0 + 146, y + 14), shorten(d, w.name, font(34, "semibold"), gx - x0 - 190), font=font(34, "semibold"), fill=BG)
    stars(d, x0 + 148, y + 62, w.rarity, 16, RARITY.get(w.rarity, SIGNAL), gap=3)
    meta = f"Lv {w.level}  ·  Break {w.breakthrough}  ·  Refine"
    d.text((x0 + 148, y + 86), meta, font=font(21), fill=soft)
    mark = potential_mark(40, w.refine, SIGNAL, (78, 81, 90))
    canvas.alpha_composite(mark, (int(x0 + 154 + d.textlength(meta, font=font(21))), y + 77))

    if w.skills:
        left, room = x0 + 24, gx - x0 - 72
        col = room // len(w.skills)
        sy = y + 134
        d.line([(left, sy - 10), (gx - 48, sy - 10)], fill=(52, 55, 62), width=1)
        for i, skill in enumerate(w.skills):
            sx = left + i * col
            name = skill.name.split(":")[0]
            d.text((sx, sy), shorten(d, name, font(17), col - 16), font=font(17), fill=soft)
            value = f"{skill.value} {tr(skill.stat)}".strip() if skill.value else ""
            vf = font(23, "semibold")
            while vf.size > 17 and d.textlength(value, font=vf) > col - 16:
                vf = font(vf.size - 1, "semibold")
            d.text((sx, sy + 24 + (23 - vf.size) // 2), shorten(d, value or "-", vf, col - 16), font=vf, fill=BG)
            boosted = min(skill.level, next((term.points for term in (w.essence.terms if w.essence else [])
                                             if term.name == skill.name), 0))
            own, extra = _pip(fill=(236, 236, 240)), _pip()
            for k in range(skill.level):
                canvas.alpha_composite(own if k < skill.level - boosted else extra, (int(sx + k * 13), int(sy + 56)))

    gem = w.essence
    if gem:
        d.line([(gx - 24, y + 22), (gx - 24, y + box_h - 22)], fill=(60, 63, 70), width=2)
        canvas.alpha_composite(_item_tile(_essence_image(images.get(gem.icon), images.get(gem.badge)), 76, ESSENCE),
                               (gx - 2, y + 18))
        d.text((gx + 90, y + 20), "ESSENCE", font=font(15, "bold"), fill=(150, 152, 160))
        d.text((gx + 90, y + 38), shorten(d, gem.name, font(28, "semibold"), 220), font=font(28, "semibold"), fill=SIGNAL)
        ty = y + 108
        for term in gem.terms[:3]:
            points = f"+{term.points}"
            px = right - 24 - d.textlength(points, font=number(21))
            d.text((px, ty - 1), points, font=number(21), fill=BG)
            d.line([(px - 10, ty + 3), (px - 10, ty + 21)], fill=(70, 73, 80), width=2)
            pills_x = _pips(canvas, px - 14, ty + 4, term.points)
            d.text((gx, ty), shorten(d, term.name, font(19), pills_x - gx - 10), font=font(19), fill=soft)
            ty += 32
    return y + box_h + 26


def _gear(canvas, d, build: Build, images, x0, right, y):
    _label(d, x0, y, "Gear")
    set_name, count = build.gear_set
    hx = x0 + d.textlength("GEAR", font=font(18, "semibold")) + 24
    if set_name:
        d.text((hx, y - 5), set_name, font=font(24, "semibold"), fill=TEXT)
        px = hx + d.textlength(set_name, font=font(24, "semibold")) + 16
        lit, dim = _pip(), _pip(fill=HAIR)
        for k in range(4):
            canvas.alpha_composite(lit if k < count else dim, (int(px + k * 16), y + 3))
    if build.tactical:
        tactical = build.tactical
        tw = d.textlength(tactical.name, font=font(20))
        d.text((right - tw, y - 3), tactical.name, font=font(20), fill=MUTED)
        _tile(canvas, images.get(tactical.icon), int(right - tw - 46), y - 8, 36, radius=9)

    gap = 16
    cw = (right - x0 - gap * 3) // 4
    ch = 222
    top = y + 34
    if not build.gear:
        for i, slot in enumerate(("Armor", "Gloves", "Kit", "Kit")):
            cx = x0 + i * (cw + gap)
            for k in range(0, cw, 18):
                d.line([(cx + k, top), (cx + min(k + 9, cw), top)], fill=HAIR, width=2)
                d.line([(cx + k, top + ch), (cx + min(k + 9, cw), top + ch)], fill=HAIR, width=2)
            for k in range(0, ch, 18):
                d.line([(cx, top + k), (cx, top + min(k + 9, ch))], fill=HAIR, width=2)
                d.line([(cx + cw, top + k), (cx + cw, top + min(k + 9, ch))], fill=HAIR, width=2)
            d.text((cx + 18, top + 16), slot.upper(), font=font(16, "bold"), fill=MUTED)
            empty = "Empty"
            d.text((cx + cw / 2 - d.textlength(empty, font=font(22)) / 2, top + ch / 2 - 14), empty, font=font(22), fill=HAIR)
        return top + ch
    lit, dim = _pip(w=12, h=15, s=4), _pip(w=12, h=15, s=4, fill=HAIR)
    for i, piece in enumerate(build.gear[:4]):
        cx = x0 + i * (cw + gap)
        rare = RARITY.get(piece.rarity, SIGNAL)
        s = 4
        card = Image.new("RGBA", (cw * s, ch * s))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, cw * s - 1, ch * s - 1), 18 * s, fill=CARD + (255,))
        band = Image.new("L", card.size)
        ImageDraw.Draw(band).rectangle((0, 0, cw * s, 7 * s), fill=255)
        band = ImageChops.multiply(band, card.getchannel("A"))
        card.paste(rare + (255,), (0, 0), band)
        ImageDraw.Draw(card).rounded_rectangle((0, 0, cw * s - 1, ch * s - 1), 18 * s, outline=HAIR + (255,), width=2 * s)
        canvas.alpha_composite(card.resize((cw, ch), Image.LANCZOS), (cx, top))
        canvas.alpha_composite(_item_tile(images.get(piece.icon), 64, rare), (cx + 14, top + 18))
        d.text((cx + 90, top + 20), piece.slot.upper(), font=font(15, "bold"), fill=MUTED)
        defense = f"DEF {piece.defense}"
        df = number(30)
        while d.textlength(defense, font=df) > cw - 104 and df.size > 18:
            df = number(df.size - 2)
        d.text((cx + 90, top + 40 + (30 - df.size) // 2), defense, font=df, fill=TEXT)
        if not piece.lines:
            d.text((cx + 14, top + 100), "stats unavailable", font=font(18), fill=MUTED)
            continue
        ly = top + 100
        for k, line in enumerate(piece.lines[:3]):
            if k:
                d.line([(cx + 14, ly - 9), (cx + cw - 14, ly - 9)], fill=(232, 230, 223), width=1)
            value_w = d.textlength(line.text, font=number(22))
            vx = cx + cw - 14 - value_w
            glyph = icon(line.name, 16, MUTED)
            nx = cx + 14 + (glyph.width + 6 if glyph is not None else 0)
            room = vx - nx - 10
            f = font(16) if d.textlength(line.name, font=font(16)) <= room else font(14)
            if glyph is not None:
                canvas.alpha_composite(glyph, (cx + 14, ly - 6))
            d.text((nx, ly - 8 + (0 if f.size == 16 else 2)), shorten(d, line.name, f, room), font=f, fill=MUTED)
            for m in range(line.max_level):
                canvas.alpha_composite(lit if m < line.level else dim, (int(nx + m * 12), ly + 14))
            d.text((vx, ly - 1), line.text, font=number(22), fill=TEXT)
            ly += 40
    return top + ch


def _footer(d, build: Build, hide_uid):
    o = build.owner
    y = H - 46
    uid = f"UID {o.uid}"
    d.text((1000, y), f"{o.name}  ·  {uid}  ·  Authority {o.level}", font=font(20), fill=MUTED)
    d.text((1930 - d.textlength("akef", font=font(20, "semibold")), y), "akef", font=font(20, "semibold"), fill=MUTED)


def render(build: Build, images, *, art=None, hide_uid=False) -> Image.Image:
    canvas = Image.new("RGBA", (W, H), BG)
    _hero(canvas, build, images, art)
    _talent_dock(canvas, build, images)
    d = canvas_draw(canvas)
    x0, right = 1000, 1930
    y = _headline(canvas, d, build, images, x0, right - x0)
    if build.stats is not None:
        y = _stats(d, build, x0, right - x0, y)
    y = _skills(canvas, d, build, images, x0, right - x0, y)
    y = _weapon(canvas, d, build, images, x0, right, y)
    _gear(canvas, d, build, images, x0, right, y)
    _footer(d, build, hide_uid)
    return canvas.convert("RGB")
