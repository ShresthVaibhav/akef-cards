from PIL import Image, ImageChops, ImageDraw

from akef.enka.build import Build
from akef_cards.draw import (
    body_x, brand, canvas_draw, cover, fit, font, icon, number, potential_mark, shorten, stand, stars,
)
from akef_cards.framing import splash_focus
from akef_cards.templates import showcase as base
from akef_cards.templates.showcase import ELEMENT_DMG, EXTRA_STATS, RARITY, SIGNAL


def element_badge(build: Build, images, size, ring=(255, 255, 255)):
    from akef_cards.templates.showcase import ELEMENT
    s = 4
    disc = Image.new("RGBA", (size * s, size * s))
    dd = ImageDraw.Draw(disc)
    dd.ellipse((0, 0, size * s - 1, size * s - 1), fill=ELEMENT.get(build.element, (120, 120, 130)) + (255,),
               outline=ring + (255,), width=2 * s)
    disc = disc.resize((size, size), Image.LANCZOS)
    glyph = images.get(build.element_icon)
    if glyph is not None:
        glyph = fit(glyph, int(size * 0.6), int(size * 0.6))
        disc.alpha_composite(glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2))
    return disc


def splash(build: Build, images, art, w, h, focus=0.1):
    if art is not None:
        return cover(art, w, h, focus)
    source = images.get(build.art)
    if source is None:
        return None
    focus = splash_focus(build)
    if focus is not None:
        return cover(base._frame_splash(source, focus), w, h, 0.0)
    img = stand(source, h - 30, int(w * 1.7))
    out = Image.new("RGBA", (w, h))
    out.paste(img, (w // 2 - body_x(img), h - img.height + 10), img)
    return out


def face_crop(build: Build, images, w, h, span=0.7):
    source = images.get(build.art)
    if source is None or splash_focus(build) is None:
        return splash(build, images, None, w, h, 0.0)
    cx, top, bottom = splash_focus(build)
    size = source.width
    figure = (bottom - top) * size
    cw = figure * span
    ch = cw * h / w
    fx, fy = cx * size, top * size + figure * 0.28
    box = (int(fx - cw / 2), int(fy - ch * 0.5), int(fx + cw / 2), int(fy + ch * 0.5))
    return source.convert("RGBA").crop(box).resize((w, h), Image.LANCZOS)


def two_pass(paint):
    _, bottom = paint(4000)
    canvas, _ = paint(bottom)
    return canvas.convert("RGB")


def extra_stats(build: Build):
    extras = [("Crit Rate", "crit_rate"), ("Crit DMG", "crit_dmg"), ("Ult Gain", "ult_gain"),
              ("Healing Received", "treatment_received")]
    own = ELEMENT_DMG.get(build.element)
    for name, field in EXTRA_STATS:
        if getattr(build.stats, field) > 1e-6:
            extras.insert(4 if field == own else len(extras), (name, field))
    s = build.stats
    return [(n, f"{s.arts_intensity:.0f}" if f == "arts_intensity" else s.percent(f)) for n, f in extras[:6]]


def attributes(build: Build):
    s = build.stats
    return [(name, getattr(s, field), s.main_attribute == field, s.sub_attribute == field)
            for name, field in (("STR", "strength"), ("AGI", "agility"), ("INT", "intellect"), ("WILL", "will"))]


def glyph(canvas, name, size, fill, x, y):
    g = icon(name, size, tuple(fill))
    if g is not None:
        canvas.alpha_composite(g, (int(x), int(y)))
        return g.width + 8
    return 0


def skills_block(canvas, d, build, images, x, y, w, p, cols=4):
    skills = build.skills[:4]
    cw = w // cols
    for i, skill in enumerate(skills):
        cx, cy = x + (i % cols) * cw, y + (i // cols) * 88
        d.rounded_rectangle((cx, cy, cx + 62, cy + 62), 12, fill=p["tile"])
        g = images.get(skill.icon)
        if g is not None:
            g = fit(g, 46, 46)
            canvas.alpha_composite(g, (cx + 31 - g.width // 2, cy + 31 - g.height // 2))
        d.rounded_rectangle((cx + 40, cy + 44, cx + 72, cy + 68), 8, fill=p["accent"])
        lv = str(skill.level)
        d.text((cx + 56 - d.textlength(lv, font=number(17)) / 2, cy + 45), lv, font=number(17), fill=p["on_accent"])
        room = cw - 86
        words = skill.name.replace("-", "- ").split(" ")
        f = next((font(size, "semibold") for size in (18, 16, 14, 13)
                  if all(d.textlength(word, font=font(size, "semibold")) <= room for word in words)), font(12, "semibold"))
        lines = base._wrap(d, skill.name, f, room, 2)
        for j, line in enumerate(lines):
            d.text((cx + 84, cy + 2 + j * 22), line, font=f, fill=p["text"])
        kind = shorten(d, skill.kind, font(14), cw - 100)
        d.text((cx + 84, cy + 6 + len(lines) * 22), kind, font=font(14), fill=p["dim"])
    return y + 88 * ((len(skills) + cols - 1) // cols) - 18


def weapon_block(canvas, d, build, images, x, y, w, p):
    wpn = build.weapon
    if wpn is None:
        d.text((x, y), "No weapon", font=font(22), fill=p["dim"])
        return y + 40
    canvas.alpha_composite(base._item_tile(images.get(wpn.icon), 92, RARITY.get(wpn.rarity, SIGNAL)), (x, y))
    d.text((x + 110, y), shorten(d, wpn.name, font(28, "semibold"), w - 120), font=font(28, "semibold"), fill=p["text"])
    stars(d, x + 112, y + 40, wpn.rarity, 16, RARITY.get(wpn.rarity, SIGNAL), gap=3)
    meta = f"Lv {wpn.level} · Break {wpn.breakthrough} · Refine"
    d.text((x + 112, y + 66), meta, font=font(18), fill=p["dim"])
    canvas.alpha_composite(potential_mark(32, wpn.refine, p["star"], p["star_dim"]),
                           (int(x + 118 + d.textlength(meta, font=font(18))), y + 59))
    y += 110
    cw = w // 3
    boosts = {t.name: t.points for t in (wpn.essence.terms if wpn.essence else [])}
    for i, skill in enumerate(wpn.skills[:3]):
        sx = x + i * cw
        value = f"{skill.value} {skill.stat}".strip() if skill.value else skill.name
        d.text((sx, y), shorten(d, skill.name, font(15), cw - 14), font=font(15), fill=p["dim"])
        value = shorten(d, value, font(19, "semibold"), cw - 14)
        d.text((sx, y + 20), value, font=font(19, "semibold"), fill=p["text"])
        boosted = min(skill.level, boosts.get(skill.name, 0))
        own, extra = base._pip(fill=p["pip"]), base._pip()
        for k in range(skill.level):
            canvas.alpha_composite(own if k < skill.level - boosted else extra, (int(sx + k * 12), y + 50))
    y += 84
    gem = wpn.essence
    if gem:
        canvas.alpha_composite(base._item_tile(base._essence_image(images.get(gem.icon), images.get(gem.badge)), 56,
                                               base.ESSENCE), (x, y - 1))
        d.text((x + 66, y + 2), "ESSENCE", font=font(13, "bold"), fill=p["dim"])
        title = shorten(d, gem.name, font(21, "semibold"), w - 80)
        d.text((x + 66, y + 18), title, font=font(21, "semibold"), fill=p["essence"])
        y += 66
        stacked = cw < 240
        for i, term in enumerate(gem.terms[:3]):
            sx, sy, room = (x, y + i * 30, w) if stacked else (x + i * cw, y, cw)
            d.text((sx, sy), shorten(d, term.name, font(16), room - 130), font=font(16), fill=p["dim"])
            base._pips(canvas, sx + room - 52, sy + 2, term.points, step=12)
            d.text((sx + room - 46, sy - 1), f"+{term.points}", font=number(18), fill=p["text"])
        y += 30 * min(len(gem.terms), 3) if stacked else 30
    return y


def gear_block(canvas, d, build, images, x, y, w, p, cols=4):
    set_name, count = build.gear_set
    if set_name:
        d.text((x, y), shorten(d, set_name, font(21, "semibold"), w - 100), font=font(21, "semibold"), fill=p["text"])
        sx = x + d.textlength(shorten(d, set_name, font(21, "semibold"), w - 100), font=font(21, "semibold")) + 14
        for k in range(count):
            canvas.alpha_composite(base._pip(), (int(sx + k * 13), y + 5))
        y += 38
    gap, th = 14, 178
    gw = (w - gap * (cols - 1)) // cols
    if not build.gear:
        th = 120
        for i, slot in enumerate(("Armor", "Gloves", "Kit", "Kit")):
            gx, gy = x + (i % cols) * (gw + gap), y + (i // cols) * (th + gap)
            for k in range(0, gw, 18):
                d.line([(gx + k, gy), (gx + min(k + 9, gw), gy)], fill=p["line"], width=2)
                d.line([(gx + k, gy + th), (gx + min(k + 9, gw), gy + th)], fill=p["line"], width=2)
            for k in range(0, th, 18):
                d.line([(gx, gy + k), (gx, gy + min(k + 9, th))], fill=p["line"], width=2)
                d.line([(gx + gw, gy + k), (gx + gw, gy + min(k + 9, th))], fill=p["line"], width=2)
            d.text((gx + 14, gy + 12), slot.upper(), font=font(13, "bold"), fill=p["dim"])
            d.text((gx + gw / 2 - d.textlength("Empty", font=font(18)) / 2, gy + th / 2 - 8), "Empty", font=font(18),
                   fill=p["dim"])
        return y + ((3 // cols) + 1) * (th + gap) - gap
    lit, dim = base._pip(w=10, h=12), base._pip(w=10, h=12, fill=p["pip_dim"])
    for i, piece in enumerate(build.gear[:4]):
        gx, gy = x + (i % cols) * (gw + gap), y + (i // cols) * (th + gap)
        p["card"](canvas, (gx, gy, gx + gw, gy + th))
        rare = RARITY.get(piece.rarity, SIGNAL)
        strip = Image.new("L", (gw * 4, th * 4))
        ImageDraw.Draw(strip).rounded_rectangle((0, 0, gw * 4 - 1, th * 4 - 1), 72, fill=255)
        ImageDraw.Draw(strip).rectangle((0, 24, gw * 4, th * 4), fill=0)
        layer = Image.new("RGBA", strip.size, rare + (255,))
        layer.putalpha(strip)
        canvas.alpha_composite(layer.resize((gw, th), Image.LANCZOS), (gx, gy))
        canvas.alpha_composite(base._item_tile(images.get(piece.icon), 46, rare), (gx + 10, gy + 12))
        d.text((gx + 66, gy + 12), piece.slot.upper(), font=font(13, "bold"), fill=p["dim"])
        d.text((gx + 66, gy + 28), f"DEF {piece.defense}", font=number(24), fill=p["text"])
        ly = gy + 74
        for k, line in enumerate(piece.lines[:3]):
            if k:
                d.line([(gx + 12, ly - 5), (gx + gw - 12, ly - 5)], fill=p["line"], width=1)
            vw = d.textlength(line.text, font=number(18))
            off = glyph(canvas, line.name, 15, p["dim"], gx + 12, ly + 2)
            label = shorten(d, line.name, font(15), gw - vw - off - 30)
            d.text((gx + 12 + off, ly), label, font=font(15), fill=p["dim"])
            d.text((gx + gw - 12 - vw, ly + 2), line.text, font=number(18), fill=p["text"])
            for m in range(line.max_level):
                canvas.alpha_composite(lit if m < line.level else dim, (gx + 12 + off + m * 11, ly + 20))
            ly += 34
    rows = (min(len(build.gear), 4) + cols - 1) // cols
    return y + rows * (th + gap) - gap


def boxed(canvas, box_fn, x, y, w, pad, draw_fn):
    layer = Image.new("RGBA", canvas.size)
    bottom = draw_fn(layer, canvas_draw(layer), x + pad, y + pad, w - 2 * pad)
    box_fn(canvas, (x, y, x + w, bottom + pad))
    canvas.alpha_composite(layer)
    return bottom + pad


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def shape(canvas, kind, geo, fill=None, outline=None, width=2, radius=0):
    pts = geo if kind == "poly" else [(geo[0], geo[1]), (geo[2], geo[3])]
    pad = width + 2
    x0, y0 = int(min(p[0] for p in pts)) - pad, int(min(p[1] for p in pts)) - pad
    x1, y1 = int(max(p[0] for p in pts)) + pad, int(max(p[1] for p in pts)) + pad
    layer = Image.new("RGBA", (max(1, x1 - x0), max(1, y1 - y0)))
    ld = ImageDraw.Draw(layer)
    moved = [(p[0] - x0, p[1] - y0) for p in pts]
    if kind == "poly":
        ld.polygon(moved, fill=fill, outline=outline, width=width if outline else 0)
    elif kind == "ellipse":
        ld.ellipse(moved, fill=fill, outline=outline, width=width)
    else:
        ld.rounded_rectangle(moved, radius, fill=fill, outline=outline, width=width)
    canvas.alpha_composite(layer, (x0, y0))


def gradient(w, h, top, bottom):
    img = Image.new("RGBA", (1, h))
    for y in range(h):
        img.putpixel((0, y), mix(top, bottom, y / max(h - 1, 1)) + (255,))
    return img.resize((w, h))


def fade(img, left=0, right=0, top=0, bottom=0):
    w, h = img.size
    mask = Image.new("L", (w, h), 255)
    md = ImageDraw.Draw(mask)
    for i in range(left):
        md.line([(i, 0), (i, h)], fill=int(255 * i / left))
    for i in range(right):
        md.line([(w - 1 - i, 0), (w - 1 - i, h)], fill=int(255 * i / right))
    edge = Image.new("L", (w, h), 255)
    ed = ImageDraw.Draw(edge)
    for i in range(top):
        ed.line([(0, i), (w, i)], fill=int(255 * i / top))
    for i in range(bottom):
        ed.line([(0, h - 1 - i), (w, h - 1 - i)], fill=int(255 * i / bottom))
    mask = ImageChops.multiply(mask, edge)
    img.putalpha(ImageChops.multiply(img.getchannel("A"), mask))
    return img


def footer(d, build, hide_uid, x, right, y, color):
    o = build.owner
    d.text((x, y), f"{o.name}  ·  UID {o.uid}  ·  Authority {o.level}", font=font(18), fill=color)
    brand(d, right, y, color)


def fit_name(d, text, start, room, low=40):
    f = number(start)
    while d.textlength(text, font=f) > room and f.size > low:
        f = number(f.size - 4)
    return f


def ink_bottom(text, f):
    # cjk and thai fallback fonts sit lower, so measure the drawn text
    probe = canvas_draw(Image.new("L", (1, 1)))
    img = Image.new("L", (int(probe.textlength(text, font=f)) + 20, int(f.size * 2)))
    canvas_draw(img).text((0, 0), text, font=f, fill=255)
    box = img.getbbox()
    return box[3] if box else f.size


def potential_after(canvas, d, build, text, f, x, y, lit, dim, k=0.72, gap=16):
    size = int(f.size * k)
    canvas.alpha_composite(potential_mark(size, build.potential, lit, dim),
                           (int(x + d.textlength(text, font=f) + gap), int(y + f.size * 0.6 - size / 2)))


def palette(**kw):
    base = {"on_accent": (16, 16, 20), "star": SIGNAL, "pip": (236, 236, 240), "essence": SIGNAL}
    base.update(kw)
    return base
