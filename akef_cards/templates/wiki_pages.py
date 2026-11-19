from __future__ import annotations

import threading

from PIL import Image, ImageChops

from akef_cards.draw import canvas_draw, cover, fit, font, number
from akef_cards.templates.showcase import BG, CARD, HAIR, MUTED, SIGNAL, SLATE, TEXT, _wrap
from akef.wiki import Cost, Node, WikiPage

LIGHT = {"bg": BG, "card": CARD, "line": HAIR, "text": TEXT, "dim": MUTED}
DARK = {"bg": (15, 16, 20), "card": (26, 28, 34), "line": (44, 47, 56), "text": (240, 241, 245), "dim": (140, 144, 154)}
P = LIGHT
_lock = threading.Lock()


def _themed(draw):
    def run(page, images, *, hide_uid=False, dark=False):
        global P
        with _lock:
            P = DARK if dark else LIGHT
            try:
                return draw(page, images, hide_uid=hide_uid)
            finally:
                P = LIGHT
    run.__name__ = draw.__name__
    return run

CHIP = BG


W = 2000
PAD = 56
HEAD = 200
AMBER = (176, 126, 0)


def _lines(d, text, f, room, limit=99):
    out = []
    for para in text.splitlines():
        if para.strip() and len(out) < limit:
            out += _wrap(d, para.strip(), f, room, limit - len(out))
    return out[:limit]


def _canvas(page: WikiPage, images, title: str, height: int):
    canvas = Image.new("RGBA", (W, height), P["bg"])
    art = images.get(page.art)
    if art is not None:
        band = cover(art, 900, HEAD, 0.18)
        fade = Image.new("L", (900, 1))
        for x in range(900):
            fade.putpixel((x, 0), int(255 * min(1.0, x / 420)))
        band.putalpha(ImageChops.multiply(band.getchannel("A"), fade.resize((900, HEAD))))
        canvas.alpha_composite(band, (W - 900, 0))
    d = canvas_draw(canvas)
    d.text((PAD, 46), title.upper(), font=font(20, "bold"), fill=SIGNAL)
    d.text((PAD - 3, 72), page.name, font=number(84), fill=P["text"])
    d.line([(PAD, HEAD), (W - PAD, HEAD)], fill=P["line"], width=2)
    d.text((W - PAD - d.textlength("akef", font=font(18, "semibold")), height - 46), "akef", font=font(18, "semibold"),
           fill=P["dim"])
    d.text((PAD, height - 46), "via skport wiki", font=font(18), fill=P["dim"])
    return canvas, d


