from PIL import Image, ImageChops, ImageDraw

from akef_cards.i18n import short_date
from akef_cards.draw import canvas_draw, cover, fit, font, number, shorten
from akef_cards.gacha import Hit, PullHistory, Track
from akef_cards.templates.profile_poster import INK, PAPER, SOFT_INK
from akef_cards.templates.pulls_board import LUCKY, UNLUCKY, _luck_color, period
from akef_cards.templates.showcase import ELEMENT, SIGNAL

W = 1600
SIDE = 500
PAD = 48
ROW = 92
SHOWN = 8
STRIPE = (246, 192, 0)
DARK_STRIPE = (226, 172, 0)
GREY = (120, 116, 100)


def _slanted(size, cut):
    w, h = size
    mask = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (w * 2, 0), (w * 2 - cut * 2, h * 2), (0, h * 2)], fill=255)
    return mask.resize(size, Image.LANCZOS)


def _chunks(d, x, y, w, h, share, cells, on, off, gap=5):
    step = (w + gap) / cells
    lit = round(min(1.0, share) * cells)
    for i in range(cells):
        cx = x + i * step
        d.polygon([(cx + 6, y), (cx + step - gap, y), (cx + step - gap - 6, y + h), (cx, y + h)],
                  fill=on if i < lit else off)


def _side(canvas, d, h: PullHistory, images, height, hide_uid):
    panel = Image.new("RGBA", (SIDE, height), SIGNAL)
    pd = ImageDraw.Draw(panel)
    for i in range(-height, SIDE, 90):
        pd.line([(i, height), (i + height, 0)], fill=STRIPE, width=28)

    lead = next((x for x in h.operators if x.portrait), None)
    art = images.get(lead.portrait) if lead else None
    top = 292 + len(h.tracks[:3]) * 150 - 10
    if art is not None and height - top > 120:
        aw = SIDE
        art = cover(art, aw, height - top, 0.0)
        ah = art.height
        fade = Image.new("L", (1, ah))
        for y in range(ah):
            fade.putpixel((0, y), int(255 * min(1.0, y / (ah * 0.28)) ** 1.4))
        art.putalpha(ImageChops.multiply(art.getchannel("A"), fade.resize((aw, ah))))
        panel.alpha_composite(art, (0, top))
    canvas.alpha_composite(panel)

    av = 112
    d.rectangle((PAD - 6, 50, PAD + av + 6, 62 + av), fill=INK)
    avatar = images.get(h.avatar)
    if avatar is not None:
        canvas.alpha_composite(cover(avatar, av, av, 0.2), (PAD, 56))
    tx = PAD + av + 24
    nf = number(50)
    while d.textlength(h.name, font=nf) > SIDE - PAD - tx and nf.size > 28:
        nf = number(nf.size - 4)
    d.text((tx - 2, 56), h.name, font=nf, fill=INK)
    uid = "UID HIDDEN" if hide_uid else f"UID {h.uid}"
    d.text((tx, 66 + nf.size), uid, font=font(19, "bold"), fill=INK)
    d.text((tx, 92 + nf.size), f"{h.region.upper()}  ·  AUTHORITY {h.level}", font=font(16, "semibold"), fill=SOFT_INK)

    y = 212
    d.rectangle((PAD, y, SIDE - PAD, y + 6), fill=INK)
    d.text((PAD, y + 22), "PITY", font=font(30, "bold"), fill=INK)
    note = "PULLS SINCE LAST 6-STAR"
    d.text((SIDE - PAD - d.textlength(note, font=font(14, "bold")), y + 34), note, font=font(14, "bold"), fill=SOFT_INK)
    y += 80
    for t in h.tracks[:3]:
        y = _pity(d, t, y)

    if lead and art is not None and height - top > 120:
        shade = Image.new("RGBA", (SIDE, 150))
        sd = ImageDraw.Draw(shade)
        for y in range(150):
            sd.line([(0, y), (SIDE, y)], fill=SIGNAL + (int(235 * (y / 150) ** 1.2),))
        canvas.alpha_composite(shade, (0, height - 150))
        cap = f"LATEST 6-STAR  ·  PULL {lead.pity}"
        cw = d.textlength(cap, font=font(15, "bold")) + 28
        d.rectangle((PAD, height - 112, PAD + cw, height - 84), fill=INK)
        d.text((PAD + 14, height - 108), cap, font=font(15, "bold"), fill=SIGNAL)
        d.text((PAD, height - 76), lead.name.upper(), font=font(34, "bold"), fill=INK)


