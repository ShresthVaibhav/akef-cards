from __future__ import annotations

import threading

from PIL import Image, ImageChops, ImageDraw

from akef_cards.draw import canvas_draw, cover, fit, font, number
from akef_cards.templates.showcase import BG, CARD, HAIR, MUTED, SIGNAL, SLATE, TEXT, _wrap
from akef.wiki import WikiPage

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


W, H = 2000, 1200
ART_W = 820
PAD = 56


def _art(canvas, page: WikiPage, images):
    art = images.get(page.art)
    if art is None:
        return
    img = fit(art, ART_W + 120, H)
    if img.height < H:
        img = cover(art, ART_W, H, 0.1)
    fade = Image.new("L", img.size, 255)
    fd = ImageDraw.Draw(fade)
    for i in range(160):
        fd.line([(img.width - 1 - i, 0), (img.width - 1 - i, img.height)], fill=int(255 * i / 160))
    img.putalpha(ImageChops.multiply(img.getchannel("A"), fade))
    canvas.alpha_composite(img, (max(0, (ART_W - img.width) // 2), H - img.height))


def _lines(d, text, f, room, limit):
    out = []
    for para in text.splitlines():
        if not para.strip():
            continue
        out += _wrap(d, para.strip(), f, room, limit - len(out))
        if len(out) >= limit:
            break
    return out[:limit]


def _render(page: WikiPage, images, *, hide_uid: bool = False) -> Image.Image:
    canvas = Image.new("RGBA", (W, H), P["bg"])
    _art(canvas, page, images)
    d = canvas_draw(canvas)
    x0, right = ART_W + 40, W - PAD
    room = right - x0

    d.text((x0, 50), "OFFICIAL WIKI", font=font(20, "bold"), fill=SIGNAL)
    nf = number(110)
    while d.textlength(page.name, font=nf) > room and nf.size > 50:
        nf = number(nf.size - 6)
    d.text((x0 - 4, 70), page.name, font=nf, fill=P["text"])
    y = 90 + nf.size

    cx = x0
    for label, value in page.info[:6]:
        lf, vf = font(16, "semibold"), font(20, "semibold")
        w = d.textlength(label, font=lf) + d.textlength(value, font=vf) + 40
        if cx + w > right:
            cx = x0
            y += 50
        d.rounded_rectangle((cx, y, cx + w, y + 40), 20, fill=SLATE)
        d.text((cx + 16, y + 10), label, font=lf, fill=(160, 162, 170))
        d.text((cx + 24 + d.textlength(label, font=lf), y + 7), value, font=vf, fill=CHIP)
        cx += w + 10
    y += 66

    if page.quote:
        d.rounded_rectangle((x0, y, x0 + 6, y + 34), 3, fill=SIGNAL)
        for line in _lines(d, f"“{page.quote}”", font(26, "semibold"), room - 24, 2):
            d.text((x0 + 22, y), line, font=font(26, "semibold"), fill=P["text"])
            y += 36
        y += 10
    for line in _lines(d, page.bio, font(20), room, 3):
        d.text((x0, y), line, font=font(20), fill=P["dim"])
        y += 29
    y += 24

    d.text((x0, y), "SKILLS", font=font(18, "bold"), fill=P["dim"])
    y += 34
    skills = page.skills[:4]
    if skills:
        sh = (H - 80 - y - 12 * (len(skills) - 1)) // len(skills)
        for skill in skills:
            d.rounded_rectangle((x0, y, right, y + sh), 20, fill=P["card"], outline=P["line"], width=2)
            d.rounded_rectangle((x0 + 16, y + 16, x0 + 84, y + 84), 16, fill=SLATE)
            icon = images.get(skill.icon)
            if icon is not None:
                g = fit(icon, 54, 54)
                canvas.alpha_composite(g, (x0 + 50 - g.width // 2, y + 50 - g.height // 2))
            tx = x0 + 104
            d.text((tx, y + 14), skill.name, font=font(26, "semibold"), fill=P["text"])
            kind = skill.kind.upper()
            kx = tx + d.textlength(skill.name, font=font(26, "semibold")) + 14
            kw = d.textlength(kind, font=font(14, "bold")) + 20
            d.rounded_rectangle((kx, y + 20, kx + kw, y + 44), 12, fill=SIGNAL)
            d.text((kx + 10, y + 23), kind, font=font(14, "bold"), fill=SLATE)
            ty = y + 52
            limit = max(1, (sh - 62) // 26)
            for line in _lines(d, skill.text, font(18), right - tx - 20, limit):
                d.text((tx, ty), line, font=font(18), fill=P["dim"])
                ty += 26
            y += sh + 12
    d.text((W - PAD - d.textlength("akef", font=font(18, "semibold")), H - 46), "akef", font=font(18, "semibold"), fill=P["dim"])
    d.text((x0, H - 46), "via skport wiki", font=font(18), fill=P["dim"])
    return canvas.convert("RGB")


render = _themed(_render)