def _icon(canvas, d, img, x, y, size, ring=None, radius=14):
    d.rounded_rectangle((x, y, x + size, y + size), radius, fill=SLATE, outline=ring, width=2 if ring else 0)
    if img is not None:
        g = fit(img, size - 10, size - 10)
        canvas.alpha_composite(g, (x + size // 2 - g.width // 2, y + size // 2 - g.height // 2))


def _costs(canvas, d, costs: list[Cost], images, x, y, size=46):
    for cost in costs:
        _icon(canvas, d, images.get(cost.icon), x, y, size, radius=10)
        count = f"{cost.count:,}" if cost.count else ""
        if count:
            tw = d.textlength(count, font=number(15))
            d.rounded_rectangle((x + size - tw - 10, y + size - 16, x + size + 2, y + size + 4), 8, fill=SIGNAL)
            d.text((x + size - tw - 4, y + size - 16), count, font=number(15), fill=SLATE)
        x += size + 14
    return x


def _render_skills(page: WikiPage, images, *, hide_uid: bool = False) -> Image.Image:
    cols, gap = 2, 24
    cw = (W - PAD * 2 - gap) // cols
    probe = canvas_draw(Image.new("RGB", (10, 10)))
    heights = [110 + 27 * len(_lines(probe, s.text, font(19), cw - 60)) for s in page.skills]
    rows = [max(heights[i:i + cols]) for i in range(0, len(heights), cols)]
    height = HEAD + 40 + sum(rows) + gap * max(0, len(rows) - 1) + 90
    canvas, d = _canvas(page, images, "Wiki · Skills", height)
    y = HEAD + 40
    for r, row_h in enumerate(rows):
        for c, skill in enumerate(page.skills[r * cols:(r + 1) * cols]):
            x = PAD + c * (cw + gap)
            d.rounded_rectangle((x, y, x + cw, y + row_h), 22, fill=P["card"], outline=P["line"], width=2)
            _icon(canvas, d, images.get(skill.icon), x + 24, y + 22, 64)
            d.text((x + 106, y + 24), skill.name, font=font(28, "semibold"), fill=P["text"])
            kind = skill.kind.upper()
            kw = d.textlength(kind, font=font(15, "bold")) + 22
            d.rounded_rectangle((x + 106, y + 62, x + 106 + kw, y + 88), 13, fill=SIGNAL)
            d.text((x + 117, y + 65), kind, font=font(15, "bold"), fill=SLATE)
            ty = y + 104
            for line in _lines(d, skill.text, font(19), cw - 60):
                heading = line.endswith(":") and line.upper() == line
                d.text((x + 30, ty), line, font=font(19, "semibold" if heading else "regular"),
                       fill=P["text"] if heading else P["dim"])
                ty += 27
        y += row_h + gap
    return canvas.convert("RGB")


def _node_height(d, node: Node, room) -> int:
    rows = 0
    for tier in node.tiers:
        rows += max(1, len(_lines(d, tier.effect, font(18), room)))
    return 92 + 30 * rows + 62 * len(node.tiers)


def _node(canvas, d, node: Node, images, x, y, w):
    room = w - 470
    h = _node_height(d, node, room)
    d.rounded_rectangle((x, y, x + w, y + h), 22, fill=P["card"], outline=P["line"], width=2)
    _icon(canvas, d, images.get(node.icon), x + 22, y + 20, 56)
    d.text((x + 94, y + 18), node.name, font=font(26, "semibold"), fill=P["text"])
    d.text((x + 94, y + 52), node.kind.upper(), font=font(15, "bold"), fill=P["dim"])
    ty = y + 92
    for tier in node.tiers:
        d.line([(x + 22, ty - 10), (x + w - 22, ty - 10)], fill=P["line"], width=1)
        d.text((x + 24, ty), tier.name, font=font(18, "semibold"), fill=P["text"])
        lines = _lines(d, tier.effect, font(18), room) or [""]
        for i, line in enumerate(lines):
            d.text((x + 24, ty + 28 + i * 30), line, font=font(18), fill=P["dim"])
        if tier.requirement:
            d.text((x + 24, ty + 28 + len(lines) * 30), tier.requirement, font=font(16), fill=AMBER)
        _costs(canvas, d, tier.costs, images, x + w - 24 - len(tier.costs) * 60 + 14, ty + 4)
        ty += 30 * len(lines) + 62
    return h


def _render_talents(page: WikiPage, images, *, hide_uid: bool = False) -> Image.Image:
    cols, gap = 2, 24
    cw = (W - PAD * 2 - gap) // cols
    probe = canvas_draw(Image.new("RGB", (10, 10)))
    nodes = page.talents
    heights = [_node_height(probe, n, cw - 470) for n in nodes]
    col_y = [0, 0]
    places = []
    for n, h in zip(nodes, heights):
        c = col_y.index(min(col_y))
        places.append((c, col_y[c]))
        col_y[c] += h + gap
    height = HEAD + 40 + max(col_y) + 70
    canvas, d = _canvas(page, images, "Wiki · Talents", height)
    for node, (c, oy) in zip(nodes, places):
        _node(canvas, d, node, images, PAD + c * (cw + gap), HEAD + 40 + oy, cw)
    return canvas.convert("RGB")


def _render_growth(page: WikiPage, images, *, hide_uid: bool = False) -> Image.Image:
    gap = 24
    lw = 900
    rw = W - PAD * 2 - lw - gap
    probe = canvas_draw(Image.new("RGB", (10, 10)))
    pot_h = [max(96, 64 + 27 * len(_lines(probe, p.text, font(18), rw - 140))) for p in page.potentials]
    left_h = 40 + len(page.promotions) * 112
    right_h = 40 + sum(pot_h) + 14 * len(pot_h)
    height = HEAD + 40 + max(left_h, right_h) + 80
    canvas, d = _canvas(page, images, "Wiki · Promotion and potential", height)

    y = HEAD + 40
    d.text((PAD, y), "PROMOTIONS", font=font(18, "bold"), fill=P["dim"])
    y += 34
    for node in page.promotions:
        tier = node.tiers[0] if node.tiers else None
        d.rounded_rectangle((PAD, y, PAD + lw, y + 98), 18, fill=P["card"], outline=P["line"], width=2)
        _icon(canvas, d, images.get(node.icon), PAD + 16, y + 16, 66)
        d.text((PAD + 100, y + 14), node.name, font=font(22, "semibold"), fill=P["text"])
        if tier:
            d.text((PAD + 100, y + 44), _lines(d, tier.effect, font(16), 440, 1)[0] if tier.effect else "", font=font(16),
                   fill=P["dim"])
            d.text((PAD + 100, y + 68), tier.requirement, font=font(15), fill=AMBER)
            _costs(canvas, d, tier.costs, images, PAD + lw - 20 - len(tier.costs) * 60 + 14, y + 24)
        y += 112

    x, y = PAD + lw + gap, HEAD + 40
    d.text((x, y), "POTENTIALS", font=font(18, "bold"), fill=P["dim"])
    y += 34
    for i, (pot, h) in enumerate(zip(page.potentials, pot_h)):
        d.rounded_rectangle((x, y, x + rw, y + h), 18, fill=P["card"], outline=P["line"], width=2)
        _icon(canvas, d, images.get(pot.icon), x + 16, y + 16, 72, ring=SIGNAL)
        d.text((x + 106, y + 14), f"P{i + 1}  {pot.name}", font=font(22, "semibold"), fill=P["text"])
        for j, line in enumerate(_lines(d, pot.text, font(18), rw - 140)):
            d.text((x + 106, y + 46 + j * 27), line, font=font(18), fill=P["dim"])
        y += h + 14
    return canvas.convert("RGB")


def _render_profile(page: WikiPage, images, *, hide_uid: bool = False) -> Image.Image:
    gap = 24
    cols = 2
    cw = (W - PAD * 2 - gap) // cols
    probe = canvas_draw(Image.new("RGB", (10, 10)))
    facts = [i for i in page.intel if not i.text]
    stories = [i for i in page.intel if i.text]
    heights = [70 + 27 * len(_lines(probe, s.text, font(19), cw - 56)) for s in stories]
    rows = [max(heights[i:i + cols]) for i in range(0, len(heights), cols)]
    weapon_h = 230 if any(costs for _, costs in page.weapons) else 0
    height = HEAD + 40 + 120 + sum(rows) + gap * len(rows) + weapon_h + 80
    canvas, d = _canvas(page, images, "Wiki · Profile", height)

    y = HEAD + 40
    x = PAD
    for label, value in [(f.label, f.title) for f in facts] + [i for i in page.info if i[0] not in {f.label for f in facts}]:
        lf, vf = font(16, "semibold"), font(22, "semibold")
        w = d.textlength(label, font=lf) + d.textlength(value, font=vf) + 44
        if x + w > W - PAD:
            break
        d.rounded_rectangle((x, y, x + w, y + 46), 23, fill=SLATE)
        d.text((x + 18, y + 13), label, font=lf, fill=(160, 162, 170))
        d.text((x + 26 + d.textlength(label, font=lf), y + 9), value, font=vf, fill=CHIP)
        x += w + 12
    y += 46 + 40
    if page.quote:
        d.rounded_rectangle((PAD, y, PAD + 6, y + 34), 3, fill=SIGNAL)
        d.text((PAD + 22, y), f"“{page.quote}”", font=font(26, "semibold"), fill=P["text"])
    y += 60

    for r, row_h in enumerate(rows):
        for c, story in enumerate(stories[r * cols:(r + 1) * cols]):
            sx = PAD + c * (cw + gap)
            d.rounded_rectangle((sx, y, sx + cw, y + row_h), 20, fill=P["card"], outline=P["line"], width=2)
            d.text((sx + 26, y + 18), story.label.upper(), font=font(15, "bold"), fill=AMBER)
            d.text((sx + 26 + d.textlength(story.label.upper(), font=font(15, "bold")) + 14, y + 13), story.title,
                   font=font(22, "semibold"), fill=P["text"])
            for j, line in enumerate(_lines(d, story.text, font(19), cw - 56)):
                d.text((sx + 26, y + 56 + j * 27), line, font=font(19), fill=P["dim"])
        y += row_h + gap

    if weapon_h:
        d.text((PAD, y + 6), "RECOMMENDED WEAPONS", font=font(18, "bold"), fill=P["dim"])
        x = PAD
        for label, costs in page.weapons:
            if not costs:
                continue
            d.text((x, y + 40), label, font=font(17, "semibold"), fill=P["text"])
            for cost in costs:
                _icon(canvas, d, images.get(cost.icon), x, y + 68, 84, radius=14)
                for j, line in enumerate(_lines(d, cost.name, font(14), 140, 2)):
                    d.text((x, y + 160 + j * 18), line, font=font(14), fill=P["dim"])
                x += 156
            x += 30
    return canvas.convert("RGB")


def _render_lore(page: WikiPage, images, *, hide_uid: bool = False) -> Image.Image:
    gap = 24
    cw = (W - PAD * 2 - gap) // 2
    probe = canvas_draw(Image.new("RGB", (10, 10)))
    heights = [80 + 26 * len(_lines(probe, s.text, font(18), cw - 56)) for s in page.stories]
    cols, places = [0, 0], []
    for h in heights:
        c = cols.index(min(cols))
        places.append((c, cols[c]))
        cols[c] += h + gap
    height = HEAD + 40 + max(cols) + 70
    canvas, d = _canvas(page, images, "Wiki · Lore", height)
    for story, h, (c, oy) in zip(page.stories, heights, places):
        x, y = PAD + c * (cw + gap), HEAD + 40 + oy
        d.rounded_rectangle((x, y, x + cw, y + h), 20, fill=P["card"], outline=P["line"], width=2)
        d.text((x + 26, y + 18), story.title, font=font(24, "semibold"), fill=P["text"])
        if story.unlock:
            uw = d.textlength(story.unlock, font=font(15, "bold"))
            d.text((x + cw - 26 - uw, y + 24), story.unlock, font=font(15, "bold"), fill=AMBER)
        for j, line in enumerate(_lines(d, story.text, font(18), cw - 56)):
            d.text((x + 26, y + 62 + j * 26), line, font=font(18), fill=P["dim"])
    return canvas.convert("RGB")


render_skills = _themed(_render_skills)


render_talents = _themed(_render_talents)


render_growth = _themed(_render_growth)


render_profile = _themed(_render_profile)


render_lore = _themed(_render_lore)
