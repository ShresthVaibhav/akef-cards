import math

from PIL import Image, ImageChops, ImageDraw

from akef_cards.draw import brand, canvas_draw, class_badge, cover, fit, font, number, shorten, stars
from akef.enka import Player, Rostered

from akef_cards.framing import GRIDS, pages as split_pages, tile_crop
from akef_cards.templates.showcase import BG, CARD, ELEMENT, HAIR, MUTED, RARITY, SIGNAL, SLATE, TEXT, _label

WIDTH = {"4x2": 2000, "3x3": 1560}
PAD = 70
GAP = 28


def _round_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    return mask


def _circle(img, size):
    img = cover(img, size, size, 0.2)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    img.putalpha(mask.resize((size, size), Image.LANCZOS))
    return img


def _backdrop(player: Player, images, w, h):
    panel = Image.new("RGBA", (w, h), CARD)
    namecard = images.get(player.namecard)
    if namecard is not None:
        panel.alpha_composite(cover(namecard, w, h, 0.5))
    else:
        pd = ImageDraw.Draw(panel)
        for i in range(int(w * 0.45), w + h, 34):
            pd.line([(i - h, h), (i, 0)], fill=(234, 232, 225), width=12)
        pd.polygon([(w - 560, 0), (w - 500, 0), (w - 700, h), (w - 760, h)], fill=(250, 214, 80))
    wash = Image.new("L", (w, 1))
    for x in range(w):
        wash.putpixel((x, 0), int(250 - 140 * max(0.0, (x / w - 0.25) / 0.75) ** 1.4))
    veil = Image.new("RGBA", (w, h), BG)
    veil.putalpha(wash.resize((w, h)))
    panel.alpha_composite(veil)
    panel.putalpha(_round_mask((w, h), 30))
    return panel


def _chip(d, x, y, label, value):
    lf, vf = font(19, "semibold"), number(26)
    w = d.textlength(label, font=lf) + d.textlength(value, font=vf) + 44
    d.rounded_rectangle((x, y, x + w, y + 46), 23, fill=SLATE)
    d.text((x + 18, y + 13), label, font=lf, fill=(160, 162, 170))
    d.text((x + 26 + d.textlength(label, font=lf), y + 7), value, font=vf, fill=SIGNAL if label == "Authority" else BG)
    return x + w + 12


