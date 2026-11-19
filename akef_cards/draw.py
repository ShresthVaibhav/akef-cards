from __future__ import annotations

import math
import re
from contextvars import ContextVar
from functools import lru_cache
from importlib import resources

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from akef_cards.i18n import t

blur_uid: ContextVar[bool] = ContextVar("akef_cards_blur_uid", default=False)
UID = re.compile(r"(?<=UID )\d[\d ]{3,}\d")

WEIGHTS = {"regular": "Regular", "medium": "Medium", "semibold": "SemiBold", "bold": "Bold"}
AXIS = {"regular": 400, "medium": 500, "semibold": 600, "bold": 700}
# barlow is latin only: fira sans covers greek/cyrillic names like "Brr-Brr-Bomb β",
# the noto fonts cover japanese, korean, chinese and thai (sc only for rare characters tc lacks)
FALLBACKS = ("FiraSans", "NotoSansJP", "NotoSansKR", "NotoSansTC", "NotoSansSC", "NotoSansThai")
ROMAN = {chr(0x2160 + i): v for i, v in enumerate(("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"))}
_fallback: dict[int, list[ImageFont.FreeTypeFont]] = {}


def _path(name: str) -> str:
    with resources.as_file(resources.files("akef_cards") / "fonts" / name) as file:
        return str(file)


def _load(family: str, size: int, weight: str) -> ImageFont.FreeTypeFont:
    static = resources.files("akef_cards") / "fonts" / f"{family}-{WEIGHTS[weight]}.ttf"
    if static.is_file():
        return ImageFont.truetype(_path(static.name), size)
    f = ImageFont.truetype(_path(f"{family}.ttf"), size)
    axes = f.get_variation_axes()
    f.set_variation_by_axes([AXIS[weight] if a.get("name") in (b"Weight", "Weight") else a["default"] for a in axes])
    return f


@lru_cache(maxsize=64)
def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    main = _load("Barlow", size, weight)
    _fallback[id(main)] = [_load(name, size, weight) for name in FALLBACKS]
    return main


@lru_cache(maxsize=None)
def _probe(path: str) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, 24)


@lru_cache(maxsize=None)
def _blank(path: str) -> bytes:
    return _shape(path, "󰀀")


def _shape(path: str, ch: str) -> bytes:
    img = Image.new("L", (48, 48))
    ImageDraw.Draw(img).text((12, 12), ch, font=_probe(path), fill=255)
    return img.tobytes()


@lru_cache(maxsize=8192)
def _has(path: str, ch: str) -> bool:
    return ch.isspace() or _shape(path, ch) != _blank(path)


def _runs(text: str, f):
    text = "".join(ROMAN.get(c, c) for c in text)
    others = _fallback.get(id(f))
    if not others or text.isascii():
        return [(text, f)]
    runs = []
    for ch in text:
        use = f
        if not ch.isascii() and not _has(f.path, ch):
            use = next((o for o in others if _has(o.path, ch)), f)
        if runs and runs[-1][1] is use:
            runs[-1] = (runs[-1][0] + ch, use)
        else:
            runs.append((ch, use))
    return runs


class Draw(ImageDraw.ImageDraw):
    def text(self, xy, text, fill=None, font=None, *args, **kwargs):
        text = t(str(text))
        found = UID.search(text) if blur_uid.get() and font is not None and hasattr(self, "canvas") else None
        if found:
            x, y = xy
            head, digits, tail = text[:found.start()], found.group(), text[found.end():]
            self.text((x, y), head, fill, font, *args, **kwargs)
            x += self.textlength(head, font=font)
            self._blurred((x, y), digits, fill, font)
            self.text((x + self.textlength(digits, font=font), y), tail, fill, font, *args, **kwargs)
            return
        runs = _runs(text, font) if font is not None else [(text, font)]
        x, y = xy
        for chunk, f in runs:
            super().text((x, y), chunk, fill=fill, font=f, *args, **kwargs)
            x += super().textlength(chunk, font=f)

    def _blurred(self, xy, text, fill, font):
        pad = max(6, font.size // 2)
        w = int(super().textlength(text, font=font)) + pad * 2
        layer = Image.new("RGBA", (w, int(font.size * 1.6) + pad * 2))
        colour = fill if isinstance(fill, tuple) else (128, 128, 128)
        ImageDraw.Draw(layer).text((pad, pad), text, fill=tuple(colour[:3]) + (255,), font=font)
        layer = layer.filter(ImageFilter.GaussianBlur(max(3, font.size / 5)))
        self.canvas.alpha_composite(layer, (int(xy[0]) - pad, int(xy[1]) - pad))

    def textlength(self, text, font=None, *args, **kwargs):
        if font is None:
            return super().textlength(text, *args, **kwargs)
        return sum(super(Draw, self).textlength(chunk, font=f) for chunk, f in _runs(t(str(text)), font))


def canvas_draw(image: Image.Image) -> Draw:
    d = Draw(image)
    d.canvas = image
    return d


def number(size: int) -> ImageFont.FreeTypeFont:
    return font(size, "semibold")


def fit(img: Image.Image, w: int, h: int) -> Image.Image:
    img = img.convert("RGBA")
    scale = min(w / img.width, h / img.height)
    return img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)


