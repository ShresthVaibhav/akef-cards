from dataclasses import dataclass

from PIL import Image

from akef_cards.draw import brand, canvas_draw, cover, font, number, shorten
from akef_cards.factory import Factory, Region, money
from akef_cards.templates.live_parts import bar, ring, round_avatar
from akef_cards.templates.profile import _round_mask
from akef_cards.templates.showcase import BG, CARD, HAIR, MUTED, SIGNAL, SLATE, TEXT

W = 1600
PAD = 56
GAP = 24


@dataclass
class Theme:
    bg: tuple
    card: tuple
    line: tuple
    text: tuple
    muted: tuple
    track: tuple
    chip: tuple
    chip_text: tuple


LIGHT = Theme(BG, CARD, HAIR, TEXT, MUTED, (232, 230, 223), SLATE, SIGNAL)
DARK = Theme((14, 15, 19), (26, 28, 34), (48, 51, 60), (238, 238, 242), (140, 143, 152), (44, 46, 54), SIGNAL, (14, 15, 19))


def _header(canvas, d, f: Factory, images, t: Theme, hide_uid):
    av = 104
    avatar = images.get(f.avatar)
    d.ellipse((PAD - 5, 41, PAD + av + 5, 51 + av), fill=SIGNAL)
    if avatar is not None:
        canvas.alpha_composite(round_avatar(avatar, av), (PAD, 46))
    tx = PAD + av + 30
    d.text((tx, 44), f.name, font=number(56), fill=t.text)
    uid = f"UID {f.uid}"
    d.text((tx, 112), f"{uid}  ·  {f.server}  ·  Authority {f.level}", font=font(24), fill=t.muted)

    posts = [p for r in f.regions for p in r.posts]
    found = sum(a.found for r in f.regions for a in r.areas)
    total = sum(a.total for r in f.regions for a in r.areas)
    stats = (("EXPLORED", f"{found / total:.0%}" if total else "-"),
             ("SETTLEMENTS MAXED", f"{sum(p.maxed for p in posts)}/{len(posts)}"))
    x = W - PAD
    for label, value in stats:
        w = max(d.textlength(value, font=number(40)), d.textlength(label, font=font(16, "bold")))
        x -= w
        d.text((x, 96), label, font=font(16, "bold"), fill=t.muted)
        d.text((x - 1, 114), value, font=number(40), fill=t.text)
        x -= 44
    d.text((W - PAD - d.textlength("FACTORY", font=font(20, "bold")), 56), "FACTORY", font=font(20, "bold"), fill=SIGNAL)


def _region(canvas, d, r: Region, images, t: Theme, x, y, w):
    d.rounded_rectangle((x, y, x + w, y + 168), 24, fill=t.card, outline=t.line, width=2)
    d.text((x + 28, y + 22), r.name, font=number(42), fill=t.text)
    lv = f"Lv {r.level}"
    lx = x + 40 + d.textlength(r.name, font=number(42))
    d.rounded_rectangle((lx, y + 34, lx + d.textlength(lv, font=font(20, "bold")) + 26, y + 66), 16, fill=t.chip)
    d.text((lx + 13, y + 37), lv, font=font(20, "bold"), fill=t.chip_text)
    d.text((x + 28, y + 88), "FUNDS", font=font(16, "bold"), fill=t.muted)
    text = f"{money(r.stock)} / {money(r.stock_max)}"
    d.text((x + w - 170 - d.textlength(text, font=number(24)), y + 82), text, font=number(24), fill=t.text)
    bar(d, x + 28, y + 118, w - 200 - 28, 14, r.stock_share, SIGNAL, t.track)

    size = 118
    gx, gy = x + w - size - 26, y + 26
    canvas.alpha_composite(ring(size, r.explored, SIGNAL, t.track, 12), (gx, gy))
    pct = f"{r.explored:.0%}"
    d.text((gx + size / 2 - d.textlength(pct, font=number(30)) / 2, gy + 30), pct, font=number(30), fill=t.text)
    ef = font(15)
    while d.textlength("explored", font=ef) > size - 36 and ef.size > 10:
        ef = font(ef.size - 1)
    d.text((gx + size / 2 - d.textlength("explored", font=ef) / 2, gy + 68), "explored", font=ef, fill=t.muted)
    y += 168 + 16

    for p in r.posts:
        d.rounded_rectangle((x, y, x + w, y + 104), 20, fill=t.card, outline=t.line, width=2)
        officer = images.get(p.officer)
        if officer is not None:
            face = cover(officer, 76, 76, 0.1)
            face.putalpha(_round_mask((76, 76), 16))
            canvas.alpha_composite(face, (x + 14, y + 14))
        else:
            d.rounded_rectangle((x + 14, y + 14, x + 90, y + 90), 16, fill=t.track)
        ix = x + 108
        tag = "MAX" if p.maxed else f"Lv {p.level}"
        tw = d.textlength(tag, font=font(16, "bold")) + 22
        d.text((ix, y + 14), shorten(d, p.name, font(24, "semibold"), w - (ix - x) - tw - 40), font=font(24, "semibold"),
               fill=t.text)
        d.rounded_rectangle((x + w - 20 - tw, y + 16, x + w - 20, y + 42), 13, fill=t.chip if p.maxed else t.track)
        d.text((x + w - 9 - tw, y + 19), tag, font=font(16, "bold"), fill=t.chip_text if p.maxed else t.text)
        full = p.stock_max and p.stock >= p.stock_max
        d.text((ix, y + 52), "STOCK", font=font(14, "bold"), fill=SIGNAL if full else t.muted)
        stock = f"{money(p.stock)} / {money(p.stock_max)}" + ("  full" if full else "")
        d.text((x + w - 20 - d.textlength(stock, font=font(18)), y + 48), stock, font=font(18), fill=t.text)
        bar(d, ix, y + 76, w - (ix - x) - 20, 10, p.stock_share, SIGNAL, t.track)
        y += 104 + 12

    y += 10
    d.text((x + 4, y), "EXPLORATION", font=font(16, "bold"), fill=t.muted)
    y += 30
    for a in r.areas:
        name = shorten(d, a.name, font(19), w * 0.42)
        d.text((x + 4, y), name, font=font(19), fill=t.text if a.share < 1 else t.muted)
        bx = x + int(w * 0.46)
        bar(d, bx, y + 8, w - (bx - x) - 110, 8, a.share, SIGNAL if a.share < 1 else t.muted, t.track)
        count = f"{a.found}/{a.total}"
        d.text((x + w - d.textlength(count, font=font(18)), y), count, font=font(18), fill=t.text if a.share < 1 else t.muted)
        y += 30
    return y


