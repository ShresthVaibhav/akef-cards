import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

import akef
import akef_cards
from akef_cards.framing import pages, splash_focus, tile_crop
from akef_cards.draw import canvas_draw, font
from akef.enka import GameData, build_from_skport, player_from_skport, profile_from_enka
from akef.wiki import wiki_page
from akef_cards.templates import showcase

DATA = Path(__file__).parent / "data"

@pytest.fixture
async def data(tmp_path):
    shutil.copytree(DATA / "enka", tmp_path, dirs_exist_ok=True)
    game = GameData(tmp_path)
    await game.load()
    return game


@pytest.fixture
async def profile(data):
    raw = json.loads((DATA / "enka" / "player.json").read_text(encoding="utf-8"))
    return await profile_from_enka(data, raw)


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


def test_essence_badge_lands_on_the_dark_face():
    capsule = Image.new("RGBA", (128, 128), (220, 230, 60, 255))
    capsule.paste((20, 20, 20, 255), (60, 30, 110, 80))
    badge = Image.new("RGBA", (64, 64), (0, 120, 255, 255))
    merged = showcase._essence_image(capsule, badge)
    assert merged.getpixel((85, 55))[2] == 255
    assert merged.getpixel((5, 120))[:3] == (220, 230, 60)
    assert showcase._essence_image(capsule, None) is capsule


def test_greek_and_roman_fall_back():
    d = canvas_draw(Image.new("RGB", (10, 10)))
    f = font(30)
    # β comes from fira sans, Ⅱ is spelled out, neither should be a zero-width box
    assert d.textlength("β", font=f) > 5
    assert d.textlength("Ⅱ", font=f) == d.textlength("II", font=f)


async def test_skport_player_pages():
    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])

    player = player_from_skport(card)
    picked = [c.name for c in card.showcased]
    assert [op.name for op in player.roster[:len(picked)]] == picked
    assert len(player.roster) == len(card.chars)
    assert [len(p) for p in pages(player, "4x2")][:-1] == [8] * (len(pages(player, "4x2")) - 1)
    assert all(len(p) <= 9 for p in pages(player, "3x3"))


@pytest.mark.parametrize("number", [1, 2, 3])
@pytest.mark.parametrize("grid", ["4x2", "3x3"])
async def test_profile_templates_render_offline(profile, number, grid):
    from akef_cards.templates import PROFILES

    template = PROFILES[number]
    image = template.render(profile.player, {}, grid=grid)
    assert image.width == template.WIDTH[grid]
    with pytest.raises(ValueError):
        template.render(profile.player, {}, grid="5x5")


async def test_enka_tiles_frame_the_face(profile):
    si = profile.player.roster[0]
    assert "/ui/ef/splash/" in si.portrait
    assert tile_crop(si) == tuple(json.loads((Path(akef_cards.__file__).parent / "data" / "faces.json").read_text())["chr_0036_jsspsi"])


def test_live_card_renders_offline():
    from akef_cards.sources.skport import live_from_skport
    from akef_cards.templates import LIVE

    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    live = live_from_skport(card)
    assert live.sanity.total > 0 and len(live.meters) == 4
    for draw in LIVE.values():
        assert draw(live, {}).size == (1600, 1000)


def test_monument_cards_render_offline():
    from akef_cards.sources.skport import monument_from_skport
    from akef_cards.templates import monument_board

    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    raw = json.loads((DATA / "indie_hard.json").read_text(encoding="utf-8"))["data"]["indieHard"]
    mon = monument_from_skport(card, akef.IndieHard.model_validate(raw))
    first = mon.event("murmurs")
    assert first.cleared == (4, 0) and first.fastest.seconds == 68
    assert len(first.stages[0].normal.team) == 4
    assert monument_board.render_overview(mon, {}).width == monument_board.W
    with pytest.raises(KeyError):
        mon.event("nope")


@pytest.mark.parametrize("number", [1, 2])
def test_factory_templates_render_offline(number):
    from akef_cards.sources.skport import factory_from_skport
    from akef_cards.templates import FACTORY

    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    factory = factory_from_skport(card)
    assert [r.name for r in factory.regions] == ["Valley IV", "Wuling"]
    assert len(factory.regions[0].posts) == 3
    assert FACTORY[number](factory, {}).width == 1600


