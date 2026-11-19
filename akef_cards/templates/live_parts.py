from __future__ import annotations

import math

from PIL import Image, ImageDraw

from akef_cards.draw import cover
from akef_cards.i18n import long_date
from akef_cards.live import Live, Meter, until

STAGE_STARS = 3


def ring(size, share, color, track, width, scale=4):
    big = Image.new("RGBA", (size * scale, size * scale))
    d = ImageDraw.Draw(big)
    # pillow grows the arc inwards from the box, so the stroke's middle sits half a width inside the edge
    box = (0, 0, size * scale - 1, size * scale - 1)
    d.arc(box, 0, 360, fill=track, width=width * scale)
    if share > 0:
        end = -90 + 360 * min(share, 1.0)
        d.arc(box, -90, end, fill=color, width=width * scale)
        r = width * scale / 2
        for angle in (-90, end):
            cx = size * scale / 2 + (size * scale / 2 - r) * math.cos(math.radians(angle))
            cy = size * scale / 2 + (size * scale / 2 - r) * math.sin(math.radians(angle))
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    return big.resize((size, size), Image.LANCZOS)


def bar(d, x, y, w, h, share, color, track):
    d.rounded_rectangle((x, y, x + w, y + h), h // 2, fill=track)
    if share > 0:
        d.rounded_rectangle((x, y, x + max(h, int(w * share)), y + h), h // 2, fill=color)


def round_avatar(img, size):
    img = cover(img, size, size, 0.2)
    big = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(big).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    img.putalpha(big.resize((size, size), Image.LANCZOS))
    return img


def sanity_note(live: Live) -> str:
    if live.sanity.done:
        return "Full"
    left = until(live.full_at, live.now)
    return f"Full in {left}" if left else ""


def meter_text(m: Meter) -> str:
    return f"{m.current:,} / {m.total:,}"


def stamp(live: Live) -> str:
    return f"{long_date(live.now)} · {live.now:%H:%M} UTC"
