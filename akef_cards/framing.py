import json
from pathlib import Path

# enka splashes are 2048x2048 scenes with the operator somewhere in them.
# the part we show: (center x, top, bottom), 0 to 1
SPLASH_FOCUS = (0.5, 0.12, 1.0)
# profile tiles: face x and y (0 to 1) and crop width relative to height
FACES = json.loads((Path(__file__).parent / "data" / "faces.json").read_text(encoding="utf-8"))
GENERAL_CROP = (0.5, 0.25, 0.42)
GRIDS = {"4x2": (4, 2), "3x3": (3, 3)}


def splash_focus(build) -> tuple[float, float, float] | None:
    return SPLASH_FOCUS if build.source == "enka" else None


def tile_crop(op) -> tuple[float, float, float] | None:
    if "enka.network" not in op.portrait:
        return None
    return tuple(FACES.get(op.id, GENERAL_CROP))


def pages(player, grid: str = "4x2") -> list:
    if grid not in GRIDS:
        raise ValueError(f"grid should be one of {sorted(GRIDS)}")
    cols, rows = GRIDS[grid]
    per = cols * rows
    return [player.roster[i:i + per] for i in range(0, len(player.roster), per)] or [[]]
