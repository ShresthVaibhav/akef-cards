from PIL import Image, ImageDraw

from akef.enka.build import Build, Talent
from akef_cards.draw import canvas_draw, fit, font, number, shorten

GREEK = "αβγδε"
LIT = (250, 250, 252)
UNLIT = (90, 93, 104)
INK = (16, 16, 20)


def _value_font(size):
    return number(max(12, int(size * 0.5)))


def stage(talent: Talent) -> str:
    if not talent.unlocked:
        return ""
    return GREEK[min(talent.level, len(GREEK)) - 1]


def _widths(build: Build, size: int):
    probe = canvas_draw(Image.new("RGBA", (1, 1)))
    out = []
    for t in build.talents:
        w = size
        if t.kind == "attribute" and t.value and t.unlocked:
            w += int(probe.textlength(t.value, font=_value_font(size))) + size // 4
        out.append(w)
    return out


def _gaps(build: Build, gap: int):
    return [gap + (gap if prev.kind != t.kind else 0) for prev, t in zip(build.talents, build.talents[1:])]


def row_width(build: Build, size: int, gap: int = 6) -> int:
    if not build.talents:
        return 0
    return sum(_widths(build, size)) + sum(_gaps(build, gap)) + size // 4


def _capsule(w, h, fill):
    s = 4
    pill = Image.new("RGBA", ((w + 2) * s, (h + 2) * s))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle((0, 0, (w + 2) * s - 1, (h + 2) * s - 1), (w + 2) * s // 2, fill=(0, 0, 0, 150))
    pd.rounded_rectangle((s, s, (w + 1) * s - 1, (h + 1) * s - 1), w * s // 2, fill=fill)
    pill = pill.rotate(-45, resample=Image.BICUBIC, expand=True)
    return pill.resize((pill.width // s, pill.height // s), Image.LANCZOS)


def _icon(canvas, images, t: Talent, x, y, size, scale):
    url = t.icon if t.unlocked or not t.locked_icon else t.locked_icon
    g = images.get(url)
    if g is None:
        return
    g = fit(g, int(size * scale), int(size * scale))
    if not t.unlocked:
        g = Image.merge("RGBA", (*[g.convert("L")] * 3, g.getchannel("A").point(lambda v: v // 2)))
    canvas.alpha_composite(g, (int(x + size / 2 - g.width / 2), int(y + size / 2 - g.height / 2)))


def _round(canvas, x, y, size, fill, ring):
    s = 4
    disc = Image.new("RGBA", (size * s, size * s))
    dd = ImageDraw.Draw(disc)
    dd.ellipse((0, 0, size * s - 1, size * s - 1), fill=fill)
    dd.ellipse((0, 0, size * s - 1, size * s - 1), outline=ring, width=int(size * 0.07 * s))
    canvas.alpha_composite(disc.resize((size, size), Image.LANCZOS), (int(x), int(y)))


def draw_row(canvas, build: Build, images, x, y, size, *, tile, text, gap=6, right=False) -> int:
    if not build.talents:
        return 0
    from akef_cards.templates.showcase import ELEMENT

    d = canvas_draw(canvas)
    tint = ELEMENT.get(build.element, (110, 114, 124))
    widths, gaps = _widths(build, size), _gaps(build, gap) + [0]
    total = row_width(build, size, gap)
    cx = x - total if right else x
    cw, ch = max(5, int(size * 0.15)), max(10, int(size * 0.36))
    for t, w, step in zip(build.talents, widths, gaps):
        if t.kind == "base":
            d.rounded_rectangle((cx, y, cx + size, y + size), max(3, size // 9), fill=tile,
                                outline=(0, 0, 0, 90), width=1)
            _icon(canvas, images, t, cx, y, size, 0.84)
            letter = stage(t)
            if letter:
                f = font(max(11, int(size * 0.5)), "bold")
                lx, ly = cx + size - size * 0.22, y + size - size * 0.3
                for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1)):
                    d.text((lx + ox - d.textlength(letter, font=f) / 2, ly + oy - f.size * 0.7), letter, font=f, fill=INK)
                d.text((lx - d.textlength(letter, font=f) / 2, ly - f.size * 0.7), letter, font=f, fill=LIT)
        else:
            on = t.unlocked
            _round(canvas, cx, y, size, (tint + (255,)) if on else (40, 42, 50, 200), (0, 0, 0, 110))
            _icon(canvas, images, t, cx, y, size, 0.8)
            if t.kind == "attribute":
                if t.value and t.unlocked:
                    f = _value_font(size)
                    d.text((cx + size + size // 6, y + (size - f.size * 1.2) / 2), t.value, font=f,
                           fill=text if t.maxed else UNLIT)
            else:
                lit, unlit = _capsule(cw, ch, LIT), _capsule(cw, ch, UNLIT)
                step_x = lit.width * 0.62
                for k in range(t.max_level):
                    px = int(cx + size - lit.width * 0.55 - (t.max_level - 1 - k) * step_x)
                    canvas.alpha_composite(lit if k < t.level else unlit, (px, int(y + size - lit.height * 0.7)))
        cx += w + step
    return total


def _padlock(size, color=(150, 153, 164)):
    s = 4
    img = Image.new("RGBA", (size * s, size * s))
    d = ImageDraw.Draw(img)
    w = size * s
    body = (w * 0.22, w * 0.46, w * 0.78, w * 0.86)
    d.arc((w * 0.32, w * 0.16, w * 0.68, w * 0.62), 180, 360, fill=color, width=int(w * 0.09))
    d.line([(w * 0.32 + w * 0.045, w * 0.39), (w * 0.32 + w * 0.045, w * 0.5)], fill=color, width=int(w * 0.09))
    d.line([(w * 0.68 - w * 0.045, w * 0.39), (w * 0.68 - w * 0.045, w * 0.5)], fill=color, width=int(w * 0.09))
    d.rounded_rectangle(body, w * 0.08, fill=color)
    return img.resize((size, size), Image.LANCZOS)


def _node(canvas, images, t: Talent, x, y, size, lit, tint, square, tile):
    s = 4
    plate = Image.new("RGBA", (size * s, size * s))
    pd = ImageDraw.Draw(plate)
    box = (0, 0, size * s - 1, size * s - 1)
    fill = (tint + (255,)) if lit else tile + (255,)
    ring = (255, 200, 0, 255) if lit else (70, 73, 84, 255)
    if square:
        pd.rounded_rectangle(box, size * s // 6, fill=fill, outline=ring, width=int(size * s * 0.07))
    else:
        pd.ellipse(box, fill=fill, outline=ring, width=int(size * s * 0.07))
    canvas.alpha_composite(plate.resize((size, size), Image.LANCZOS), (int(x), int(y)))
    if lit:
        g = images.get(t.icon)
        if g is not None:
            g = fit(g, int(size * 0.66), int(size * 0.66))
            canvas.alpha_composite(g, (int(x + size / 2 - g.width / 2), int(y + size / 2 - g.height / 2)))
    else:
        lock = _padlock(int(size * 0.56))
        canvas.alpha_composite(lock, (int(x + size / 2 - lock.width / 2), int(y + size / 2 - lock.height / 2)))


def draw_tree(canvas, build: Build, images, x, y, width, *, tile=(36, 38, 46), text=(236, 237, 240),
              dim=(140, 144, 154), size=34, step=50, row=52) -> int:
    from akef_cards.templates.showcase import ELEMENT

    if not build.talents:
        return y
    d = canvas_draw(canvas)
    tint = ELEMENT.get(build.element, (110, 114, 124))
    widest = max(t.max_level for t in build.talents)
    label_x = x + (widest - 1) * step + size + 18
    for t in build.talents:
        cy = y + size / 2
        for k in range(t.max_level - 1):
            a, b = x + k * step + size, x + (k + 1) * step
            joined = k + 1 < t.level
            d.line([(a, cy), (b, cy)], fill=(255, 200, 0) if joined else (70, 73, 84), width=3)
        for k in range(t.max_level):
            nx = x + k * step
            _node(canvas, images, t, nx, y, size, k < t.level, tint, t.kind == "base", tile)
            if t.kind == "base":
                letter = GREEK[k]
                f = font(15, "bold")
                d.text((nx + size - 4, y + size - 14), letter, font=f, fill=text if k < t.level else dim)
        f = font(17, "semibold")
        room = x + width - label_x
        name = t.name
        if t.kind == "attribute" and t.value and t.unlocked:
            name = f"{t.name} {t.value}"
        d.text((label_x, y + 2), shorten(d, name, f, room), font=f, fill=text if t.unlocked else dim)
        kind = {"attribute": "Friendship", "combat": "Combat Talent", "base": "Base Skill"}[t.kind]
        d.text((label_x, y + 22), f"{kind}  ·  {t.level}/{t.max_level}", font=font(13), fill=dim)
        y += row
    return y - row + size
