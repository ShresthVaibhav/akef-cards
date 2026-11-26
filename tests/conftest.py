import json
import shutil

import pytest

from akef.enka import GameData, profile_from_enka

from tests.helpers import DATA


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
