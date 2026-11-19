from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from akef_cards.draw import canvas_draw, cover, fit, font, number, shorten
from akef_cards.i18n import short_date
from akef_cards.monument import Event, Monument, Stage, clock
from akef_cards.templates.flex import member
from akef_cards.templates.live_parts import round_avatar
from akef_cards.templates.parts import two_pass
from akef_cards.templates.profile import _round_mask
from akef_cards.templates.showcase import BG, CARD, HAIR, MUTED, SIGNAL, SLATE, TEXT

W = 2000
PAD = 56
AGONY = (214, 64, 58)

LIGHT = {"bg": BG, "card": CARD, "line": HAIR, "text": TEXT, "dim": MUTED, "tile": SLATE, "chip": SLATE}
DARK = {"bg": (15, 16, 20), "card": (26, 28, 34), "line": (44, 47, 56), "text": (240, 241, 245),
        "dim": (140, 144, 154), "tile": (40, 43, 52), "chip": (236, 236, 240)}


def _poster(img, w, h, fill):
    # some posters carry a half transparent green edge from their cutout, it shows up once they're scaled
    img = img.convert("RGBA")
    img.putalpha(img.getchannel("A").point(lambda v: 255 if v > 180 else 0))
    out = Image.new("RGBA", (w, h), fill + (255,))
    out.alpha_composite(cover(img, w, h, 0.2))
    return out


def _header(canvas, d, mon: Monument, images, hide_uid, p, w=None):
    w = w or W
    av = 104
    avatar = images.get(mon.avatar)
    d.ellipse((PAD - 5, 41, PAD + av + 5, 41 + av + 10), fill=SIGNAL)
    if avatar is not None:
        canvas.alpha_composite(round_avatar(avatar, av), (PAD, 46))
    tx = PAD + av + 30
    d.text((tx, 44), mon.name, font=number(56), fill=p["text"])
    uid = f"UID {mon.uid}"
    d.text((tx, 112), f"{uid}  ·  {mon.region}  ·  Authority {mon.level}", font=font(24), fill=p["dim"])
    label = "MONUMENT"
    d.text((w - PAD - d.textlength(label, font=font(20, "bold")), 56), label, font=font(20, "bold"), fill=SIGNAL)


