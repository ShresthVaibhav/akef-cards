from functools import lru_cache

from PIL import Image, ImageDraw

from akef_cards.draw import canvas_draw, font, icon, number, shorten
from akef_cards.exploration import KINDS, Exploration, counted, done, missing, percent, share
from akef_cards.templates.factory_board import DARK, LIGHT, Theme
from akef_cards.templates.live_parts import bar, ring, round_avatar
from akef_cards.templates.showcase import SIGNAL

W = 1600
PAD = 56
GAP = 20
INK = (18, 18, 20)
CREAM = (255, 250, 214)
SAND = (236, 222, 150)
YELLOW = Theme(SIGNAL, CREAM, INK, INK, (92, 82, 20), (226, 190, 0), INK, SIGNAL)
KIND_ICONS = ("explore_puzzle", "explore_chest", "explore_equipment", "explore_collectible", "explore_datalogger",
              "explore_aurylene")
KIND_COLOURS = ((139, 108, 232), (232, 156, 42), (222, 92, 74), (52, 168, 148), (76, 132, 222), (212, 88, 160))


@lru_cache(maxsize=128)
def kind_icon(i: int, size: int) -> Image.Image:
    plate = Image.new("RGBA", (size * 4, size * 4))
    ImageDraw.Draw(plate).rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1), size, fill=KIND_COLOURS[i] + (255,))
    plate = plate.resize((size, size), Image.LANCZOS)
    glyph = icon(KIND_ICONS[i], int(size * 0.76), (255, 255, 255)).copy()
    alpha = glyph.getchannel("A")
    peak = alpha.getextrema()[1] or 255
    glyph.putalpha(alpha.point(lambda v: min(255, v * 255 // peak)))
    plate.alpha_composite(glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2))
    return plate


def _centred(d, cx, y, text, f, fill):
    d.text((cx - d.textlength(text, font=f) / 2, y), text, font=f, fill=fill)


def _right(d, x, y, text, f, fill):
    d.text((x - d.textlength(text, font=f), y), text, font=f, fill=fill)


def _sums(areas) -> tuple[int, int]:
    return sum(min(a.found, a.total) for a in areas), sum(a.total for a in areas)


def _kinds(areas) -> list[tuple[int, int]]:
    return [(sum(min(a.kinds[i][0], a.kinds[i][1]) for a in areas if a.kinds),
             sum(a.kinds[i][1] for a in areas if a.kinds)) for i in range(len(KINDS))]


def _count(found, total) -> str:
    return f"{found:,} / {total:,}" if total else "-"


def _header(canvas, d, e: Exploration, images, t: Theme, accent):
    av = 104
    avatar = images.get(e.avatar)
    d.ellipse((PAD - 5, 41, PAD + av + 5, 51 + av), fill=accent)
    if avatar is not None:
        canvas.alpha_composite(round_avatar(avatar, av), (PAD, 46))
    tx = PAD + av + 30
    d.text((tx, 44), shorten(d, e.name, number(56), 620), font=number(56), fill=t.text)
    d.text((tx, 112), f"UID {e.uid}  ·  {e.server}  ·  Authority {e.level}", font=font(24), fill=t.muted)
    _right(d, W - PAD, 48, "EXPLORATION", font(20, "bold"), accent)

    stats = (("EXPLORED", percent(e.found, e.total)),
             ("AREAS CLEARED", f"{sum(done(a) for a in e.areas)}/{len(e.areas)}"),
             ("ITEMS LEFT", f"{e.total - e.found:,}"))
    x = W - PAD
    for label, value in stats:
        w = max(d.textlength(value, font=number(40)), d.textlength(label, font=font(16, "bold")))
        _right(d, x, 96, label, font(16, "bold"), t.muted)
        _right(d, x, 114, value, number(40), t.text)
        x -= w + 44


def _footer(d, h, t: Theme):
    d.text((PAD, h - 44), "via skport", font=font(18), fill=t.muted)
    _right(d, W - PAD, h - 44, "akef", font(18, "semibold"), t.muted)


def _render(e: Exploration, images, t: Theme, accent, body) -> Image.Image:
    def paint(h):
        canvas = Image.new("RGBA", (W, h), t.bg)
        d = canvas_draw(canvas)
        _header(canvas, d, e, images, t, accent)
        return canvas, d, body(canvas, d, e, t, 200)

    rows = len(e.areas) + len(e.regions) * 3
    _, _, bottom = paint(900 + rows * 360)
    canvas, d, bottom = paint(bottom + 80)
    _footer(d, canvas.height, t)
    return canvas.convert("RGB")


def _region_title(d, region, t: Theme, y, accent):
    found, total = _sums(region.areas)
    d.text((PAD, y), region.name, font=number(40), fill=t.text)
    cleared = sum(done(a) for a in region.areas)
    note = f"{cleared}/{len(region.areas)} areas cleared  ·  {_count(found, total)}  ·  {percent(found, total)}"
    _right(d, W - PAD, y + 8, note, number(26), t.muted)
    bar(d, PAD, y + 60, W - PAD * 2, 8, share(found, total), accent, t.track)
    return y + 88


def _kind_strip(canvas, d, areas, t: Theme, y, accent):
    cw = (W - PAD * 2 - 12 * 5) // 6
    for i, (found, total) in enumerate(_kinds(areas)):
        x = PAD + i * (cw + 12)
        d.rounded_rectangle((x, y, x + cw, y + 104), 18, fill=t.card, outline=t.line, width=2)
        canvas.alpha_composite(kind_icon(i, 34), (x + 16, y + 14))
        d.text((x + 60, y + 19), shorten(d, KINDS[i], font(19, "semibold"), cw - 70), font=font(19, "semibold"),
               fill=t.text)
        d.text((x + 16, y + 54), _count(found, total), font=number(25), fill=t.text if total else t.muted)
        bar(d, x + 16, y + 88, cw - 32, 6, share(found, total), accent, t.track)
    return y + 104 + GAP


def _kind_rows(canvas, d, area, t: Theme, x, y, w):
    for i, (found, total) in enumerate(area.kinds):
        row = y + i * 38
        canvas.alpha_composite(kind_icon(i, 26), (x, row))
        d.text((x + 38, row), KINDS[i], font=font(20), fill=t.text if total else t.muted)
        bx = x + 196
        bar(d, bx, row + 9, w - 196 - 240, 8, share(found, total), SIGNAL if found < total else t.muted, t.track)
        _right(d, x + w - 108, row, _count(found, total), number(20), t.text if total else t.muted)
        if total:
            note = f"{total - found} left" if total > found else "done"
            _right(d, x + w, row, note, font(19, "semibold" if total > found else "regular"),
                   t.text if total > found else t.muted)


def _kind_grid(canvas, d, area, t: Theme, x, y, w):
    cw = w // 3
    for i, (found, total) in enumerate(area.kinds):
        cx, cy = x + (i % 3) * cw, y + (i // 3) * 62
        canvas.alpha_composite(kind_icon(i, 28), (cx, cy))
        d.text((cx + 38, cy - 4), _count(found, total), font=number(20),
               fill=t.text if total else t.muted)
        d.text((cx + 38, cy + 20), shorten(d, KINDS[i], font(15), cw - 44), font=font(15), fill=t.muted)
        if total:
            bar(d, cx, cy + 44, cw - 18, 5, share(found, total), SIGNAL if found < total else t.muted, t.track)


def _todo(canvas, d, e, t, y):
    wide = (W - PAD * 2 - GAP) // 2
    small = (W - PAD * 2 - GAP * 2) // 3
    for region in e.regions:
        y = _region_title(d, region, t, y, SIGNAL)
        y = _kind_strip(canvas, d, region.areas, t, y, SIGNAL)
        todo = sorted((a for a in region.areas if not done(a)), key=lambda a: a.total - a.found)
        if todo:
            d.text((PAD, y), "STILL TO DO", font=font(16, "bold"), fill=t.muted)
            y += 30
        for n, a in enumerate(todo):
            x = PAD + (n % 2) * (wide + GAP)
            top = y + (n // 2) * (330 + GAP)
            d.rounded_rectangle((x, top, x + wide, top + 330), 22, fill=t.card, outline=SIGNAL, width=3)
            d.text((x + 26, top + 16), shorten(d, a.name, font(28, "semibold"), wide - 170), font=font(28, "semibold"),
                   fill=t.text)
            _right(d, x + wide - 26, top + 14, percent(a.found, a.total), number(34), t.text)
            d.text((x + 26, top + 56), f"{_count(a.found, a.total)} found  ·  {a.total - a.found:,} left", font=font(20),
                   fill=t.muted)
            _kind_rows(canvas, d, a, t, x + 26, top + 96, wide - 52)
        y += ((len(todo) + 1) // 2) * (330 + GAP)

        cleared = [a for a in region.areas if done(a)]
        if cleared:
            d.text((PAD, y), "CLEARED", font=font(16, "bold"), fill=t.muted)
            y += 30
        for n, a in enumerate(cleared):
            x = PAD + (n % 3) * (small + GAP)
            top = y + (n // 3) * (184 + 14)
            d.rounded_rectangle((x, top, x + small, top + 184), 20, fill=t.card, outline=t.line, width=2)
            d.text((x + 22, top + 14), shorten(d, a.name, font(23, "semibold"), small - 150), font=font(23, "semibold"),
                   fill=t.text)
            _right(d, x + small - 22, top + 16, _count(a.found, a.total), number(20), t.muted)
            _kind_grid(canvas, d, a, t, x + 22, top + 62, small - 40)
        y += ((len(cleared) + 2) // 3) * (184 + 14) + 36
    return y


def _rings(canvas, d, e, t, y):
    cols = 3
    cw = (W - PAD * 2 - GAP * (cols - 1)) // cols
    tall = 330
    for region in e.regions:
        y = _region_title(d, region, t, y, SIGNAL)
        y = _kind_strip(canvas, d, region.areas, t, y, SIGNAL)
        for n, a in enumerate(region.areas):
            x = PAD + (n % cols) * (cw + GAP)
            top = y + (n // cols) * (tall + GAP)
            d.rounded_rectangle((x, top, x + cw, top + tall), 26, fill=t.card,
                                outline=SIGNAL if done(a) else t.line, width=2)
            size = 112
            canvas.alpha_composite(ring(size, share(a.found, a.total), SIGNAL, t.track, 11), (x + 22, top + 22))
            _centred(d, x + 22 + size / 2, top + 60, percent(a.found, a.total), number(28), t.text)
            tx = x + 22 + size + 20
            d.text((tx, top + 32), shorten(d, a.name, font(24, "semibold"), cw - size - 62), font=font(24, "semibold"),
                   fill=t.text)
            d.text((tx, top + 66), f"{_count(a.found, a.total)} found", font=font(19), fill=t.muted)
            left = missing(a)
            status = "CLEARED" if done(a) else f"{a.total - a.found:,} LEFT"
            if len(left) == 1:
                status = f"{counted(left[0][1], left[0][0]).upper()} LEFT"
            d.text((tx, top + 96), shorten(d, status, font(18, "bold"), cw - size - 62), font=font(18, "bold"),
                   fill=SIGNAL if done(a) else t.text)
            d.line((x + 22, top + 154, x + cw - 22, top + 154), fill=t.line, width=2)
            _kind_grid(canvas, d, a, t, x + 22, top + 176, cw - 40)
        y += ((len(region.areas) + cols - 1) // cols) * (tall + GAP) + 36
    return y


def _poster(canvas, d, e, t, y):
    grey, white = (150, 150, 156), (240, 240, 240)
    d.rounded_rectangle((PAD, y, W - PAD, y + 168), 28, fill=INK)
    d.text((PAD + 32, y + 4), percent(e.found, e.total), font=number(100), fill=SIGNAL)
    d.text((PAD + 36, y + 124), f"{e.found:,} of {e.total:,} found", font=font(22, "semibold"), fill=white)
    start = PAD + 320
    step = (W - PAD - 16 - start) // 6
    for i, (label, found, total) in enumerate(e.kind_totals()):
        x = start + i * step
        canvas.alpha_composite(kind_icon(i, 34), (x, y + 20))
        d.text((x + 44, y + 26), shorten(d, label, font(17, "bold"), step - 52), font=font(17, "bold"), fill=grey)
        value = "-" if not total else f"{total - found:,} left" if total > found else "DONE"
        d.text((x, y + 62), value, font=number(34), fill=SIGNAL if total > found else white)
        d.text((x, y + 108), _count(found, total), font=font(18), fill=grey)
        bar(d, x, y + 140, step - 28, 6, share(found, total), SIGNAL, (52, 52, 58))
    y += 168 + 20

    cols = 3
    cw = (W - PAD * 2 - 14 * (cols - 1)) // cols
    for region in e.regions:
        found, total = _sums(region.areas)
        d.rounded_rectangle((PAD, y, W - PAD, y + 54), 18, fill=INK)
        d.text((PAD + 22, y + 8), shorten(d, region.name, number(28), 600), font=number(28), fill=SIGNAL)
        _right(d, W - PAD - 22, y + 11, f"{_count(found, total)}  ·  {percent(found, total)}", number(23),
               (240, 240, 240))
        y += 54 + 12
        for n, a in enumerate(region.areas):
            x = PAD + (n % cols) * (cw + 14)
            _poster_area(canvas, d, a, x, y + (n // cols) * (156 + 12), cw)
        y += ((len(region.areas) + cols - 1) // cols) * (156 + 12) + 8
    return y


def _poster_area(canvas, d, a, x, y, w):
    d.rounded_rectangle((x, y, x + w, y + 156), 20, fill=CREAM, outline=INK, width=3)
    note = "DONE" if done(a) else f"{a.total - a.found:,} LEFT"
    nw = d.textlength(note, font=font(16, "bold")) + 22
    d.rounded_rectangle((x + w - 16 - nw, y + 12, x + w - 16, y + 40), 14, fill=SAND if done(a) else INK)
    d.text((x + w - 5 - nw, y + 16), note, font=font(16, "bold"), fill=INK if done(a) else SIGNAL)
    d.text((x + 18, y + 10), shorten(d, a.name, font(23, "semibold"), w - nw - 50), font=font(23, "semibold"), fill=INK)
    bar(d, x + 18, y + 55, w - 112, 8, share(a.found, a.total), INK, SAND)
    _right(d, x + w - 18, y + 47, percent(a.found, a.total), number(19), INK)

    cell = (w - 28) // 3
    for i, (found, total) in enumerate(a.kinds):
        cx, cy = x + 18 + (i % 3) * cell, y + 76 + (i // 3) * 38
        lacking = total > found
        if lacking:
            d.rounded_rectangle((cx - 6, cy - 3, cx + cell - 10, cy + 33), 10, fill=INK)
        canvas.alpha_composite(kind_icon(i, 30), (cx, cy))
        d.text((cx + 38, cy + 3), _count(found, total), font=number(20),
               fill=SIGNAL if lacking else INK if total else (150, 136, 60))


def render_todo(e: Exploration, images, *, hide_uid: bool = False) -> Image.Image:
    return _render(e, images, LIGHT, SIGNAL, _todo)


def render_rings(e: Exploration, images, *, hide_uid: bool = False) -> Image.Image:
    return _render(e, images, DARK, SIGNAL, _rings)


def render_poster(e: Exploration, images, *, hide_uid: bool = False) -> Image.Image:
    return _render(e, images, YELLOW, INK, _poster)


TEMPLATES = {1: render_todo, 2: render_rings, 3: render_poster}
