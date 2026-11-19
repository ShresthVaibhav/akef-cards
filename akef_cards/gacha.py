from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Hit:
    name: str
    icon: str
    rarity: int
    pity: int
    hard: int
    banner: str
    when: datetime | None
    element: str = ""
    portrait: str = ""

    @property
    def luck(self) -> float:
        return self.pity / self.hard if self.hard else 0.0


@dataclass
class Track:
    name: str
    banner: str
    since: int
    hard: int
    banner_pulls: int = 0
    featured_at: int = 0


@dataclass
class PullHistory:
    name: str
    uid: str
    level: int
    region: str
    avatar: str
    tracks: list[Track]
    operators: list[Hit]
    weapons: list[Hit]
    total: int
    free: int
    weapon_total: int
    fives: int
    weapon_fives: int
    after: datetime | None = None
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def average(self) -> float:
        paid = self.total - self.free
        return paid / len(self.operators) if self.operators else 0.0

    def urls(self) -> list[str]:
        out = [self.avatar] + [h.icon for h in self.operators + self.weapons] + [h.portrait for h in self.operators[:1]]
        return [u for u in out if u]
