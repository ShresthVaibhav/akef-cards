import threading

from PIL import Image

from akef_cards.draw import brand, canvas_draw, cover, font, number, shorten, star
from akef_cards.live import Live, until
from akef_cards.templates.live_parts import STAGE_STARS, bar, meter_text, ring, round_avatar, sanity_note, stamp
from akef_cards.templates.profile import _round_mask
from akef_cards.templates.showcase import BG, CARD, HAIR, MUTED, SIGNAL, SLATE, TEXT

W, H = 1600, 1000
PAD = 56

LIGHT = {"bg": BG, "card": CARD, "line": HAIR, "text": TEXT, "dim": MUTED, "track": (232, 230, 223),
         "chip": SLATE, "done": SLATE, "contract": SLATE}
DARK = {"bg": (15, 16, 20), "card": (26, 28, 34), "line": (44, 47, 56), "text": (240, 241, 245), "dim": (140, 144, 154),
        "track": (48, 51, 60), "chip": (44, 47, 56), "done": (236, 236, 240), "contract": (8, 9, 12)}
P = LIGHT
_lock = threading.Lock()


def _panel(d, x, y, w, h):
    d.rounded_rectangle((x, y, x + w, y + h), 26, fill=P["card"], outline=P["line"], width=2)


def _header(canvas, d, live: Live, images, hide_uid):
    av = 104
    avatar = images.get(live.avatar)
    d.ellipse((PAD - 5, 46 - 5, PAD + av + 5, 46 + av + 5), fill=SIGNAL)
    if avatar is not None:
        canvas.alpha_composite(round_avatar(avatar, av), (PAD, 46))
    tx = PAD + av + 30
    d.text((tx, 44), live.name, font=number(56), fill=P["text"])
    uid = f"UID {live.uid}"
    d.text((tx, 112), f"{uid}  ·  {live.region}  ·  Authority {live.level}", font=font(24), fill=P["dim"])
    label = "LIVE STATUS"
    d.text((W - PAD - d.textlength(label, font=font(20, "bold")), 56), label, font=font(20, "bold"), fill=SIGNAL)
    d.text((W - PAD - d.textlength(stamp(live), font=font(22)), 86), stamp(live), font=font(22), fill=P["dim"])


def _sanity(canvas, d, live: Live, x, y, w, h):
    _panel(d, x, y, w, h)
    d.text((x + 34, y + 30), "SANITY", font=font(20, "bold"), fill=P["dim"])
    size = 280
    gx, gy = x + (w - size) // 2, y + 76
    canvas.alpha_composite(ring(size, live.sanity.share, SIGNAL, P["track"], 26), (gx, gy))
    value = str(live.sanity.current)
    d.text((gx + size / 2 - d.textlength(value, font=number(92)) / 2, gy + 72), value, font=number(92), fill=P["text"])
    total = f"/ {live.sanity.total}"
    d.text((gx + size / 2 - d.textlength(total, font=font(28)) / 2, gy + 178), total, font=font(28), fill=P["dim"])
    note = sanity_note(live)
    nf = font(28, "semibold")
    d.rounded_rectangle((x + w / 2 - d.textlength(note, font=nf) / 2 - 22, y + h - 80,
                         x + w / 2 + d.textlength(note, font=nf) / 2 + 22, y + h - 32), 24,
                        fill=P["chip"] if live.sanity.done else P["track"])
    d.text((x + w / 2 - d.textlength(note, font=nf) / 2, y + h - 73), note, font=nf,
           fill=SIGNAL if live.sanity.done else P["text"])


def _meter(d, m, x, y, w, h):
    _panel(d, x, y, w, h)
    d.text((x + 28, y + 24), m.label.upper(), font=font(18, "bold"), fill=P["dim"])
    d.text((x + 26, y + 52), meter_text(m), font=number(46), fill=P["text"])
    if m.done:
        tag = "DONE"
        tw = d.textlength(tag, font=font(16, "bold")) + 24
        d.rounded_rectangle((x + w - 28 - tw, y + 24, x + w - 28, y + 52), 14, fill=P["chip"])
        d.text((x + w - 16 - tw, y + 28), tag, font=font(16, "bold"), fill=SIGNAL)
    bar(d, x + 28, y + h - 52, w - 56, 14, m.share, SIGNAL if not m.done else P["done"], P["track"])
    if m.note:
        d.text((x + 28, y + h - 30), m.note, font=font(17), fill=P["dim"])