def stand(img: Image.Image, height: int, max_width: int) -> Image.Image:
    # skport art is one canvas size for everyone, so slim poses come out tiny if fitted whole.
    # trim to the figure and size it by height instead
    img = img.convert("RGBA")
    box = img.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
    if box:
        img = img.crop(box)
    scale = min(height / img.height, max_width / img.width)
    return img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)


def body_x(img: Image.Image) -> int:
    column = img.getchannel("A").resize((img.width, 1), Image.BOX)
    weights = list(column.tobytes())
    total = sum(weights)
    return int(sum(i * v for i, v in enumerate(weights)) / total) if total else img.width // 2


def cover(img: Image.Image, w: int, h: int, focus: float = 0.15) -> Image.Image:
    img = img.convert("RGBA")
    scale = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
    left, top = (img.width - w) // 2, int((img.height - h) * focus)
    return img.crop((left, top, left + w, top + h))


def shorten(d: ImageDraw.ImageDraw, text: str, f, room: float) -> str:
    text = t(text)
    if d.textlength(text, font=f) <= room:
        return text
    while text and d.textlength(text + "…", font=f) > room:
        text = text[:-1]
    return text.rstrip(" :·") + "…"


def star(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill) -> None:
    points = []
    for i in range(10):
        radius = r if i % 2 == 0 else r * 0.45
        angle = math.pi / 2 + i * math.pi / 5
        points.append((cx + radius * math.cos(angle), cy - radius * math.sin(angle)))
    d.polygon(points, fill=fill)


MARK_CENTRE = (8.08, 7.28)
MARK_WEDGE = [(10.93, 0.71), (8.22, 2.27), (8.43, 6.46), (11.07, 7.23)]
MARK_BLADE = [(8.28, 3.24), (8.15, 6.2), (8.47, 6.76), (10.0, 7.8), (12.21, 9.22), (12.21, 6.6), (11.0, 5.85),
              (8.94, 4.51), (8.6, 4.1)]


@lru_cache(maxsize=64)
def rarity_mark(size: int, fill: tuple) -> Image.Image:
    s = size * 4
    img = Image.new("RGBA", (s, s))
    d = ImageDraw.Draw(img)
    cx, cy = MARK_CENTRE
    scale = s / 13.6

    def place(points, turn):
        a = math.radians(turn)
        out = []
        for x, y in points:
            dx, dy = x - cx, y - cy
            rx, ry = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
            out.append(((rx + 1.43) * scale + s / 2, (ry + 0.34) * scale + s / 2))
        return out

    for turn in (0, 120, 240):
        d.polygon(place(MARK_WEDGE, turn), fill=tuple(fill[:3]) + (130,))
    for turn in (0, 120, 240):
        d.polygon(place(MARK_BLADE, turn), fill=tuple(fill[:3]) + (255,))
    return img.resize((size, size), Image.LANCZOS)


def stars(d: ImageDraw.ImageDraw, x: float, y: float, count: int, size: float, fill, gap: float = 4) -> float:
    canvas = getattr(d, "canvas", None)
    step = size + gap
    for i in range(count):
        if canvas is not None:
            mark = rarity_mark(int(size * 1.15), tuple(fill))
            canvas.alpha_composite(mark, (int(x + i * step - size * 0.07), int(y - size * 0.07)))
        else:
            star(d, x + size / 2 + i * step, y + size / 2, size / 2, fill)
    return count * step - gap


