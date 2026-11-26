from PIL import Image, ImageDraw

from akef_cards.contract import ContractDetail, Run
from akef_cards.draw import brand, canvas_draw, cover, fit, font, number, rarity_mark
from akef_cards.i18n import long_date
from akef_cards.live import until
from akef_cards.monument import clock
from akef_cards.templates.flex import member
from akef_cards.templates.live_parts import meter_text, round_avatar
from akef_cards.templates.profile import _round_mask
from akef_cards.templates.showcase import BG, CARD, HAIR, MUTED, SIGNAL, SLATE, TEXT

W = 2000
PAD = 56
SHOWN = 4

LIGHT = {"bg": BG, "card": CARD, "line": HAIR, "text": TEXT, "dim": MUTED, "tile": SLATE}
DARK = {"bg": (15, 16, 20), "card": (26, 28, 34), "line": (44, 47, 56), "text": (240, 241, 245),
        "dim": (140, 144, 154), "tile": (40, 43, 52)}


def best_runs(cd: ContractDetail, count=SHOWN) -> list[Run]:
    return sorted(cd.runs, key=lambda r: (-r.score, r.seconds))[:count]


def _header(canvas, d, cd: ContractDetail, images, p):
    av = 104
    avatar = images.get(cd.avatar)
    d.ellipse((PAD - 5, 41, PAD + av + 5, 41 + av + 10), fill=SIGNAL)
    if avatar is not None:
        canvas.alpha_composite(round_avatar(avatar, av), (PAD, 46))
    tx = PAD + av + 30
    d.text((tx, 44), cd.name, font=number(56), fill=p["text"])
    d.text((tx, 112), f"UID {cd.uid}  ·  {cd.region}  ·  Authority {cd.level}", font=font(24), fill=p["dim"])
    label = "CONTINGENCY CONTRACT"
    d.text((W - PAD - d.textlength(label, font=font(20, "bold")), 56), label, font=font(20, "bold"), fill=SIGNAL)


def _banner(canvas, d, cd: ContractDetail, images, x, y, w, h, p):
    art = Image.new("RGBA", (w, h), p["tile"] + (255,))
    img = images.get(cd.contract.art)
    if img is not None:
        art.alpha_composite(cover(img, w, h, 0.3))
    shade = Image.new("RGBA", (w, h))
    sd = ImageDraw.Draw(shade)
    for col in range(w):
        sd.line([(col, 0), (col, h)], fill=(8, 9, 12, int(215 * max(0.0, 1 - col / (w * 0.7)) ** 1.2)))
    art.alpha_composite(shade)
    art.putalpha(_round_mask((w, h), 28))
    canvas.alpha_composite(art, (x, y))
    c = cd.contract
    nf = number(60)
    while d.textlength(c.name, font=nf) > w * 0.6 and nf.size > 30:
        nf = number(nf.size - 4)
    d.text((x + 36, y + 32), c.name, font=nf, fill=(255, 255, 255))
    bits = []
    if c.starts and c.ends:
        bits.append(f"{long_date(c.starts)} to {long_date(c.ends)}")
    left = until(c.ends, cd.now) if c.ends else ""
    bits.append(f"ends in {left}" if left else "finished")
    d.text((x + 38, y + 44 + nf.size), "  ·  ".join(bits), font=font(22), fill=(214, 216, 224))
    stats = [("BEST RISK", str(c.best)), ("ATTEMPTS", str(c.attempts))]
    stats += [(m.label.upper(), meter_text(m)) for m in c.missions]
    sx = x + 38
    for label, value in stats:
        d.text((sx, y + h - 92), label, font=font(15, "bold"), fill=(170, 172, 180))
        vx = sx
        if label == "BEST RISK":
            canvas.alpha_composite(rarity_mark(40, SIGNAL), (int(sx - 2), y + h - 62))
            vx += 46
        d.text((vx - 2, y + h - 68), value, font=number(44), fill=SIGNAL if label == "BEST RISK" else (255, 255, 255))
        sx = max(sx + d.textlength(label, font=font(15, "bold")), vx + d.textlength(value, font=number(44))) + 52
    medal = images.get(c.medal)
    if medal is not None:
        g = fit(medal, 120, 120)
        canvas.alpha_composite(g, (x + w - 30 - g.width, y + h // 2 - g.height // 2))


def _battle(canvas, d, r: Run, rank, images, x, y, w, h, p):
    top = rank == 1
    d.rounded_rectangle((x, y, x + w, y + h), 24, fill=p["card"], outline=SIGNAL if top else p["line"],
                        width=3 if top else 2)
    rf = number(40)
    tag = f"#{rank}"
    d.text((x + 24, y + 20), tag, font=rf, fill=SIGNAL if top else p["dim"])
    score = str(r.score)
    rx = x + 44 + d.textlength(tag, font=rf)
    canvas.alpha_composite(rarity_mark(42, SIGNAL), (int(rx), y + 24))
    d.text((rx + 50, y + 16), score, font=number(48), fill=SIGNAL if top else p["text"])
    line = f"{clock(r.seconds)}  ·  wave {r.waves}"
    d.text((x + w - 24 - d.textlength(line, font=number(26)), y + 22), line, font=number(26), fill=p["text"])
    when = long_date(r.when) if r.when else ""
    note = ("cleared" if r.cleared else "failed") + (f"  ·  {when}" if when else "")
    d.text((x + w - 24 - d.textlength(note, font=font(17)), y + 56), note, font=font(17), fill=p["dim"])
    gap = 14
    tw = (w - 48 - gap * 3) // 4
    ty = y + 96
    for k in range(4):
        tx = x + 24 + k * (tw + gap)
        if k < len(r.team):
            member(canvas, r.team[k], images, tx, ty, tw, h - 120, compact=True)
        else:
            d.rounded_rectangle((tx, ty, tx + tw, ty + h - 120), 18, fill=p["tile"])


def _render(cd: ContractDetail, images, p) -> Image.Image:
    runs = best_runs(cd)
    cols = 2
    bw = (W - PAD * 2 - 30) // cols
    bh = 470
    rows = max(1, -(-len(runs) // cols))
    top = 196 + 300 + 36
    h = top + 46 + rows * (bh + 30) + 70
    canvas = Image.new("RGBA", (W, h), p["bg"] + (255,))
    d = canvas_draw(canvas)
    _header(canvas, d, cd, images, p)
    _banner(canvas, d, cd, images, PAD, 196, W - PAD * 2, 300, p)
    d.text((PAD, top), "BEST BATTLES", font=font(18, "bold"), fill=p["dim"])
    note = f"top {len(runs)} of {len(cd.runs)} by risk" if runs else "no runs yet"
    d.text((PAD + d.textlength("BEST BATTLES", font=font(18, "bold")) + 14, top + 1), note, font=font(17), fill=p["dim"])
    y = top + 46
    for i, r in enumerate(runs):
        _battle(canvas, d, r, i + 1, images, PAD + (i % cols) * (bw + 30), y + (i // cols) * (bh + 30), bw, bh, p)
    d.text((PAD, h - 44), "via skport", font=font(18), fill=p["dim"])
    brand(d, W - PAD, h - 44, p["dim"])
    return canvas.convert("RGB")


def render(cd, images, *, hide_uid=False):
    return _render(cd, images, LIGHT)


def render_dark(cd, images, *, hide_uid=False):
    return _render(cd, images, DARK)


TEMPLATES = {1: render, 2: render_dark}
