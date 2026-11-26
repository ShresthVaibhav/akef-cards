from PIL import Image, ImageChops

from akef_cards.contract import Contracts
from akef_cards.draw import brand, canvas_draw, cover, fit, font, number
from akef_cards.templates.contract_board import medal_image, time_left
from akef_cards.templates.live_parts import round_avatar
from akef_cards.templates.profile_midnight import DIM, LINE, NIGHT, PANEL, WHITE, _gradient
from akef_cards.templates.showcase import SIGNAL

W, H = 1600, 900
PAD = 56
OFF = (44, 46, 54)
DONE = (120, 210, 140)


def render(cs: Contracts, images, *, hide_uid: bool = False) -> Image.Image:
    canvas = Image.new("RGBA", (W, H), NIGHT)
    c = cs.current
    art = images.get(c.art) if c else None
    if art is not None:
        band = cover(art, W, 420, 0.5)
        band.putalpha(ImageChops.multiply(band.getchannel("A"), _gradient(W, 420, 0.25, 1.0, 1.2).point(lambda v: 255 - v)))
        canvas.alpha_composite(band)
    d = canvas_draw(canvas)

    av = 88
    avatar = images.get(cs.avatar)
    if avatar is not None:
        canvas.alpha_composite(round_avatar(avatar, av), (PAD, 44))
    d.ellipse((PAD - 4, 40, PAD + av + 4, 48 + av), outline=SIGNAL, width=3)
    d.text((PAD + av + 24, 48), cs.name, font=number(42), fill=WHITE)
    uid = f"UID {cs.uid}"
    d.text((PAD + av + 26, 100), f"{uid}   /   {cs.region}", font=font(20), fill=DIM)
    if c is None:
        d.text((PAD, 260), "No Contingency Contract yet", font=font(32), fill=DIM)
        return canvas.convert("RGB")

    d.text((PAD, 220), "CONTINGENCY CONTRACT", font=font(20, "bold"), fill=SIGNAL)
    nf = number(64)
    while d.textlength(c.name, font=nf) > W - PAD * 2 and nf.size > 34:
        nf = number(nf.size - 4)
    d.text((PAD - 2, 248), c.name, font=nf, fill=WHITE)
    left = time_left(c, cs.now)
    if left:
        d.text((PAD, 260 + nf.size + 10), left.upper(), font=font(20, "bold"), fill=DIM)

    y = 430
    sw = 420
    d.rounded_rectangle((PAD, y, PAD + sw, H - 80), 24, fill=PANEL, outline=LINE, width=2)
    d.text((PAD + 30, y + 28), "BEST SCORE", font=font(18, "bold"), fill=DIM)
    d.text((PAD + 26, y + 52), str(c.best), font=number(170), fill=SIGNAL)
    d.text((PAD + 30, H - 140), f"{c.attempts} ATTEMPTS", font=font(20, "bold"), fill=DIM)

    medal = medal_image(images, c)
    if medal is not None:
        g = fit(medal, 130, 130)
        canvas.alpha_composite(g, (PAD + sw - 30 - g.width, y + 30))

    mx = PAD + sw + 28
    mw = W - PAD - mx
    d.rounded_rectangle((mx, y, mx + mw, H - 80), 24, fill=PANEL, outline=LINE, width=2)
    my = y + 34
    for m in c.missions:
        d.text((mx + 32, my), m.label.upper(), font=font(19, "bold"), fill=DIM)
        value = f"{m.current} / {m.total}"
        d.text((mx + mw - 32 - d.textlength(value, font=number(34)), my - 8), value, font=number(34),
               fill=DONE if m.done else WHITE)
        cells = max(1, m.total)
        step = (mw - 64 + 8) / cells
        for k in range(cells):
            x0 = mx + 32 + k * step
            d.rounded_rectangle((x0, my + 40, x0 + step - 8, my + 60), 5,
                                fill=(DONE if m.done else SIGNAL) if k < m.current else OFF)
        my += 100
    status = (f"MEDAL LV {c.medal_level}" + (" · PLATED" if c.plated else "")) if c.medal_level else "MEDAL NOT EARNED YET"
    d.text((mx + 32, H - 124), status, font=font(18, "bold"), fill=SIGNAL if c.medal_level else DIM)
    brand(d, W - PAD, H - 50, DIM)
    return canvas.convert("RGB")