def _medal(canvas, d, event: Event, images, x, y, size, p):
    medal = images.get(event.medal)
    if medal is None or not event.medal_level:
        return
    d.rounded_rectangle((x, y, x + size, y + size), size // 5, fill=p["card"],
                        outline=SIGNAL if event.plated else p["line"], width=3)
    g = fit(medal, int(size * 0.85), int(size * 0.85))
    canvas.alpha_composite(g, (x + size // 2 - g.width // 2, y + size // 2 - g.height // 2))


def _summary(event: Event) -> str:
    normal, agony = event.cleared
    total = len(event.stages)
    text = f"Normal {normal}/{total}   ·   Agony {agony}/{total}"
    if event.medal_level:
        text += f"   ·   Medal Lv {event.medal_level}" + (" plated" if event.plated else "")
    return text


def _stage_head(canvas, d, s: Stage, images, x, y, w, p):
    d.rounded_rectangle((x, y, x + 96, y + 96), 18, fill=p["tile"])
    enemy = images.get(s.enemy)
    if enemy is not None:
        g = fit(enemy, 86, 86)
        canvas.alpha_composite(g, (x + 48 - g.width // 2, y + 48 - g.height // 2))
    name = shorten(d, s.name, font(24, "semibold"), w - 130)
    d.text((x + 116, y + 12), name, font=font(24, "semibold"), fill=p["text"])
    d.text((x + 116, y + 48), f"Lv {s.level}", font=font(19), fill=p["dim"])


def _rules(d, event: Event, x, y, w, p, limit=4):
    if not event.rules:
        return y
    d.text((x, y), "RULES", font=font(16, "bold"), fill=p["dim"])
    y += 28
    for rule in event.rules[:limit]:
        line = ""
        for word in rule.split():
            test = f"{line} {word}".strip()
            if d.textlength(test, font=font(18)) > w and line:
                d.text((x, y), line, font=font(18), fill=p["text"])
                y += 26
                line = word
            else:
                line = test
        d.text((x, y), line, font=font(18), fill=p["text"])
        y += 34
    return y


def _footer(d, w, y, p):
    d.text((PAD, y), "via skport", font=font(18), fill=p["dim"])
    d.text((w - PAD - d.textlength("akef", font=font(18, "semibold")), y), "akef", font=font(18, "semibold"),
           fill=p["dim"])


def _stage(canvas, d, s: Stage, images, x, y, w, p, art_h):
    clear = s.agony if s.agony else s.normal
    agony = s.agony is not None
    label, color = ("AGONY", AGONY) if agony else ("NORMAL", p["text"])
    if agony:
        glow = Image.new("RGBA", (w + 60, art_h + 210))
        ImageDraw.Draw(glow).rounded_rectangle((30, 30, w + 30, art_h + 180), 28, outline=AGONY + (170,), width=10)
        canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14)), (int(x) - 30, int(y) - 30))
    d.rounded_rectangle((x, y, x + w, y + art_h + 150), 24, fill=p["card"], outline=AGONY if agony else p["line"],
                        width=4 if agony else 2)
    if agony:
        tag = "AGONY CLEAR"
        tw = d.textlength(tag, font=font(15, "bold")) + 28
        d.rounded_rectangle((x + 22, y - 14, x + 22 + tw, y + 16), 15, fill=AGONY)
        d.text((x + 36, y - 10), tag, font=font(15, "bold"), fill=(255, 255, 255))
    _stage_head(canvas, d, s, images, x + 22, y + 22, w - 300, p)
    tag_x = x + w - 24
    for text, f, fill_, dy in ((label, font(16, "bold"), color, 26),
                               (clock(clear.seconds) if clear else "not cleared", number(44) if clear else font(22),
                                AGONY if agony else (p["text"] if clear else p["dim"]), 48),
                               (short_date(clear.when) if clear and clear.when else "", font(17), p["dim"], 100)):
        if text:
            d.text((tag_x - d.textlength(text, font=f), y + dy), text, font=f, fill=fill_)
    if s.agony and s.normal_done:
        note = f"normal {clock(s.normal.seconds)}   " if s.normal else "normal cleared   "
        d.text((tag_x - d.textlength(label, font=font(16, "bold")) - d.textlength(note, font=font(16)), y + 26), note,
               font=font(16), fill=p["dim"])
    team = clear.team if clear else []
    ty = y + 134
    gap = 16
    tw = (w - 44 - gap * 3) // 4
    for k in range(4):
        tx = x + 22 + k * (tw + gap)
        if k < len(team):
            member(canvas, team[k], images, tx, ty, tw, art_h - 4)
        else:
            d.rounded_rectangle((tx, ty, tx + tw, ty + art_h - 4), 22, fill=p["tile"])
    return y + art_h + 150


def _banner(mon: Monument, event: Event, images, hide_uid, p) -> Image.Image:
    w = 2000
    inner = w - PAD * 2
    bh = 460
    cols = 2
    cw = (inner - 24) // cols
    art_h = 300

    def paint(h):
        canvas = Image.new("RGBA", (w, h), p["bg"] + (255,))
        d = canvas_draw(canvas)
        _header(canvas, d, mon, images, hide_uid, p, w)
        top = 196
        poster = images.get(event.art)
        art = _poster(poster, inner, bh, p["tile"]) if poster is not None else Image.new("RGBA", (inner, bh), p["tile"] + (255,))
        shade = Image.new("RGBA", (inner, bh))
        sd = ImageDraw.Draw(shade)
        for row in range(bh // 2):
            sd.line([(0, bh - 1 - row), (inner, bh - 1 - row)], fill=(8, 9, 12, int(220 * (1 - row / (bh / 2)) ** 1.4)))
        art.alpha_composite(shade)
        art.putalpha(_round_mask((inner, bh), 28))
        canvas.alpha_composite(art, (PAD, top))
        nf = number(64)
        while d.textlength(event.name, font=nf) > inner - 200 and nf.size > 32:
            nf = number(nf.size - 4)
        d.text((PAD + 32, top + bh - nf.size - 74), event.name, font=nf, fill=(255, 255, 255))
        d.text((PAD + 34, top + bh - 56), _summary(event), font=font(24), fill=(214, 216, 224))
        _medal(canvas, d, event, images, PAD + inner - 150, top + bh - 150, 118, p)

        normal, agony = event.cleared
        if agony:
            tag = f"AGONY {agony}/{len(event.stages)}"
            tw = d.textlength(tag, font=font(22, "bold")) + 40
            d.rounded_rectangle((PAD + 32, top + 30, PAD + 32 + tw, top + 76), 23, fill=AGONY)
            d.text((PAD + 52, top + 38), tag, font=font(22, "bold"), fill=(255, 255, 255))
        y = top + bh + 30
        if event.rules:
            y = _rules(d, event, PAD, y, inner, p, 3) + 10
        row_h = art_h + 150 + 40
        for i, s in enumerate(event.stages):
            _stage(canvas, d, s, images, PAD + (i % cols) * (cw + 24), y + (i // cols) * row_h, cw, p, art_h)
        y += -(-len(event.stages) // cols) * row_h + 40
        _footer(d, w, y, p)
        return canvas, y + 50

    return two_pass(paint)


def latest(mon: Monument) -> Event:
    running = [e for e in mon.events if e.running]
    if running:
        return running[0]
    if not mon.events:
        raise KeyError("no monument events on this account")
    dated = [e for e in mon.events if e.started]
    return max(dated, key=lambda e: e.started) if dated else mon.events[0]


def render_banner(mon, event, images, *, hide_uid=False):
    return _banner(mon, event, images, hide_uid, LIGHT)


def render_banner_dark(mon, event, images, *, hide_uid=False):
    return _banner(mon, event, images, hide_uid, DARK)


TEMPLATES = {1: render_banner, 2: render_banner_dark}
