import json

import pytest
from PIL import Image

import akef
import akef_cards
from akef_cards.framing import splash_focus
from akef.enka import build_from_skport
from akef_cards.templates import showcase

from tests.helpers import DATA


async def test_skport_build_renders(data):
    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    build = build_from_skport(data, card, card.character("Arcane"))
    assert splash_focus(build) is None
    assert showcase.render(build, {}).size == (showcase.W, showcase.H)


async def test_renders_offline(profile):
    image = showcase.render(profile.build("Si"), {})
    assert image.size == (showcase.W, showcase.H)


async def test_custom_art_fills_the_left(profile):
    art = Image.new("RGBA", (600, 900), (200, 80, 80, 255))
    image = showcase.render(profile.build("Liino"), {}, art=art, hide_uid=True)
    assert image.getpixel((300, 600))[0] > 150


async def test_build_without_stats_or_gear(profile):
    build = profile.build("Si")
    build.stats, build.gear, build.weapon = None, [], None
    showcase.render(build, {})


async def test_unknown_template(profile):
    cards = akef_cards.Cards()
    with pytest.raises(ValueError):
        await cards.render(profile.build("Si"), template="nope")


async def test_enka_splash_gets_framed(profile):
    si = profile.build("Si")
    assert splash_focus(si) == splash_focus(profile.build("Arcane")) is not None
    scene = Image.new("RGBA", (2048, 2048), (90, 120, 200, 255))
    framed = showcase._frame_splash(scene, splash_focus(si))
    assert framed.size == (showcase.ART_W, showcase.H)
    assert framed.getpixel((400, 700))[3] == 255
    assert framed.getpixel((showcase.ART_W - 2, 700))[3] < 20


def test_essence_badge():
    capsule = Image.new("RGBA", (128, 128), (220, 230, 60, 255))
    capsule.paste((20, 20, 20, 255), (60, 30, 110, 80))
    badge = Image.new("RGBA", (64, 64), (0, 120, 255, 255))
    merged = showcase._essence_image(capsule, badge)
    assert merged.getpixel((85, 55))[2] == 255
    assert merged.getpixel((5, 120))[:3] == (220, 230, 60)
    assert showcase._essence_image(capsule, None) is capsule


@pytest.mark.parametrize("template", [2])
async def test_other_templates(profile, template):
    from akef_cards.templates import TEMPLATES

    image = TEMPLATES[template](profile.build("Si"), {})
    assert image.width > 1900 and image.height >= 1200
    bare = profile.build("Arcane")
    bare.stats, bare.gear, bare.weapon, bare.talents = None, [], None, []
    TEMPLATES[template](bare, {})


async def test_compare(profile):
    from akef_cards.templates import compare

    a, b = profile.build("Si"), profile.build("Si")
    image = compare.render(a, b, {})
    assert image.width == compare.W and 1000 < image.height < 1800
    b.stats = None
    compare.render(a, b, {}, hide_uid=True)


@pytest.mark.parametrize("template", [2])
async def test_compare_styles(profile, template):
    from akef_cards.templates import COMPARE

    a, b = profile.build("Si"), profile.build("Si")
    assert COMPARE[template](a, b, {}).height < 1300
    b.stats, b.gear = None, []
    COMPARE[template](a, b, {}, hide_uid=True)


def test_hidden_uid():
    from akef_cards.draw import blur_uid, canvas_draw, font

    def draw(hidden):
        token = blur_uid.set(hidden)
        try:
            img = Image.new("RGBA", (400, 60), (255, 255, 255, 255))
            canvas_draw(img).text((10, 10), "UID 4727743200", font=font(30), fill=(0, 0, 0))
        finally:
            blur_uid.reset(token)
        return img

    plain, blurred = draw(False), draw(True)
    assert plain.crop((0, 0, 32, 60)).tobytes() == blurred.crop((0, 0, 32, 60)).tobytes()
    assert plain.crop((80, 0, 400, 60)).tobytes() != blurred.crop((80, 0, 400, 60)).tobytes()