def _pity(d, t: Track, y):
    label = {"Limited operators": "LIMITED", "Standard": "STANDARD"}.get(t.name, "WEAPON")
    d.text((PAD, y), label, font=font(20, "bold"), fill=INK)
    d.text((PAD + 4 + d.textlength(label, font=font(20, "bold")) + 10, y + 4),
           shorten(d, t.banner.upper(), font(14, "semibold"), SIDE - PAD * 2 - 140), font=font(14, "semibold"),
           fill=SOFT_INK)
    value = str(t.since)
    d.text((PAD - 4, y + 22), value, font=number(76), fill=INK)
    vx = PAD + 6 + d.textlength(value, font=number(76))
    d.text((vx, y + 54), f"/ {t.hard}", font=font(24, "bold"), fill=SOFT_INK)
    left = max(0, t.hard - t.since)
    tag = f"{left} TO GO"
    tw = d.textlength(tag, font=font(16, "bold")) + 24
    d.rectangle((SIDE - PAD - tw, y + 56, SIDE - PAD, y + 84), fill=INK)
    d.text((SIDE - PAD - tw + 12, y + 60), tag, font=font(16, "bold"), fill=SIGNAL)
    share = t.since / t.hard if t.hard else 0
    _chunks(d, PAD, y + 106, SIDE - PAD * 2, 16, share, 16, UNLUCKY if share >= 0.8 else INK, DARK_STRIPE)
    return y + 150


def _stats(d, h: PullHistory, x, y, w):
    tiles = [("PULLS", f"{h.total:,}", f"{h.free} free" if h.free else "operators"),
             ("6-STARS", str(len(h.operators)), f"{h.fives} five-stars"),
             ("PER 6-STAR", f"{h.average:.1f}" if h.operators else "-", "free left out"),
             ("WEAPON PULLS", f"{h.weapon_total:,}", f"{len(h.weapons)} six-stars")]
    tw = (w - 3 * 16) // 4
    for i, (label, value, sub) in enumerate(tiles):
        tx = x + i * (tw + 16)
        d.rectangle((tx, y, tx + tw, y + 118), fill=INK)
        d.rectangle((tx, y, tx + tw, y + 5), fill=SIGNAL)
        d.text((tx + 18, y + 18), label, font=font(15, "bold"), fill=(170, 170, 176))
        d.text((tx + 16, y + 38), value, font=number(46), fill=SIGNAL if label == "6-STARS" else (245, 245, 245))
        d.text((tx + 18, y + 90), sub.upper(), font=font(13, "bold"), fill=(120, 120, 128))
    return y + 118


