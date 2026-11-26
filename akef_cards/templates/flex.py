from PIL import Image, ImageDraw

from akef_cards.draw import canvas_draw, class_badge, cover, fit, font, number, potential_mark, shorten, stars
from akef_cards.templates.profile import _round_mask
from akef_cards.templates.showcase import ELEMENT, RARITY, SIGNAL


def _shade(w, h, top, strength):
    layer = Image.new("RGBA", (w, h))
    ld = ImageDraw.Draw(layer)
    for row in range(h - top):
        k = row / max(h - top - 1, 1)
        ld.line([(0, top + row), (w, top + row)], fill=(8, 9, 12, int(strength * k ** 1.3)))
    return layer


def member(canvas, f, images, x, y, w, h, *, radius=22, compact=False):
    tint = ELEMENT.get(getattr(f, "element", ""), (110, 114, 124))
    card = Image.new("RGBA", (w, h), tuple(int(c * 0.45) for c in tint) + (255,))
    art = images.get(getattr(f, "art", "")) or images.get(getattr(f, "portrait", ""))
    if art is not None:
        card.alpha_composite(cover(art, w, h, 0.06))
    card.alpha_composite(_shade(w, h, int(h * 0.45), 235))
    card.putalpha(_round_mask((w, h), radius))
    canvas.alpha_composite(card, (int(x), int(y)))
    d = canvas_draw(canvas)
    rare = RARITY.get(getattr(f, "rarity", 0), SIGNAL)
    d.rounded_rectangle((x, y + h - 6, x + w, y + h), 3, fill=rare)

    size = max(30, w // 9)
    d.ellipse((x + 12, y + 12, x + 12 + size, y + 12 + size), fill=tint, outline=(255, 255, 255), width=2)
    glyph = images.get(getattr(f, "element_icon", ""))
    if glyph is not None:
        g = fit(glyph, int(size * 0.62), int(size * 0.62))
        canvas.alpha_composite(g, (int(x + 12 + size / 2 - g.width / 2), int(y + 12 + size / 2 - g.height / 2)))
    badge = class_badge(getattr(f, "profession", ""), size, (16, 17, 21)) if getattr(f, "profession", "") else None
    if badge is not None:
        canvas.alpha_composite(badge, (int(x + 18 + size), y + 12))
    star = int(size * 1.25)
    canvas.alpha_composite(potential_mark(star, getattr(f, "potential", 0), SIGNAL, (110, 112, 122)),
                           (int(x + w - star - 8), y + 6))

    name = getattr(f, "name", "") or ""
    nf = font(max(16, w // 11) if not compact else max(14, w // 9), "semibold")
    if name:
        d.text((x + 14, y + h - nf.size - 50), shorten(d, name, nf, w - 28), font=nf, fill=(255, 255, 255))
    lv = f"Lv {getattr(f, 'level', 0)}"
    lf = number(max(15, nf.size - 4))
    d.text((x + 14, y + h - lf.size - 18), lv, font=lf, fill=(220, 222, 230))
    marks = getattr(f, "rarity", 0)
    if marks and not compact:
        stars(d, x + w - 14 - marks * 17, y + h - 34, marks, 14, rare, gap=3)


def strip(canvas, team, images, x, y, size, gap=8):
    d = canvas_draw(canvas)
    for i, f in enumerate(team[:4]):
        mx = x + i * (size + gap)
        rare = RARITY.get(getattr(f, "rarity", 0), (120, 120, 120))
        d.rounded_rectangle((mx - 2, y - 2, mx + size + 2, y + size + 2), 12, fill=rare)
        img = images.get(getattr(f, "portrait", ""))
        if img is not None:
            face = cover(img, size, size, 0.1)
            face.putalpha(_round_mask((size, size), 10))
            canvas.alpha_composite(face, (mx, y))
        tint = ELEMENT.get(getattr(f, "element", ""))
        if tint:
            dot = size // 3
            d.ellipse((mx + size - dot + 2, y + size - dot + 2, mx + size + 4, y + size + 4), fill=tint)
    return 4 * (size + gap) - gap