async def test_cards_keeps_drawn_cards(profile, tmp_path):
    cards = akef_cards.Cards(images=akef_cards.ImageCache(tmp_path))
    si = profile.build("Si")
    si.art, si.element_icon, si.skills, si.talents, si.gear, si.weapon = "", "", [], [], [], None
    first = await cards.render(si)
    assert len(cards._drawn._data) == 1
    again = await cards.render(si)
    assert again.tobytes() == first.tobytes() and again is not first
    si.level = 80
    await cards.render(si)
    assert len(cards._drawn._data) == 2
    await cards.render(si, art=Image.new("RGBA", (10, 10)))
    assert len(cards._drawn._data) == 2


async def test_pull_history_card(data):
    from akef_cards.sources.skport import pulls_from_skport
    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    raw = json.loads((DATA / "pulls.json").read_text(encoding="utf-8"))
    ops = [akef.Pull.model_validate(dict(r, banner=k.lower())) for k, rows in raw["chars"].items() for r in rows]
    weapons = [akef.Pull.model_validate(dict(r, banner=r.get("poolType", ""))) for r in raw["weapons"]]
    pulls = akef.Pulls(operators=sorted((p for p in ops if p.kind == "draw"), key=lambda p: p.seq_id),
                       weapons=sorted(weapons, key=lambda p: p.seq_id))
    history = pulls_from_skport(data, card, pulls)
    assert [h.pity for h in history.operators][:2] == [68, 69]
    assert all(h.icon for h in history.operators + history.weapons)
    from akef_cards.templates import PULLS

    for module in PULLS.values():
        assert module.render(history, {}).width == module.W

    from datetime import date

    recent = pulls_from_skport(data, card, pulls, date(2026, 11, 1))
    assert [h.name for h in recent.operators] == ["Argent Flow"]
    assert recent.total < history.total
    assert [t.since for t in recent.tracks] == [t.since for t in history.tracks]


@pytest.mark.parametrize("number", [1, 2])
def test_contract_card(number):
    from akef_cards.sources.skport import contracts_from_skport
    from akef_cards.templates import CONTRACT

    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    contracts = contracts_from_skport(card)
    assert contracts.current.best == card.crisis_contract[0].highest
    raw = card.crisis_contract[0]
    want = [raw.weekly_mission.total, raw.indicator_mission.total, raw.stage_mission.total]
    assert [m.total for m in contracts.current.missions] == want
    assert CONTRACT[number].render(contracts, {}).width == CONTRACT[number].W


@pytest.mark.parametrize("text", ["アーケイン", "아케인", "煙火邀星河"])
def test_cjk_falls_back(text):
    d = canvas_draw(Image.new("RGB", (10, 10)))
    f = font(30, "bold")
    from akef_cards.draw import _runs

    used = {run_font.path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for _, run_font in _runs(text, f)}
    assert used and all(name.startswith("NotoSans") for name in used)
    assert d.textlength(text, font=f) > 30 * len(text) * 0.6


def test_labels_follow_the_language():
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


async def test_cards_draw_in_another_language(profile, data, tmp_path):
    cards = akef_cards.Cards(data=data, images=akef_cards.ImageCache(tmp_path))
    data.locale = "de"
    try:
        image = await cards.render(profile.build("Si"))
    finally:
        data.locale = "en"
    assert image.size == (showcase.W, showcase.H)


@pytest.mark.parametrize("name", ["Abriegelungsartillerie", "Überschwänglicher Auslöser", "白けさせるない！胸中に成竹在り", "ใครก็ห้ามขัดจังหวะความสนุก"])
def test_skill_names_stay_in_their_column(name):
    d = canvas_draw(Image.new("RGB", (10, 10)))
    f = font(21, "semibold")
    lines = showcase._wrap(d, name, f, 130, 2)
    assert 1 <= len(lines) <= 2
    assert all(d.textlength(line, font=f) <= 130 for line in lines)