def _row(canvas, d, hit: Hit, images, x, y, w):
    color = _luck_color(hit)
    h = ROW - 12
    body = Image.new("RGBA", (w, h), INK + (255,))
    body.putalpha(_slanted((w, h), 26))
    canvas.alpha_composite(body, (x, y))

    size = h - 16
    tint = ELEMENT.get(hit.element, (58, 58, 64))
    d.rectangle((x + 8, y + 8, x + 8 + size, y + 8 + size), fill=tuple(int(c * 0.55) for c in tint))
    icon = images.get(hit.icon)
    if icon is not None:
        art = cover(icon, size, size, 0.1) if hit.element else fit(icon, size - 8, size - 8)
        canvas.alpha_composite(art, (x + 8 + (size - art.width) // 2, y + 8 + (size - art.height) // 2))
    d.rectangle((x + 8, y + 8 + size - 4, x + 8 + size, y + 8 + size), fill=color)

    tx = x + size + 26
    num = str(hit.pity)
    nw = d.textlength(num, font=number(40))
    room = w - (tx - x) - nw - 60
    d.text((tx, y + 10), shorten(d, hit.name.upper(), font(22, "bold"), room), font=font(22, "bold"), fill=(245, 245, 245))
    when = short_date(hit.when).upper()
    d.text((tx, y + 40), shorten(d, f"{when}  ·  {hit.banner.upper()}", font(13, "bold"), room), font=font(13, "bold"),
           fill=(150, 150, 156))
    bar_w = room
    d.rectangle((tx, y + 62, tx + bar_w, y + 66), fill=(52, 52, 58))
    d.rectangle((tx, y + 62, tx + int(bar_w * min(1.0, hit.luck)), y + 66), fill=color)
    nx = x + w - 44 - nw
    d.text((nx, y + 12), num, font=number(40), fill=color)
    d.text((nx + nw / 2 - d.textlength("PULL", font=font(12, "bold")) / 2, y + 56), "PULL", font=font(12, "bold"),
           fill=(150, 150, 156))


def _column(canvas, d, title, hits, images, x, y, w):
    d.text((x, y), title, font=font(26, "bold"), fill=INK)
    count = str(len(hits))
    cx = x + d.textlength(title, font=font(26, "bold")) + 14
    d.rectangle((cx, y + 4, cx + d.textlength(count, font=font(18, "bold")) + 18, y + 32), fill=SIGNAL)
    d.text((cx + 9, y + 6), count, font=font(18, "bold"), fill=INK)
    y += 48
    if not hits:
        d.text((x, y), "NONE IN THIS PERIOD", font=font(18, "bold"), fill=GREY)
    for hit in hits[:SHOWN]:
        _row(canvas, d, hit, images, x, y, w)
        y += ROW
    if len(hits) > SHOWN:
        d.text((x, y + 2), f"+{len(hits) - SHOWN} OLDER", font=font(16, "bold"), fill=GREY)


def render(h: PullHistory, images, *, hide_uid: bool = False) -> Image.Image:
    rows = min(SHOWN, max(len(h.operators), len(h.weapons), 1))
    more = 30 if max(len(h.operators), len(h.weapons)) > SHOWN else 0
    list_h = 300 + 48 + rows * ROW + more + 90
    side_h = 292 + len(h.tracks[:3]) * 150 + 420
    height = max(list_h, side_h)
    canvas = Image.new("RGBA", (W, height), PAPER)
    d = canvas_draw(canvas)
    _side(canvas, d, h, images, height, hide_uid)

    x0 = SIDE + PAD
    inner = W - x0 - PAD
    d.text((x0, 40), "PULL HISTORY", font=font(64, "bold"), fill=INK)
    span = period(h).upper()
    sw = d.textlength(span, font=font(16, "bold")) + 28
    d.rectangle((x0, 118, x0 + sw, 146), fill=INK)
    d.text((x0 + 14, 122), span, font=font(16, "bold"), fill=SIGNAL)
    d.rectangle((W - PAD - 120, 58, W - PAD, 66), fill=INK)
    d.rectangle((W - PAD - 120, 76, W - PAD - 50, 84), fill=SIGNAL)
    _stats(d, h, x0, 168, inner)

    cw = (inner - 28) // 2
    _column(canvas, d, "OPERATORS", h.operators, images, x0, 316, cw)
    _column(canvas, d, "WEAPONS", h.weapons, images, x0 + cw + 28, 316, cw)

    lx = x0
    for text, color in (("LUCKY", LUCKY), ("NORMAL", SIGNAL), ("NEAR PITY", UNLUCKY)):
        d.rectangle((lx, height - 46, lx + 16, height - 30), fill=color)
        d.text((lx + 24, height - 48), text, font=font(15, "bold"), fill=INK)
        lx += 40 + d.textlength(text, font=font(15, "bold")) + 16
    d.text((W - PAD - d.textlength("AKEF", font=font(18, "bold")), height - 48), "AKEF", font=font(18, "bold"), fill=INK)
    return canvas.convert("RGB")
