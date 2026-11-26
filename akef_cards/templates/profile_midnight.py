import math

from PIL import Image, ImageChops, ImageDraw

from akef_cards.draw import brand, canvas_draw, class_badge, cover, fit, font, number, shorten, stars
from akef.enka import Player, Rostered

from akef_cards.framing import GRIDS, pages as split_pages
from akef_cards.templates.profile import BOARD_H, BOARD_W, WIDTH, _round_mask, board_size, medal_board, portrait_for
from akef_cards.templates.showcase import ELEMENT, RARITY, SIGNAL

NIGHT = (14, 15, 19)
PANEL = (26, 28, 34)
LINE = (48, 51, 60)
WHITE = (238, 238, 242)
DIM = (140, 143, 152)
PAD, GAP = 64, 22
HEAD_H = 380


def _gradient(w, h, start, end, power=1.0, vertical=True):
    strip = Image.new("L", (1, h) if vertical else (w, 1))
    n = h if vertical else w
    for i in range(n):
        t = max(0.0, min(1.0, (i / n - start) / max(end - start, 1e-6))) ** power
        strip.putpixel((0, i) if vertical else (i, 0), int(255 * t))
    return strip.resize((w, h))


def _header(canvas, d, player: Player, images, w, hide_uid):
    h = HEAD_H
    band = Image.new("RGBA", (w, h), PANEL)
    art = images.get(player.namecard)
    if art is None:
        bd = ImageDraw.Draw(band)
        for i in range(int(w * 0.4), w + h, 34):
            bd.line([(i - h, h), (i, 0)], fill=(34, 36, 43), width=12)
        bd.polygon([(w - 300, 0), (w - 180, 0), (w - 420, h), (w - 540, h)], fill=(120, 96, 0))
    else:
        art = cover(art, w, h, 0.5)
        art.putalpha(ImageChops.multiply(art.getchannel("A"), _gradient(w, h, 0.2, 0.75, 1.3, vertical=False)))
        band.alpha_composite(art)
    shade = Image.new("RGBA", (w, h), NIGHT)
    shade.putalpha(_gradient(w, h, 0.45, 1.0, 1.0).point(lambda v: v * 0.9))
    band.alpha_composite(shade)
    canvas.alpha_composite(band)

    av = 150
    ax, ay = PAD, 70
    canvas.alpha_composite(_rounded(images.get(player.avatar), av) if images.get(player.avatar) else
                           Image.new("RGBA", (av, av), LINE), (ax, ay))
    d.rounded_rectangle((ax - 3, ay - 3, ax + av + 3, ay + av + 3), 30, outline=SIGNAL, width=3)

    tx = ax + av + 40
    bx = w - PAD
    if player.medals:
        name_end = tx + max(d.textlength(player.name, font=number(88)), 420) + 60
        unit = min((w - PAD - name_end) / BOARD_W, (h - 120) / BOARD_H, 70)
        bw, bh = board_size(unit)
        bx = w - PAD - bw
        medal_board(canvas, player.medals, images, bx, 50, unit)
    d.text((tx, ay - 6), "OPERATOR PROFILE", font=font(20, "bold"), fill=SIGNAL)
    nf = number(88)
    while d.textlength(player.name, font=nf) > bx - 40 - tx and nf.size > 44:
        nf = number(nf.size - 4)
    d.text((tx - 4, ay + 18), player.name, font=nf, fill=WHITE)
    uid = f"UID {player.uid}"
    d.text((tx, ay + 30 + nf.size), "   /   ".join(p for p in (uid, player.region, f"Day {player.days:,}" if player.days else "") if p),
           font=font(24), fill=DIM)
    line = f"“{player.signature}”" if player.signature else player.mission
    if line:
        d.text((PAD, ay + av + 34), shorten(d, line, font(26), bx - 40 - PAD), font=font(26), fill=WHITE)

    stats = [("AUTHORITY", player.level), ("WORLD", player.world_level), ("OPERATORS", player.operators_owned),
             ("WEAPONS", player.weapons_owned), ("FILES", player.files)] + [(n.upper(), lv) for n, lv in player.regions]
    y = h - 16 - 70
    x = PAD
    for label, value in stats:
        text = f"{value:,}"
        cw = max(d.textlength(text, font=number(40)), d.textlength(label, font=font(16, "bold"))) + 40
        if x + cw > w - PAD:
            break
        d.text((x, y), label, font=font(16, "bold"), fill=DIM)
        d.text((x - 1, y + 20), text, font=number(40), fill=SIGNAL if label == "AUTHORITY" else WHITE)
        x += cw
        d.line([(x - 20, y + 6), (x - 20, y + 60)], fill=LINE, width=2)
    return h + 34


