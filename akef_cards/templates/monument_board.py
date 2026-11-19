from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageOps

from akef_cards.draw import canvas_draw, cover, fit, font, number, shorten
from akef_cards.monument import Event, Monument, clock
from akef_cards.templates.live_parts import round_avatar
from akef_cards.templates.showcase import BG, CARD, HAIR, MUTED, SIGNAL, SLATE, TEXT

W = 1600
PAD = 56
GAP = 24
TRACK = (232, 230, 223)
AGONY = (206, 64, 52)


def _header(canvas, d, mon: Monument, images, title, hide_uid):
    av = 104
    avatar = images.get(mon.avatar)
    d.ellipse((PAD - 5, 46 - 5, PAD + av + 5, 46 + av + 5), fill=SIGNAL)
    if avatar is not None:
        canvas.alpha_composite(round_avatar(avatar, av), (PAD, 46))
    tx = PAD + av + 30
    d.text((tx, 44), mon.name, font=number(56), fill=TEXT)
    uid = f"UID {mon.uid}"
    d.text((tx, 112), f"{uid}  ·  {mon.region}  ·  Authority {mon.level}", font=font(24), fill=MUTED)
    d.text((W - PAD - d.textlength(title, font=font(20, "bold")), 56), title, font=font(20, "bold"), fill=SIGNAL)


def _totals(d, mon: Monument, y):
    normal = sum(e.cleared[0] for e in mon.events)
    agony = sum(e.cleared[1] for e in mon.events)
    stages = sum(len(e.stages) for e in mon.events)
    medals = sum(1 for e in mon.events if e.medal_level)
    x = W - PAD
    for label, value in (("MEDALS", f"{medals}/{len(mon.events)}"), ("AGONY", f"{agony}/{stages}"), ("NORMAL", f"{normal}/{stages}")):
        w = max(d.textlength(value, font=number(40)), d.textlength(label, font=font(16, "bold")))
        x -= w
        d.text((x, y), label, font=font(16, "bold"), fill=AGONY if label == "AGONY" else MUTED)
        d.text((x - 1, y + 18), value, font=number(40), fill=TEXT)
        x -= 44


def _pips(d, x, y, flags, color, size=16, gap=6):
    for i, on in enumerate(flags):
        px = x + i * (size + gap)
        d.rounded_rectangle((px, y, px + size, y + size), 4, fill=color if on else TRACK)


def _event_tile(canvas, d, e: Event, images, x, y, tw, art_h, th):
    d.rounded_rectangle((x, y, x + tw, y + th), 24, fill=CARD, outline=HAIR, width=2)
    art = Image.new("RGBA", (tw, art_h), SLATE)
    poster = images.get(e.art)
    normal, agony = e.cleared
    if poster is not None:
        poster = cover(poster, tw, art_h, 0.2)
        if not normal:
            grey = ImageOps.grayscale(poster.convert("RGB")).convert("RGBA")
            grey.putalpha(poster.getchannel("A"))
            poster = Image.blend(grey, Image.new("RGBA", poster.size, BG + (255,)), 0.35)
        art.alpha_composite(poster)
    mask = Image.new("L", (tw, art_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw - 1, art_h + 40), 24, fill=255)
    art.putalpha(mask)
    canvas.alpha_composite(art, (x, y))

    medal = images.get(e.medal)
    if medal is not None and e.medal_level:
        mx, my = x + tw - 92, y + art_h - 80
        d.rounded_rectangle((mx, my, mx + 76, my + 76), 18, fill=CARD, outline=SIGNAL if e.plated else HAIR, width=3)
        g = fit(medal, 64, 64)
        canvas.alpha_composite(g, (mx + 38 - g.width // 2, my + 38 - g.height // 2))
    if e.running:
        d.rounded_rectangle((x + 16, y + 16, x + 120, y + 46), 15, fill=SIGNAL)
        d.text((x + 30, y + 20), "RUNNING", font=font(17, "bold"), fill=SLATE)

    iy = y + art_h + 20
    d.text((x + 22, iy), shorten(d, e.name, font(26, "semibold"), tw - 44), font=font(26, "semibold"), fill=TEXT)
    total = len(e.stages)
    d.text((x + 22, iy + 46), "NORMAL", font=font(15, "bold"), fill=MUTED)
    _pips(d, x + 104, iy + 46, [s.normal_done for s in e.stages], SLATE)
    d.text((x + tw - 22 - d.textlength(f"{normal}/{total}", font=number(20)), iy + 42), f"{normal}/{total}",
           font=number(20), fill=TEXT)
    d.text((x + 22, iy + 76), "AGONY", font=font(15, "bold"), fill=AGONY if agony else MUTED)
    _pips(d, x + 104, iy + 76, [s.agony_done for s in e.stages], AGONY)
    d.text((x + tw - 22 - d.textlength(f"{agony}/{total}", font=number(20)), iy + 72), f"{agony}/{total}",
           font=number(20), fill=AGONY if agony else TEXT)
    fastest = e.fastest
    note = f"Fastest clear {clock(fastest.seconds)}" if fastest else "Not cleared yet"
    d.text((x + 22, iy + 112), note, font=font(19), fill=MUTED)


def render_overview(mon: Monument, images, *, hide_uid: bool = False) -> Image.Image:
    cols = 4
    tw = (W - PAD * 2 - GAP * (cols - 1)) // cols
    art_h = int(tw * 1.2)
    th = art_h + 160
    rows = max(1, math.ceil(len(mon.events) / cols))
    h = 210 + rows * th + (rows - 1) * GAP + 80
    canvas = Image.new("RGBA", (W, h), BG)
    d = canvas_draw(canvas)
    _header(canvas, d, mon, images, "MONUMENT", hide_uid)
    _totals(d, mon, 96)
    for i, e in enumerate(mon.events):
        r, c = divmod(i, cols)
        _event_tile(canvas, d, e, images, PAD + c * (tw + GAP), 200 + r * (th + GAP), tw, art_h, th)
    _footer(d, h)
    return canvas.convert("RGB")


def _footer(d, h):
    d.text((PAD, h - 44), "via skport", font=font(18), fill=MUTED)
    d.text((W - PAD - d.textlength("akef", font=font(18, "semibold")), h - 44), "akef", font=font(18, "semibold"), fill=MUTED)
