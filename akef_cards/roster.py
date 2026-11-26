from dataclasses import dataclass, field
from datetime import datetime, timezone

MAX_LEVEL, MAX_PROMOTION, MAX_SKILL, MAX_GEAR = 90, 4, 12, 70


@dataclass
class Trained:
    name: str
    rarity: int
    element: str
    element_icon: str
    portrait: str
    level: int
    promotion: int
    potential: int
    skills: list[int]
    talents: tuple[int, int]
    weapon: str = ""
    weapon_icon: str = ""
    weapon_rarity: int = 0
    weapon_level: int = 0
    weapon_refine: int = 0
    essence: str = ""
    essence_rarity: int = 0
    gear: list[tuple[str, int, int]] = field(default_factory=list)

    @property
    def progress(self) -> float:
        parts = [
            self.level / MAX_LEVEL,
            self.promotion / MAX_PROMOTION,
            sum(self.skills) / (MAX_SKILL * len(self.skills)) if self.skills else 0,
            self.weapon_level / MAX_LEVEL,
            sum(level for _, level, _ in self.gear) / (MAX_GEAR * 4),
        ]
        return min(1.0, sum(parts) / len(parts))


@dataclass
class Roster:
    name: str
    uid: str
    level: int
    region: str
    avatar: str
    operators: list[Trained]
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def maxed(self) -> int:
        return sum(op.progress >= 0.999 for op in self.operators)

    def urls(self) -> list[str]:
        out = [self.avatar]
        for op in self.operators:
            out += [op.portrait, op.element_icon, op.weapon_icon] + [icon for icon, _, _ in op.gear]
        return [u for u in out if u]
