import json
from pathlib import Path

import pytest

import akef
import akef_cards
from akef_cards.framing import pages, tile_crop
from akef.enka import player_from_skport

from tests.helpers import DATA


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
async def test_profile_templates(profile, number, grid):
    from akef_cards.templates import PROFILES

    template = PROFILES[number]
    image = template.render(profile.player, {}, grid=grid)
    assert image.width == template.WIDTH[grid]
    with pytest.raises(ValueError):
        template.render(profile.player, {}, grid="5x5")


async def test_enka_tiles(profile):
    si = profile.player.roster[0]
    assert "/ui/ef/splash/" in si.portrait
    assert tile_crop(si) == tuple(json.loads((Path(akef_cards.__file__).parent / "data" / "faces.json").read_text())["chr_0036_jsspsi"])