def _echoes(d, live: Live, x, y, w, h):
    _panel(d, x, y, w, h)
    e = live.echoes
    d.text((x + 28, y + 24), "WAR ECHOES", font=font(18, "bold"), fill=P["dim"])
    if e is None:
        d.text((x + 28, y + 60), "No season running", font=font(26), fill=P["dim"])
        return
    d.text((x + 28, y + 52), shorten(d, e.cycle or e.season, font(32, "semibold"), w - 200), font=font(32, "semibold"), fill=P["text"])
    total = f"{e.stars}"
    d.text((x + w - 70 - d.textlength(total, font=number(44)), y + 46), total, font=number(44), fill=P["text"])
    star(d, x + w - 46, y + 72, 16, SIGNAL)
    sy = y + 110
    for name, got in e.stages[:3]:
        d.text((x + 28, sy), shorten(d, name, font(21), w - 200), font=font(21), fill=P["text"])
        for i in range(STAGE_STARS):
            star(d, x + w - 120 + i * 32, sy + 13, 12, SIGNAL if i < got else P["track"])
        sy += 36
    left = until(e.ends, live.now)
    if left:
        d.text((x + 28, y + h - 36), f"Cycle ends in {left}", font=font(18), fill=P["dim"])


def _contract(canvas, d, live: Live, images, x, y, w, h):
    c = live.contract
    panel = Image.new("RGBA", (w, h), P["contract"])
    art = images.get(c.art) if c else None
    if art is not None:
        art = cover(art, w, h, 0.4)
        art.putalpha(art.getchannel("A").point(lambda v: v * 45 // 100))
        panel.alpha_composite(art)
    panel.putalpha(_round_mask((w, h), 26))
    canvas.alpha_composite(panel, (x, y))
    d.text((x + 28, y + 24), "CONTINGENCY CONTRACT", font=font(18, "bold"), fill=(170, 172, 180))
    if c is None:
        d.text((x + 28, y + 60), "Nothing running", font=font(26), fill=(170, 172, 180))
        return
    d.text((x + 28, y + 52), shorten(d, c.name, font(30, "semibold"), w - 56), font=font(30, "semibold"), fill=BG)
    d.text((x + 28, y + 100), "BEST", font=font(16, "bold"), fill=(170, 172, 180))
    d.text((x + 26, y + 118), str(c.best), font=number(64), fill=SIGNAL)
    mx = x + 200
    d.text((mx, y + 100), "WEEKLY", font=font(16, "bold"), fill=(170, 172, 180))
    d.text((mx, y + 122), meter_text(c.weekly), font=number(36), fill=BG)
    bar(d, mx, y + 172, w - (mx - x) - 32, 12, c.weekly.share, SIGNAL, (60, 63, 70))
    left = until(c.ends, live.now)
    if left:
        d.text((x + 28, y + h - 36), f"Ends in {left}", font=font(18), fill=(170, 172, 180))


def render(live: Live, images, *, hide_uid: bool = False, dark: bool = False) -> Image.Image:
    global P
    with _lock:
        P = DARK if dark else LIGHT
        try:
            return _render(live, images, hide_uid)
        finally:
            P = LIGHT


def _render(live: Live, images, hide_uid) -> Image.Image:
    canvas = Image.new("RGBA", (W, H), P["bg"])
    d = canvas_draw(canvas)
    _header(canvas, d, live, images, hide_uid)
    top = 196
    sw = 440
    _sanity(canvas, d, live, PAD, top, sw, 470)
    gx = PAD + sw + 24
    cw = (W - PAD - gx - 24) // 2
    for i, m in enumerate(live.meters[:4]):
        r, c = divmod(i, 2)
        _meter(d, m, gx + c * (cw + 24), top + r * (223 + 24), cw, 223)
    by = top + 470 + 24
    bw = (W - PAD * 2 - 24) // 2
    _echoes(d, live, PAD, by, bw, 250)
    _contract(canvas, d, live, images, PAD + bw + 24, by, bw, 250)
    d.text((PAD, H - 44), "via skport", font=font(18), fill=P["dim"])
    brand(d, W - PAD, H - 44, P["dim"])
    return canvas.convert("RGB")


def render_dark(live: Live, images, *, hide_uid: bool = False) -> Image.Image:
    return render(live, images, hide_uid=hide_uid, dark=True)