def test_untranslated_labels_keep_enka_names():
    with pytest.warns(UserWarning, match="aren't translated"):
        cards = akef_cards.Cards(lang="ja")
    assert cards.data.locale == "ja"


def test_unknown_language_falls_back_to_english():
    with pytest.warns(UserWarning, match="not supported"):
        cards = akef_cards.Cards(lang="klingon")
    assert cards.data.locale == "en"


def test_roster_card():
    from akef_cards.sources.skport import roster_from_skport
    from akef_cards.templates import roster_board

    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    roster = roster_from_skport(card)
    assert len(roster.operators) == len(card.chars)
    assert all(0 <= op.progress <= 1 for op in roster.operators)
    assert roster_board.render(roster, {}).width == roster_board.W


def test_wiki_card():
    from akef_cards.templates import wiki_board

    doc = {"blockIds": ["a", "b"], "blockMap": {"a": {"text": {"inlineElements": [{"text": {"text": "\"Quote.\""}}]}},
                                                 "b": {"text": {"inlineElements": [{"text": {"text": "Bio."}}]}}}}
    item = akef.WikiItem.model_validate({
        "itemId": "1", "name": "Arcane", "brief": {"description": doc},
        "document": {"documentMap": {"d": doc},
                     "chapterGroup": [{"title": "Ability Matrix", "widgets": [{"id": "w", "title": "//Combat Skills"}]}],
                     "widgetCommonMap": {"w": {"tableList": [{"label": "Codename", "value": "Arcane"}, {"label": "Race", "value": "Liberi"}],
                                               "tabList": [], "tabDataMap": {"t": {"intro": {"name": "Gloompurge (Array Arcana: INT)", "type": "Ultimate", "description": "d"}}}}}},
    })
    page = wiki_page(item)
    assert (page.quote, page.bio, page.info) == ("Quote.", "Bio.", [("Race", "Liberi")])
    assert page.skills[0].name == "Gloompurge"
    assert wiki_board.render(page, {}).width == wiki_board.W


async def test_wiki_pages_render(tmp_path):
    from akef.wiki import Cost, Intel, Node, Potential, Story, Tier, WikiPage, WikiPart, WikiSkill

    page = WikiPage("Arcane", "", "Quote.", "Bio.", [("Race", "Liberi")],
                    skills=[WikiSkill("Gloompurge", "Ultimate", "", "ULTIMATE:\nBoom.")],
                    talents=[Node("Keen Mind", "Talent", "", [Tier("Keen Mind 1", "INT +8", "E1", [Cost("T-Creds", "", 1000)])])],
                    promotions=[Node("Promotion I", "Elite", "", [Tier("Promotion I", "Cap 40", "Lv 20", [])])],
                    potentials=[Potential("Watcher", "", "Stronger.")],
                    intel=[Intel("Faction", "HAS", ""), Intel("Expertise", "Formation", "Three as one.")],
                    stories=[Story("File 1", "Reach trust: Close", "A long story.")])
    cards = akef_cards.Cards(images=akef_cards.ImageCache(tmp_path))
    assert page.parts == list(WikiPart)
    assert len(await cards.render_wiki_pages(page)) == 6
    assert len(await cards.render_wiki_pages(page, [WikiPart.SKILLS, "lore"])) == 2
    assert WikiPart.TALENTS.needs_index and not WikiPart.LORE.needs_index
    with pytest.raises(ValueError):
        await cards.render_wiki(page, "nope")


@pytest.mark.parametrize("template", [2])
async def test_other_templates_render_offline(profile, template):
    from akef_cards.templates import TEMPLATES

    image = TEMPLATES[template](profile.build("Si"), {})
    assert image.width > 1900 and image.height >= 1200
    bare = profile.build("Arcane")
    bare.stats, bare.gear, bare.weapon, bare.talents = None, [], None, []
    TEMPLATES[template](bare, {})


async def test_compare_renders_offline(profile):
    from akef_cards.templates import compare

    a, b = profile.build("Si"), profile.build("Si")
    image = compare.render(a, b, {})
    assert image.width == compare.W and 1000 < image.height < 1800
    b.stats = None
    compare.render(a, b, {}, hide_uid=True)


