import json

import pytest

import akef
import akef_cards

from tests.helpers import DATA, skport_card


def test_live_card():
    from akef_cards.sources.skport import live_from_skport
    from akef_cards.templates import LIVE

    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    live = live_from_skport(card)
    assert live.sanity.total > 0 and len(live.meters) == 4
    for draw in LIVE.values():
        assert draw(live, {}).size == (1600, 1000)


def test_monument():
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
def test_factory(number):
    from akef_cards.sources.skport import factory_from_skport
    from akef_cards.templates import FACTORY

    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    factory = factory_from_skport(card)
    assert [r.name for r in factory.regions] == ["Valley IV", "Wuling"]
    assert len(factory.regions[0].posts) == 3
    assert FACTORY[number](factory, {}).width == 1600


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


def test_roster_card():
    from akef_cards.sources.skport import roster_from_skport
    from akef_cards.templates import roster_board

    card = akef.Card.model_validate(json.loads((DATA / "card_detail.json").read_text(encoding="utf-8"))["data"]["detail"])
    roster = roster_from_skport(card)
    assert len(roster.operators) == len(card.chars)
    assert all(0 <= op.progress <= 1 for op in roster.operators)
    assert roster_board.render(roster, {}).width == roster_board.W


def test_detail_cards():
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


def test_exploration_kinds():
    from akef_cards.exploration import counted, missing, percent

    e = akef_cards.Cards().skport_exploration(skport_card())
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

    real = akef_cards.Cards().skport_exploration(skport_card())
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


async def test_exploration_client():
    cards = akef_cards.Cards()

    async def no_images(urls):
        return {}

    cards.images.get = no_images
    e = cards.skport_exploration(skport_card())
    plain, hidden = await cards.render_exploration(e), await cards.render_exploration(e, hidden=True)
    assert plain.tobytes() != hidden.tobytes()
    assert (await cards.render_bytes(e, template=3)).name == "exploration.png"
    with pytest.raises(ValueError):
        await cards.render_exploration(e, template=9)
