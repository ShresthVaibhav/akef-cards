import asyncio
import io
import json
import os
import shutil
import threading
import time
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


async def test_art_that_wont_download_says_what_to_do(monkeypatch):
    from akef_cards import images

    monkeypatch.setattr(images, "_is_public", lambda host: True)
    with pytest.raises(akef_cards.CardError, match="pass the bytes"):
        await images.load_art("http://127.0.0.1:9/art.png", allow_remote=True)


async def test_art_strings_need_an_opt_in(tmp_path):
    from akef_cards.images import load_art

    file = tmp_path / "art.png"
    Image.new("RGBA", (4, 4)).save(file)
    with pytest.raises(akef_cards.CardError, match="allow_local"):
        await load_art(str(file))
    with pytest.raises(akef_cards.CardError, match="allow_remote"):
        await load_art("HTTPS://example.com/art.png")
    with pytest.raises(akef_cards.CardError, match="allow_local"):
        await load_art(str(file), allow_remote=True)
    for art in (file, file.read_bytes()):
        assert (await load_art(art)).size == (4, 4)
    assert (await load_art(str(file), allow_local=True)).size == (4, 4)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/a.png", "http://localhost/a.png", "http://2130706433/a.png", "http://10.0.0.1/a.png",
    "http://192.168.1.1/a.png", "http://169.254.169.254/latest", "http://0.0.0.0/a.png",
    "http://[::1]/a.png", "http://[::ffff:127.0.0.1]/a.png",
])
async def test_art_url_cant_reach_private_addresses(url):
    from akef_cards.images import load_art

    with pytest.raises(akef_cards.CardError, match="private address|InvalidUrl"):
        await load_art(url, allow_remote=True)


async def test_art_download_checks_redirects_and_size(monkeypatch):
    from aiohttp import web
    from akef_cards import images

    async def hop(request):
        raise web.HTTPFound("http://10.0.0.1/secret.png")

    async def loop(request):
        raise web.HTTPFound("/loop")

    async def huge(request):
        return web.Response(body=b"x" * 2048)

    async def text(request):
        return web.Response(body=b"not a pic")

    app = web.Application()
    for route in (hop, loop, huge, text):
        app.router.add_get(f"/{route.__name__}", route)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 0).start()
    base = f"http://127.0.0.1:{runner.addresses[0][1]}"
    real = images._is_public
    monkeypatch.setattr(images, "_is_public", lambda host: host == "127.0.0.1" or real(host))
    monkeypatch.setattr(images, "MAX_ART_BYTES", 1024)
    try:
        for path, error in (("hop", "private address"), ("loop", "too many times"), ("huge", "too big"),
                            ("text", "is it an image")):
            with pytest.raises(akef_cards.CardError, match=error):
                await images.load_art(f"{base}/{path}", allow_remote=True)
    finally:
        await runner.cleanup()


async def test_custom_art_cards_arent_cached(profile, tmp_path):
    file = tmp_path / "art.png"
    Image.new("RGBA", (600, 900), (200, 80, 80, 255)).save(file)
    cards = akef_cards.Cards(images=akef_cards.ImageCache(tmp_path / "cache"))

    async def blank_images(urls):
        return {u: Image.new("RGBA", (64, 64)) for u in urls if u}

    cards.images.get = blank_images
    build = profile.build("Si")
    old = await cards.render(build, art=str(file), allow_local=True)
    Image.new("RGBA", (600, 900), (80, 80, 200, 255)).save(file)
    new = await cards.render(build, art=str(file), allow_local=True)
    assert old.tobytes() != new.tobytes()
    with pytest.raises(akef_cards.CardError, match="allow_local"):
        await cards.render(build, art=str(file))

    assert not cards._drawn._data
    await cards.render(build)
    assert len(cards._drawn._data) == 1


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


async def test_render_bytes_jpeg_and_wiki(profile, tmp_path):
    from akef.wiki import WikiPage, WikiSkill

    cards = akef_cards.Cards(images=akef_cards.ImageCache(tmp_path))
    for fmt in ("JPEG", "jpg"):
        file = await cards.render_bytes(profile.build("Si"), format=fmt)
        assert file.read(3) == b"\xff\xd8\xff"
    page = WikiPage("Arcane", "", "Quote.", "Bio.", [("Race", "Liberi")],
                    skills=[WikiSkill("Gloompurge", "Ultimate", "", "Boom.")])
    files = await cards.render_bytes(page, format="JPEG")
    assert len(files) == len(page.parts) and files[0].name == "wiki1.jpeg"