def _rounded(img, size, radius=28):
    img = cover(img, size, size, 0.2)
    img.putalpha(_round_mask((size, size), radius))
    return img


def _tile(canvas, d, op: Rostered, images, x, y, tw, th):
    tint = ELEMENT.get(op.element, DIM)
    card = Image.new("RGBA", (tw, th), tuple(int(PANEL[i] + (tint[i] - PANEL[i]) * 0.35) for i in range(3)) + (255,))
    art = portrait_for(op, images, tw, th, 0.08)
    if art is not None:
        card.alpha_composite(art)
    shade = Image.new("RGBA", (tw, th), NIGHT)
    shade.putalpha(_gradient(tw, th, 0.5, 1.0, 1.2).point(lambda v: v * 0.95))
    card.alpha_composite(shade)
    card.putalpha(_round_mask((tw, th), 22))
    canvas.alpha_composite(card, (x, y))

    rare = RARITY.get(op.rarity, DIM)
    d.rounded_rectangle((x, y, x + tw, y + th), 22, outline=LINE, width=2)
    d.rounded_rectangle((x + 20, y + th - 10, x + tw - 20, y + th - 6), 2, fill=rare)

    glyph = images.get(op.element_icon)
    d.ellipse((x + 16, y + 16, x + 58, y + 58), fill=tint)
    if glyph is not None:
        g = fit(glyph, 28, 28)
        canvas.alpha_composite(g, (x + 37 - g.width // 2, y + 37 - g.height // 2))
    badge = class_badge(op.profession, 42, (12, 13, 16), WHITE)
    if badge is not None:
        canvas.alpha_composite(badge, (x + 66, y + 16))
    for i in range(5):
        px = x + tw - 26 - (4 - i) * 16
        d.rounded_rectangle((px, y + 30, px + 10, y + 42), 3, fill=SIGNAL if i < op.potential else (78, 80, 90))

    bottom = y + th - 26
    nf = font(32, "bold")
    room = tw - 40
    lv = str(op.level)
    d.text((x + 20, bottom - 112), "LV", font=font(16, "bold"), fill=SIGNAL)
    d.text((x + 18, bottom - 96), lv, font=number(54), fill=WHITE)
    tag = f"E{op.promotion}" if op.promotion is not None else ""
    if tag:
        tx = x + 30 + d.textlength(lv, font=number(54))
        d.rounded_rectangle((tx, bottom - 72, tx + 44, bottom - 46), 8, fill=SIGNAL)
        d.text((tx + 22 - d.textlength(tag, font=font(18, "bold")) / 2, bottom - 70), tag, font=font(18, "bold"), fill=NIGHT)
    d.text((x + 20, bottom - 36), shorten(d, op.name, nf, room), font=nf, fill=WHITE)
    stars(d, x + 22, bottom - 132, op.rarity, 16, rare, gap=2)



def render(player: Player, images, *, grid: str = "4x2", page: int = 0, hide_uid: bool = False) -> Image.Image:
    pages = split_pages(player, grid)
    cols, _ = GRIDS[grid]
    chunk = pages[page]
    w = WIDTH[grid]
    tw = (w - PAD * 2 - GAP * (cols - 1)) // cols
    th = int(tw * 1.3)
    rows = max(1, math.ceil(len(chunk) / cols))

    head = HEAD_H + 34
    h = head + 50 + rows * th + (rows - 1) * GAP + 90

    canvas = Image.new("RGBA", (w, h), NIGHT)
    d = canvas_draw(canvas)
    y = _header(canvas, d, player, images, w, hide_uid)
    d.text((PAD, y), "ROSTER", font=font(18, "bold"), fill=DIM)
    if len(pages) > 1:
        text = f"{page + 1:02d} / {len(pages):02d}"
        d.text((w - PAD - d.textlength(text, font=number(22)), y - 4), text, font=number(22), fill=SIGNAL)
    y += 40
    for i, op in enumerate(chunk):
        r, c = divmod(i, cols)
        _tile(canvas, d, op, images, PAD + c * (tw + GAP), y + r * (th + GAP), tw, th)
    source = "enka.network" if player.source == "enka" else "skport"
    d.text((PAD, h - 54), f"via {source}", font=font(19), fill=DIM)
    brand(d, w - PAD, h - 54, DIM, 19)
    return canvas.convert("RGB")