STAT_ICON = {
    "HP": "MaxHp", "ATK": "Atk", "DEF": "Def",
    "STR": "Str", "Strength": "Str", "AGI": "Agi", "Agility": "Agi",
    "INT": "Wisd", "Intellect": "Wisd", "WILL": "Will", "Will": "Will",
    "Crit Rate": "CriticalRate", "Crit DMG": "CriticalDamageIncrease", "Ult Gain": "UltimateSpGainScalar",
    "Healing Received": "HealTakenIncrease", "Treatment": "HealOutputIncrease", "Treatment Bonus": "HealOutputIncrease",
    "Arts Intensity": "PhysicalAndSpellInflictionEnhance", "Stagger DMG": "PoiseDamageOutputScalar",
    "Physical DMG": "PhysicalDamageIncrease", "Heat DMG": "FireDamageIncrease", "Electric DMG": "PulseDamageIncrease",
    "Cryo DMG": "CrystDamageIncrease", "Nature DMG": "NaturalDamageIncrease",
    "Basic ATK DMG": "NormalAttackDamageIncrease", "Basic Attack DMG": "NormalAttackDamageIncrease",
    "Battle Skill DMG": "NormalSkillDamageIncrease", "Combo Skill DMG": "ComboSkillDamageIncrease",
    "Ultimate DMG": "UltimateSkillDamageIncrease", "DMG vs. Staggered": "DamageToBrokenUnitIncrease",
}
CLASS_ICON = {"Striker": "ASSAULT", "Caster": "CASTER", "Defender": "DEFENDER", "Guard": "GUARD",
              "Supporter": "SUPPORTER", "Vanguard": "VANGUARD"}


@lru_cache(maxsize=256)
def icon(name: str, size: int, fill: tuple) -> Image.Image | None:
    key = STAT_ICON.get(name) or CLASS_ICON.get(name) or name
    file = resources.files("akef_cards") / "data" / "icons" / f"{key}.png"
    if not file.is_file():
        return None
    with resources.as_file(file) as path:
        glyph = Image.open(path).convert("RGBA")
    glyph = fit(glyph, size, size)
    tinted = Image.new("RGBA", glyph.size, tuple(fill[:3]) + (255,))
    tinted.putalpha(glyph.getchannel("A"))
    return tinted


@lru_cache(maxsize=64)
def class_badge(name: str, size: int, fill: tuple = (26, 28, 33), ink: tuple = (255, 255, 255)) -> Image.Image | None:
    glyph = icon(name, int(size * 0.7), tuple(ink))
    if glyph is None:
        return None
    s = 4
    plate = Image.new("RGBA", (size * s, size * s))
    ImageDraw.Draw(plate).rounded_rectangle((0, 0, size * s - 1, size * s - 1), size * s // 4, fill=tuple(fill[:3]) + (255,))
    plate = plate.resize((size, size), Image.LANCZOS)
    plate.alpha_composite(glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2))
    return plate


def stat_label(d, x, y, name, f, fill, size=None) -> float:
    size = size or int(f.size * 1.05)
    glyph = icon(name, size, tuple(fill))
    canvas = getattr(d, "canvas", None)
    if glyph is not None and canvas is not None:
        canvas.alpha_composite(glyph, (int(x), int(y + (f.size * 1.2 - glyph.height) / 2)))
        x += glyph.width + 6
    d.text((x, y), name, font=f, fill=fill)
    return x + d.textlength(name, font=f)


def lerp(a, b, t: float):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


@lru_cache(maxsize=64)
def potential_mark(size: int, level: int, lit: tuple, dim: tuple) -> Image.Image:
    s = size * 4
    img = Image.new("RGBA", (s, s))
    c, r = s / 2, s * 0.45
    length, side, shear = r * 1.18, r * 0.28, 36

    def polar(angle, dist, ox=c, oy=c):
        return ox + dist * math.cos(math.radians(angle)), oy + dist * math.sin(math.radians(angle))

    rods = []
    for k in range(5):
        start = -122 - 72 * k
        px, py = polar(start, r)
        tx, ty = polar(start + 144, r)
        heading = math.degrees(math.atan2(ty - py, tx - px))
        ex, ey = polar(heading, length, px, py)
        sx, sy = polar(heading + shear, side, 0, 0)
        rods.append([(px, py), (ex, ey), (ex + sx, ey + sy), (px + sx, py + sy)])
    order = [k for k in range(5) if k >= level] + [k for k in range(5) if k < level]
    for k in order:
        shadow = Image.new("RGBA", (s, s))
        ImageDraw.Draw(shadow).polygon([(x + s * 0.006, y + s * 0.018) for x, y in rods[k]], fill=(0, 0, 0, 90))
        img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(s * 0.008)))
        ImageDraw.Draw(img).polygon(rods[k], fill=tuple((lit if k < level else dim)[:3]) + (255,))
    return img.resize((size, size), Image.LANCZOS)