async def _pic_server(handler):
    from aiohttp import web

    app = web.Application()
    app.router.add_get("/{name}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 0).start()
    return runner, f"http://127.0.0.1:{runner.addresses[0][1]}"


def _png():
    out = io.BytesIO()
    Image.new("RGBA", (8, 8), (1, 2, 3, 255)).save(out, format="PNG")
    return out.getvalue()


async def test_same_image_downloads_once(tmp_path):
    from aiohttp import web

    hits, gate = [], asyncio.Event()

    async def pic(request):
        hits.append(request.path)
        await gate.wait()
        return web.Response(body=_png())

    runner, base = await _pic_server(pic)
    cache = akef_cards.ImageCache(tmp_path)
    url = f"{base}/a.png"
    try:
        tasks = [asyncio.create_task(cache.get([url])) for _ in range(20)]
        while not hits:
            await asyncio.sleep(0.01)
        tasks[0].cancel()
        await asyncio.sleep(0.01)
        gate.set()
        done = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await runner.cleanup()
    assert isinstance(done[0], asyncio.CancelledError)
    assert all(url in got for got in done[1:])
    assert hits == ["/a.png"]
    assert not cache._loading and cache._session is None
    assert [f.name for f in tmp_path.iterdir()] == ["a.png.img"]


async def test_failed_download_gets_retried(tmp_path):
    from aiohttp import web

    hits = []

    async def flaky(request):
        hits.append(1)
        return web.Response(status=500) if len(hits) == 1 else web.Response(body=_png())

    runner, base = await _pic_server(flaky)
    cache = akef_cards.ImageCache(tmp_path)
    try:
        assert await cache.get([f"{base}/a.png"]) == {}
        assert len(await cache.get([f"{base}/a.png"])) == 1
    finally:
        await runner.cleanup()


def test_failed_save_leaves_the_old_file(tmp_path, monkeypatch):
    cache = akef_cards.ImageCache(tmp_path)
    file = tmp_path / "a.img"
    cache._save(file, b"old")

    def nope(*args):
        raise PermissionError

    monkeypatch.setattr("os.replace", nope)
    cache._save(file, b"new")
    assert file.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [file]


def test_cleanup_survives_vanishing_files(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    cache = akef_cards.ImageCache(tmp_path, max_mb=0)
    for i in range(300):
        (tmp_path / f"{i}.img").write_bytes(b"x" * 100)
    real = Path.glob
    monkeypatch.setattr(Path, "glob", lambda self, p: [*real(self, p), self / "ghost.img"])
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda _: (cache.trim(), cache.size()), range(16)))
    monkeypatch.undo()
    assert not list(tmp_path.glob("*.img"))


@pytest.mark.parametrize("limit, most", [(None, 6), (1, 1), (2, 2)])
async def test_render_limit(limit, most):
    cards = akef_cards.Cards(max_renders=limit)
    lock, running, peak = threading.Lock(), [0], [0]

    def slow(images):
        with lock:
            running[0] += 1
            peak[0] = max(peak[0], running[0])
        time.sleep(0.15)
        with lock:
            running[0] -= 1
        return Image.new("RGBA", (1, 1))

    await asyncio.gather(*(cards._draw(None, [], slow) for _ in range(6)))
    assert peak[0] == most


async def test_cancelled_render_keeps_its_slot_till_done():
    cards = akef_cards.Cards(max_renders=1)
    started, finish, order = threading.Event(), threading.Event(), []

    def first(images):
        started.set()
        finish.wait(5)
        order.append("first")
        return Image.new("RGBA", (1, 1))

    def second(images):
        order.append("second")
        return Image.new("RGBA", (1, 1))

    one = asyncio.create_task(cards._draw(None, [], first))
    assert await asyncio.to_thread(started.wait, 5)
    one.cancel()
    two = asyncio.create_task(cards._draw(None, [], second))
    await asyncio.sleep(0.2)
    assert order == []
    finish.set()
    await two
    assert order == ["first", "second"]


def test_render_limit_has_to_be_positive():
    with pytest.raises(ValueError):
        akef_cards.Cards(max_renders=0)