def _cabins(canvas, d, f: Factory, images, t: Theme, y):
    if not f.cabins:
        return y
    d.text((PAD, y), "DIJIANG CABINS", font=font(16, "bold"), fill=t.muted)
    y += 30
    cols = min(6, len(f.cabins))
    cw = (W - PAD * 2 - 16 * (cols - 1)) // cols
    for i, c in enumerate(f.cabins[:cols]):
        x = PAD + i * (cw + 16)
        d.rounded_rectangle((x, y, x + cw, y + 150), 20, fill=t.card, outline=t.line, width=2)
        d.text((x + 18, y + 14), shorten(d, c.name, font(20, "semibold"), cw - 36), font=font(20, "semibold"), fill=t.text)
        d.text((x + 18, y + 40), f"Lv {c.level}", font=number(18), fill=SIGNAL)
        for k, url in enumerate(c.crew[:3]):
            img = images.get(url)
            ax = x + 18 + k * 62
            if img is not None:
                canvas.alpha_composite(round_avatar(img, 54), (ax, y + 76))
            else:
                d.ellipse((ax, y + 76, ax + 54, y + 130), fill=t.track)
        if not c.crew:
            d.text((x + 18, y + 92), "empty", font=font(18), fill=t.muted)
    return y + 150


def _height(f: Factory) -> int:
    longest = max((len(r.areas) for r in f.regions), default=0)
    posts = max((len(r.posts) for r in f.regions), default=0)
    body = 184 + posts * 116 + 40 + longest * 30
    return 200 + body + (216 if f.cabins else 0) + 80


def render(f: Factory, images, *, theme: Theme = LIGHT, hide_uid: bool = False) -> Image.Image:
    h = _height(f)
    canvas = Image.new("RGBA", (W, h), theme.bg)
    d = canvas_draw(canvas)
    _header(canvas, d, f, images, theme, hide_uid)
    cols = max(1, len(f.regions))
    cw = (W - PAD * 2 - GAP * (cols - 1)) // cols
    bottom = 200
    for i, r in enumerate(f.regions):
        bottom = max(bottom, _region(canvas, d, r, images, theme, PAD + i * (cw + GAP), 200, cw))
    _cabins(canvas, d, f, images, theme, bottom + 36)
    d.text((PAD, h - 44), "via skport", font=font(18), fill=theme.muted)
    brand(d, W - PAD, h - 44, theme.muted)
    return canvas.convert("RGB")


def render_dark(f: Factory, images, *, hide_uid: bool = False) -> Image.Image:
    return render(f, images, theme=DARK, hide_uid=hide_uid)
