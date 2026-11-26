from PIL import Image, ImageChops, ImageOps

from akef_cards.contract import Contract, Contracts
from akef_cards.draw import brand, canvas_draw, cover, fit, font, number, shorten
from akef_cards.live import until
from akef_cards.templates.live_parts import ring, round_avatar
from akef_cards.templates.profile import _round_mask
from akef_cards.templates.showcase import BG, CARD, HAIR, MUTED, SIGNAL, SLATE, TEXT

W, H = 1600, 900
PAD = 56
GAP = 24
TRACK = (232, 230, 223)
DONE = (64, 170, 96)


def medal_image(images, c: Contract):
    icon = images.get(c.medal)
    if icon is None or c.medal_level:
        return icon
    grey = ImageOps.grayscale(icon.convert("RGB")).convert("RGBA")
    grey.putalpha(icon.getchannel("A").point(lambda a: a * 45 // 100))
    return grey


def time_left(c: Contract, now) -> str:
    left = until(c.ends, now)
    if not left:
        return ""
    return "ended" if left == "now" else f"{left} left"


def _header(canvas, d, cs: Contracts, images, hide_uid):
    av = 104
    avatar = images.get(cs.avatar)
    d.ellipse((PAD - 5, 41, PAD + av + 5, 51 + av), fill=SIGNAL)
    if avatar is not None:
        canvas.alpha_composite(round_avatar(avatar, av), (PAD, 46))
    tx = PAD + av + 30
    d.text((tx, 44), cs.name, font=number(56), fill=TEXT)
    uid = f"UID {cs.uid}"
    d.text((tx, 112), f"{uid}  ·  {cs.region}  ·  Authority {cs.level}", font=font(24), fill=MUTED)
    d.text((W - PAD - d.textlength("CONTINGENCY CONTRACT", font=font(20, "bold")), 56), "CONTINGENCY CONTRACT",
           font=font(20, "bold"), fill=SIGNAL)


def _banner(canvas, d, c: Contract, images, y):
    w, h = W - PAD * 2, 230
    panel = Image.new("RGBA", (w, h), SLATE)
    art = images.get(c.art)
    if art is not None:
        panel.alpha_composite(cover(art, w, h, 0.5))
    shade = Image.new("L", (w, 1))
    for x in range(w):
        shade.putpixel((x, 0), int(225 * max(0.0, 1 - x / (w * 0.7)) ** 1.3))
    veil = Image.new("RGBA", (w, h), SLATE)
    veil.putalpha(shade.resize((w, h)))
    panel.alpha_composite(veil)
    panel.putalpha(ImageChops.multiply(panel.getchannel("A"), _round_mask((w, h), 26)))
    canvas.alpha_composite(panel, (PAD, y))
    d.text((PAD + 36, y + 40), "CURRENT CONTRACT", font=font(18, "bold"), fill=SIGNAL)
    nf = number(58)
    while d.textlength(c.name, font=nf) > w * 0.62 and nf.size > 32:
        nf = number(nf.size - 4)
    d.text((PAD + 34, y + 66), c.name, font=nf, fill=BG)
    return y + h + GAP


def render(cs: Contracts, images, *, hide_uid: bool = False) -> Image.Image:
    canvas = Image.new("RGBA", (W, H), BG)
    d = canvas_draw(canvas)
    _header(canvas, d, cs, images, hide_uid)
    c = cs.current
    if c is None:
        d.text((PAD, 240), "No Contingency Contract on this account yet", font=font(32), fill=MUTED)
        return canvas.convert("RGB")
    y = _banner(canvas, d, c, images, 200)
    left = time_left(c, cs.now)
    if left:
        tw = d.textlength(left.upper(), font=font(18, "bold")) + 32
        d.rounded_rectangle((W - PAD - 30 - tw, 240, W - PAD - 30, 276), 18, fill=SIGNAL)
        d.text((W - PAD - 30 - tw + 16, 246), left.upper(), font=font(18, "bold"), fill=SLATE)

    th = H - y - 90
    sw = 330
    d.rounded_rectangle((PAD, y, PAD + sw, y + th), 26, fill=CARD, outline=HAIR, width=2)
    d.text((PAD + 32, y + 28), "BEST SCORE", font=font(18, "bold"), fill=MUTED)
    d.text((PAD + 28, y + 50), str(c.best), font=number(150), fill=TEXT)
    d.text((PAD + 32, y + th - 60), f"{c.attempts} attempt{'s' if c.attempts != 1 else ''}", font=font(24), fill=MUTED)

    mw = 320
    mx = W - PAD - mw
    d.rounded_rectangle((mx, y, mx + mw, y + th), 26, fill=CARD, outline=HAIR, width=2)
    d.text((mx + 30, y + 28), "MEDAL", font=font(18, "bold"), fill=MUTED)
    medal = medal_image(images, c)
    if medal is not None:
        g = fit(medal, 170, 170)
        canvas.alpha_composite(g, (mx + mw // 2 - g.width // 2, y + 64))
    status = f"Lv {c.medal_level}" + (" · plated" if c.plated else "") if c.medal_level else "not earned yet"
    d.text((mx + mw / 2 - d.textlength(status, font=font(22, "semibold")) / 2, y + th - 60), status,
           font=font(22, "semibold"), fill=TEXT if c.medal_level else MUTED)

    rx = PAD + sw + GAP
    rw = mx - GAP - rx
    d.rounded_rectangle((rx, y, rx + rw, y + th), 26, fill=CARD, outline=HAIR, width=2)
    d.text((rx + 30, y + 28), "MISSIONS", font=font(18, "bold"), fill=MUTED)
    size = 150
    step = (rw - 60) / max(1, len(c.missions))
    for i, m in enumerate(c.missions):
        cx = rx + 30 + i * step + (step - size) / 2
        color = DONE if m.done else SIGNAL
        canvas.alpha_composite(ring(size, m.share, color, TRACK, 15), (int(cx), y + 70))
        value = f"{m.current}/{m.total}"
        d.text((cx + size / 2 - d.textlength(value, font=number(36)) / 2, y + 70 + size / 2 - 24), value,
               font=number(36), fill=TEXT)
        d.text((cx + size / 2 - d.textlength(m.label, font=font(19, "semibold")) / 2, y + 70 + size + 18), m.label,
               font=font(19, "semibold"), fill=TEXT)
    if cs.past:
        names = ", ".join(f"{p.name} ({p.best})" for p in cs.past[:3])
        d.text((PAD, H - 60), shorten(d, f"Past: {names}", font(18), W - PAD * 2 - 80), font=font(18), fill=MUTED)
    brand(d, W - PAD, H - 50, MUTED)
    return canvas.convert("RGB")