def _header(canvas, d, player: Player, images, w, hide_uid):
    x0, y0 = PAD, 60
    inner = w - PAD * 2
    left_w = (760 if w >= 1800 else 600) if player.medals else inner - 40
    chips = [("Authority", player.level), ("World", player.world_level)]
    if player.days:
        chips.append(("Day", player.days))
    chips += [("Operators", player.operators_owned), ("Weapons", player.weapons_owned), ("Files", player.files)]
    chips += list(player.regions)
    placed, cx, row = [], x0 + 48, 0
    for label, value in chips:
        text = f"{value:,}"
        width = d.textlength(label, font=font(19, "semibold")) + d.textlength(text, font=number(26)) + 44
        if cx + width > x0 + left_w and cx > x0 + 48:
            cx, row = x0 + 48, row + 1
        placed.append((cx, row, label, text))
        cx += width + 12
    chip_y = y0 + 48 + 176 + 36
    bottom = chip_y + row * 58 + 46 + 40
    canvas.alpha_composite(_backdrop(player, images, inner, bottom - y0), (x0, y0))

    av = 176
    ax, ay = x0 + 48, y0 + 48
    d.ellipse((ax - 7, ay - 7, ax + av + 7, ay + av + 7), fill=SIGNAL)
    d.ellipse((ax - 2, ay - 2, ax + av + 2, ay + av + 2), fill=CARD)
    avatar = images.get(player.avatar)
    if avatar is not None:
        canvas.alpha_composite(_circle(avatar, av), (ax, ay))
    else:
        d.ellipse((ax, ay, ax + av, ay + av), fill=SLATE)

    tx = ax + av + 44
    room = left_w - (tx - x0)
    nf = number(96)
    while d.textlength(player.name, font=nf) > room and nf.size > 48:
        nf = number(nf.size - 4)
    d.text((tx - 4, y0 + 34), player.name, font=nf, fill=TEXT)
    uid = f"UID {player.uid}"
    meta = "  ·  ".join(p for p in (uid, player.region) if p)
    d.text((tx, y0 + 52 + nf.size), meta, font=font(26), fill=MUTED)
    line = f"“{player.signature}”" if player.signature else (f"Now: {player.mission}" if player.mission else "")
    if line:
        d.text((tx, y0 + 96 + nf.size), shorten(d, line, font(26), room), font=font(26), fill=TEXT)

    for cx, row, label, text in placed:
        _chip(d, cx, chip_y + row * 58, label, text)

    if player.medals:
        end = x0 + inner - 40
        unit = min((end - (x0 + left_w + 30)) / BOARD_W, (bottom - y0 - 60) / BOARD_H)
        bw, bh = board_size(unit)
        medal_board(canvas, player.medals, images, end - bw, y0 + (bottom - y0 - bh) // 2, unit, (0, 0, 0, 40))
    return bottom + 34


def _hexagon(w, h):
    return [(w / 2, 0), (w, h * 0.25), (w, h * 0.75), (w / 2, h), (0, h * 0.75), (0, h * 0.25)]


def medal_board(canvas, medals, images, x, y, unit, empty=(0, 0, 0, 150)) -> int:
    w, h, gap = int(unit * 2), int(unit * 2.31), unit * 0.2
    s = 4
    shape = Image.new("L", (w * s, h * s))
    ImageDraw.Draw(shape).polygon([(px * s, py * s) for px, py in _hexagon(w, h)], fill=255)
    shape = shape.resize((w, h), Image.LANCZOS)
    by_slot = {m.slot: m for m in medals if 1 <= m.slot <= 10}
    for slot in range(1, 11):
        row, col = (slot - 1) % 2, (slot - 1) // 2
        mx = int(x + col * (w + gap) + row * (w + gap) / 2)
        my = int(y + row * (h - unit * 0.5))
        medal = by_slot.get(slot)
        icon = images.get(medal.icon) if medal else None
        if icon is None:
            plate = Image.new("RGBA", (w, h), empty)
        else:
            plate = cover(icon, int(w * 1.2), int(h * 1.2), 0.5).crop((int(w * 0.1), int(h * 0.1), int(w * 0.1) + w, int(h * 0.1) + h))
        plate.putalpha(ImageChops.multiply(plate.getchannel("A"), shape))
        canvas.alpha_composite(plate, (mx, my))
    return int(h * 2 - unit * 0.5)


BOARD_W, BOARD_H = 2 * 5 + 0.2 * 4 + 1.1, 2.31 * 2 - 0.5


def board_size(unit) -> tuple[int, int]:
    return int(unit * BOARD_W), int(unit * BOARD_H)


def portrait_for(op: Rostered, images, w, h, focus=0.1):
    portrait = images.get(op.portrait)
    crop = tile_crop(op)
    if portrait is not None and crop:
        fx, fy, width = crop
        box_w = width * portrait.height
        box_h = box_w * h / w
        left, top = fx * portrait.width - box_w / 2, fy * portrait.height - box_h * 0.36
        portrait = portrait.crop((int(left), int(top), int(left + box_w), int(top + box_h)))
    return cover(portrait, w, h, focus) if portrait is not None else None


def _tile(canvas, d, op: Rostered, images, x, y, tw, th):
    art_h = int(tw * 0.9)
    shadow = Image.new("RGBA", (tw, th), CARD)
    shadow.putalpha(_round_mask((tw, th), 24))
    canvas.alpha_composite(shadow, (x, y))
    d.rounded_rectangle((x, y, x + tw, y + th), 24, outline=HAIR, width=2)

    tint = ELEMENT.get(op.element, MUTED)
    art = Image.new("RGBA", (tw, art_h), tuple(int(BG[i] + (tint[i] - BG[i]) * 0.28) for i in range(3)) + (255,))
    portrait = portrait_for(op, images, tw, art_h)
    if portrait is not None:
        art.alpha_composite(portrait)
    fade = Image.new("L", (1, art_h))
    for yy in range(art_h):
        fade.putpixel((0, yy), int(150 * max(0.0, (yy / art_h - 0.62) / 0.38) ** 1.6))
    shade = Image.new("RGBA", (tw, art_h), SLATE)
    shade.putalpha(fade.resize((tw, art_h)))
    art.alpha_composite(shade)
    mask = Image.new("L", (tw, art_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw - 1, art_h + 40), 24, fill=255)
    art.putalpha(mask)
    canvas.alpha_composite(art, (x, y))

    rare = RARITY.get(op.rarity, MUTED)
    d.rectangle((x, y + art_h, x + tw, y + art_h + 6), fill=rare)
    stars(d, x + 20, y + art_h - 38, op.rarity, 22, rare, gap=3)

    glyph = images.get(op.element_icon)
    d.ellipse((x + 16, y + 16, x + 62, y + 62), fill=tint)
    if glyph is not None:
        g = fit(glyph, 30, 30)
        canvas.alpha_composite(g, (x + 39 - g.width // 2, y + 39 - g.height // 2))
    badge = class_badge(op.profession, 46, SLATE)
    if badge is not None:
        canvas.alpha_composite(badge, (x + 70, y + 16))

    iy = y + art_h + 24
    nf = font(34, "semibold")
    d.text((x + 22, iy), shorten(d, op.name, nf, tw - 44), font=nf, fill=TEXT)
    lv = f"Lv {op.level}"
    d.text((x + 22, iy + 48), lv, font=number(30), fill=TEXT)
    bits = [f"E{op.promotion}"] if op.promotion is not None else []
    bits.append(f"P{op.potential}")
    d.text((x + 34 + d.textlength(lv, font=number(30)), iy + 52), "  ".join(bits), font=font(26), fill=MUTED)



def _roster(canvas, d, page: list[Rostered], images, w, y, grid, number_, total):
    cols, _ = GRIDS[grid]
    x0, inner = PAD, w - PAD * 2
    _label(d, x0, y, "Operators")
    if total > 1:
        text = f"{number_} / {total}"
        d.text((x0 + inner - d.textlength(text, font=number(24)), y - 4), text, font=number(24), fill=MUTED)
    y += 38
    tw = (inner - GAP * (cols - 1)) // cols
    th = int(tw * 0.9) + 140
    for i, op in enumerate(page):
        r, c = divmod(i, cols)
        _tile(canvas, d, op, images, x0 + c * (tw + GAP), y + r * (th + GAP), tw, th)
    rows = max(1, math.ceil(len(page) / cols))
    return y + rows * th + (rows - 1) * GAP


def height(player: Player, page: list[Rostered], grid: str) -> int:
    w = WIDTH[grid]
    probe = Image.new("RGBA", (w, 4000), BG)
    return _layout(probe, player, page, {}, grid, 1, 1, False)


def _layout(canvas, player, page, images, grid, number_, total, hide_uid):
    w = canvas.width
    d = canvas_draw(canvas)
    y = _header(canvas, d, player, images, w, hide_uid)
    y = _roster(canvas, d, page, images, w, y, grid, number_, total)
    return y + 96


def render(player: Player, images, *, grid: str = "4x2", page: int = 0, hide_uid: bool = False) -> Image.Image:
    pages = split_pages(player, grid)
    chunk = pages[page]
    w = WIDTH[grid]
    h = height(player, chunk, grid)
    canvas = Image.new("RGBA", (w, h), BG)
    _layout(canvas, player, chunk, images, grid, page + 1, len(pages), hide_uid)
    d = canvas_draw(canvas)
    source = "enka.network" if player.source == "enka" else "skport"
    d.text((PAD, h - 58), f"via {source}", font=font(20), fill=MUTED)
    brand(d, w - PAD, h - 58, MUTED, 20)
    return canvas.convert("RGB")
