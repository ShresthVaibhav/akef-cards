import pytest
from PIL import Image

import akef_cards
from akef_cards.draw import canvas_draw, font
from akef_cards.templates import showcase


def test_greek_fallback():
    d = canvas_draw(Image.new("RGB", (10, 10)))
    f = font(30)
    # β comes from fira sans and Ⅱ is spelled out, neither should be a blank box
    assert d.textlength("β", font=f) > 5
    assert d.textlength("Ⅱ", font=f) == d.textlength("II", font=f)


@pytest.mark.parametrize("text", ["アーケイン", "아케인", "煙火邀星河"])
def test_cjk_falls_back(text):
    d = canvas_draw(Image.new("RGB", (10, 10)))
    f = font(30, "bold")
    from akef_cards.draw import _runs

    used = {run_font.path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for _, run_font in _runs(text, f)}
    assert used and all(name.startswith("NotoSans") for name in used)
    assert d.textlength(text, font=f) > 30 * len(text) * 0.6


def test_label_lang():
    from akef_cards.i18n import duration, language, t

    token = language.set("ja")
    try:
        assert t("Intellect") == "知性"
        assert t("GEAR") == "GEAR"
        assert duration("2M") == "2M"
        assert t("Not a known label") == "Not a known label"
    finally:
        language.reset(token)
    assert t("GEAR") == "GEAR"


async def test_other_lang(profile, data, tmp_path):
    cards = akef_cards.Cards(data=data, images=akef_cards.ImageCache(tmp_path))
    data.locale = "de"
    try:
        image = await cards.render(profile.build("Si"))
    finally:
        data.locale = "en"
    assert image.size == (showcase.W, showcase.H)


@pytest.mark.parametrize("name", ["Abriegelungsartillerie", "Überschwänglicher Auslöser", "白けさせるない！胸中に成竹在り", "ใครก็ห้ามขัดจังหวะความสนุก"])
def test_skill_names_fit(name):
    d = canvas_draw(Image.new("RGB", (10, 10)))
    f = font(21, "semibold")
    lines = showcase._wrap(d, name, f, 130, 2)
    assert 1 <= len(lines) <= 2
    assert all(d.textlength(line, font=f) <= 130 for line in lines)


def test_untranslated_keeps_names():
    with pytest.warns(UserWarning, match="aren't translated"):
        cards = akef_cards.Cards(lang="ja")
    assert cards.data.locale == "ja"


def test_unknown_lang():
    with pytest.warns(UserWarning, match="not supported"):
        cards = akef_cards.Cards(lang="klingon")
    assert cards.data.locale == "en"


def test_missing_label_logs(caplog):
    from akef_cards import i18n

    token = i18n.language.set("de")
    try:
        with caplog.at_level("WARNING", logger="akef_cards"):
            assert i18n.t("Talents 12/12") == "Talents 12/12"
            assert i18n.t("HP") != "HP"
    finally:
        i18n.language.reset(token)
    assert any("Talents {}" in r.getMessage() for r in caplog.records)