async def test_disk_work_stays_off_the_main_loop(tmp_path, monkeypatch):
    from aiohttp import web

    async def pic(request):
        return web.Response(body=_png())

    main, calls = threading.get_ident(), []

    def watch(owner, name):
        real = getattr(owner, name)

        def spy(*args, **kwargs):
            calls.append((name, threading.get_ident() == main))
            return real(*args, **kwargs)

        monkeypatch.setattr(owner, name, spy)

    watch(Path, "read_bytes")
    watch(akef_cards.ImageCache, "_save")
    watch(os, "utime")
    runner, base = await _pic_server(pic)
    try:
        for _ in range(2):
            assert len(await akef_cards.ImageCache(tmp_path).get([f"{base}/a.png"])) == 1
    finally:
        await runner.cleanup()
    assert {name for name, _ in calls} == {"read_bytes", "_save", "utime"}
    assert not any(on_main for _, on_main in calls)


def _card():
    raw = json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))
    return akef.Card.model_validate(raw["data"]["detail"])


def test_exploration_keeps_each_kind():
    from akef_cards.exploration import counted, missing, percent

    e = akef_cards.Cards().skport_exploration(_card())
    assert e.areas and all(len(a.kinds) == 6 for a in e.areas)
    for a in e.areas:
        assert a.found == sum(f for f, _ in a.kinds) and a.total == sum(t for _, t in a.kinds)
        assert sum(n for _, n in missing(a)) == sum(max(0, t - f) for f, t in a.kinds)
    assert sum(t for _, _, t in e.kind_totals()) == e.total
    assert percent(999, 1000) == "99%" and percent(0, 0) == "-"
    assert [counted(1, "Chests"), counted(1, "Blackboxes"), counted(2, "Chests")] == ["1 Chest", "1 Blackbox", "2 Chests"]


@pytest.mark.parametrize("template", [1, 2, 3])
async def test_exploration_templates_render(template):
    from akef_cards.exploration import Exploration
    from akef_cards.factory import Area, Region
    from akef_cards.templates import EXPLORATION, exploration_boards

    real = akef_cards.Cards().skport_exploration(_card())
    huge = Area("A really long area name that goes on and on forever " * 2, 0, 600, [(0, 100)] * 6)
    clear = Area("Done", 6, 6, [(1, 1)] * 6)
    empty = Area("Nothing here", 0, 0, [(0, 0)] * 6)
    regions = [
        [],
        [Region("Empty", 1, 0, 0)],
        [Region("Mixed", 1, 0, 0, areas=[huge] * 9 + [clear, empty])],
        [Region("Done", 1, 0, 0, areas=[clear] * 30)] * 3,
    ]
    for e in [real] + [Exploration("x", "123456789", 1, "Asia", "", r) for r in regions]:
        image = EXPLORATION[template](e, {})
        assert image.width == exploration_boards.W and image.height > 200


async def test_exploration_through_the_client():
    cards = akef_cards.Cards()

    async def no_images(urls):
        return {}

    cards.images.get = no_images
    e = cards.skport_exploration(_card())
    plain, hidden = await cards.render_exploration(e), await cards.render_exploration(e, hidden=True)
    assert plain.tobytes() != hidden.tobytes()
    assert (await cards.render_bytes(e, template=3)).name == "exploration.png"
    with pytest.raises(ValueError):
        await cards.render_exploration(e, template=9)


def _moving(frames=6, size=(160, 90), format="GIF"):
    shots = [Image.new("RGB", size, (40 * i, 200 - 30 * i, 90)) for i in range(frames)]
    out = io.BytesIO()
    shots[0].save(out, format, save_all=True, append_images=shots[1:], duration=50, loop=0)
    return out.getvalue()


def test_animation_frames_keep_their_timing():
    from akef_cards.animate import read_frames

    for format in ("GIF", "WEBP"):
        frames, times = read_frames(_moving(format=format), frame_step=1)
        assert len(frames) == 6 and times == [50] * 6
        frames, times = read_frames(_moving(format=format))
        assert len(frames) == 3 and times == [100] * 3
    frames, times = read_frames(_moving(7))
    assert len(frames) == 4 and times == [100, 100, 100, 50]
    frames, times = read_frames(_moving(10), max_frames=4)
    assert len(frames) == 4 and sum(times) == 500
    for tiny in (2, 3):
        frames, times = read_frames(_moving(tiny), frame_step=10)
        assert len(frames) == 2 and sum(times) == tiny * 50