@pytest.mark.parametrize("template", [2])
async def test_compare_styles_render_offline(profile, template):
    from akef_cards.templates import COMPARE

    a, b = profile.build("Si"), profile.build("Si")
    assert COMPARE[template](a, b, {}).height < 1300
    b.stats, b.gear = None, []
    COMPARE[template](a, b, {}, hide_uid=True)


def test_untranslated_labels_fall_back_to_english_and_log(caplog):
    from akef_cards import i18n

    token = i18n.language.set("de")
    try:
        with caplog.at_level("WARNING", logger="akef_cards"):
            assert i18n.t("Talents 12/12") == "Talents 12/12"
            assert i18n.t("HP") != "HP"
    finally:
        i18n.language.reset(token)
    assert any("Talents {}" in r.getMessage() for r in caplog.records)


def test_image_cache_trims_the_least_recently_used(tmp_path):
    import os
    import time

    from akef_cards.images import ImageCache

    cache = ImageCache(tmp_path, max_mb=0.003)
    urls = [f"https://example.com/{i}.png" for i in range(4)]
    now = time.time()
    for i, url in enumerate(urls):
        cache._file(url).write_bytes(b"x" * 1024)
        os.utime(cache._file(url), (now - 100 + i, now - 100 + i))
    os.utime(cache._file(urls[0]), (now, now))
    cache.trim(keep=[urls[1]])
    left = {u for u in urls if cache._file(u).exists()}
    assert left == {urls[0], urls[1], urls[3]}
    assert cache.size() <= 3 * 1024


async def test_image_cache_keys_by_file_name(tmp_path):
    from akef_cards.images import ImageCache

    cache = ImageCache(tmp_path)
    Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(cache._file("https://a.example/20260101/abc123.png"), "PNG")
    got = await cache.get(["https://b.example/20261105/abc123.png?expires=1"])
    assert list(got) == ["https://b.example/20261105/abc123.png?expires=1"]


async def test_art_that_wont_download_says_what_to_do():
    from akef_cards.images import load_art

    with pytest.raises(akef_cards.CardError, match="pass the bytes"):
        await load_art("http://127.0.0.1:9/art.png")


def test_detail_cards_render_offline():
    from akef_cards.sources.skport import contract_detail_from_skport, monument_from_skport
    from akef_cards.templates import contract_detail, monument_event

    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    raw = json.loads((DATA / "indie_hard.json").read_text(encoding="utf-8"))["data"]["indieHard"]
    mon = monument_from_skport(card, akef.IndieHard.model_validate(raw))
    for draw in monument_event.TEMPLATES.values():
        assert draw(mon, monument_event.latest(mon), {}).width == monument_event.W
    detail = contract_detail_from_skport(card, akef.ContractDetail.model_validate(
        json.loads((DATA / "crisis_contract.json").read_text(encoding="utf-8"))["crisisContract"]))
    assert detail.best and len(detail.best.team) == 4 and detail.buffs and detail.foes
    for draw in contract_detail.TEMPLATES.values():
        assert draw(detail, {}).width == contract_detail.W


def test_hidden_blurs_the_uid_digits():
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


def test_wiki_cards_have_a_dark_style():
    from akef_cards.templates import wiki_board

    assert wiki_board.LIGHT["bg"] != wiki_board.DARK["bg"]
    assert wiki_board.P is wiki_board.LIGHT


async def test_render_bytes_takes_every_card(tmp_path):
    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    cards = akef_cards.Cards(images=akef_cards.ImageCache(tmp_path))
    live = await cards.render_bytes(cards.skport_live(card))
    assert live.name == "live.png" and live.read(4)[1:] == b"PNG"
    roster = await cards.render_bytes(cards.skport_roster(card), format="JPEG")
    assert roster.name == "roster.jpeg"
    pages = await cards.render_bytes(cards.skport_player(card), grid="4x2")
    assert isinstance(pages, list) and pages[0].name == "profile1.png"
    with pytest.raises(TypeError):
        await cards.render_bytes("nope")