def test_still_or_broken_art_cant_be_animated(monkeypatch):
    from akef_cards import animate

    for bad, error in ((_png(), "doesnt move"), (b"nope", "couldn't read")):
        with pytest.raises(akef_cards.CardError, match=error):
            animate.read_frames(bad)
    monkeypatch.setattr(animate, "MAX_TOTAL_PIXELS", 1000)
    with pytest.raises(akef_cards.CardError, match="too big"):
        animate.read_frames(_moving())


@pytest.mark.parametrize("template", [1, 2])
async def test_two_render_trick_matches_a_real_render(profile, template):
    from PIL import ImageChops
    from akef_cards import animate

    build = profile.build("Liino")
    draw, _, span = animate.LAYOUTS[template]
    black, white, real = (draw(build, {}, art=Image.new("RGBA", (span, showcase.H), c))
                          for c in ((0, 0, 0, 255), (255, 255, 255, 255), (180, 60, 120, 255)))
    mixed = ImageChops.add(black, ImageChops.multiply(ImageChops.subtract(white, black),
                                                      Image.new("RGB", black.size, (180, 60, 120))))
    assert max(high for _, high in ImageChops.difference(mixed, real).getextrema()) <= 3


@pytest.mark.parametrize("template", [1, 2])
@pytest.mark.parametrize("format, how", [("WEBP", "contain"), ("GIF", "cover")])
async def test_render_animated(profile, template, format, how):
    cards = akef_cards.Cards()

    async def no_images(urls):
        return {}

    cards.images.get = no_images
    out = await cards.render_animated(profile.build("Si"), _moving(), template=template, format=format, fit=how,
                                      width=500)
    assert out.name == f"card.{format.lower()}"
    with Image.open(out) as img:
        assert img.format == format and img.n_frames == 3 and img.width == 500
    every = await cards.render_animated(profile.build("Si"), _moving(), template=template, frame_step=1, width=500)
    with Image.open(every) as img:
        assert img.n_frames == 6


async def test_animated_art_follows_the_same_rules(profile, tmp_path, monkeypatch):
    from akef_cards import images

    cards = akef_cards.Cards()
    build = profile.build("Si")
    file = tmp_path / "a.gif"
    file.write_bytes(_moving())
    with pytest.raises(akef_cards.CardError, match="allow_local"):
        await cards.render_animated(build, str(file))
    with pytest.raises(akef_cards.CardError, match="allow_remote"):
        await cards.render_animated(build, "https://example.com/a.gif")
    with pytest.raises(akef_cards.CardError, match="private address"):
        await cards.render_animated(build, "http://127.0.0.1/a.gif", allow_remote=True)
    monkeypatch.setattr(images, "MAX_ART_BYTES", 10)
    with pytest.raises(akef_cards.CardError, match="too big"):
        await cards.render_animated(build, file)
    for bad in ({"template": 3}, {"format": "MP4"}, {"fit": "stretch"}, {"width": 5}, {"frame_step": 0}):
        with pytest.raises(ValueError):
            await cards.render_animated(build, _moving(), **bad)


@pytest.mark.parametrize("format", ["GIF", "WEBP"])
def test_smaller_animations_still_look_right(format):
    from PIL import ImageChops
    from akef_cards.animate import _encode

    frames = []
    for x in (0, 40, 80, 0, 0, 120):
        frame = Image.new("RGB", (200, 80), (240, 238, 232))
        frame.paste((200, 40, 40), (x, 20, x + 30, 50))
        frames.append(frame)
    times = [40, 50, 60, 70, 80, 90]
    with Image.open(io.BytesIO(_encode(frames, times, format, 90))) as img:
        shown, clock = [], 0
        for i in range(img.n_frames):
            img.seek(i)
            got = img.convert("RGB")
            clock += img.info["duration"]
            shown.append((clock, got))
    assert clock == sum(times)
    start = 0
    for frame, took in zip(frames, times):
        got = next(g for end, g in shown if start + took / 2 < end)
        off = ImageChops.difference(frame, got).convert("L")
        assert sum(i * n for i, n in enumerate(off.histogram())) / (200 * 80) < 3
        start += took
