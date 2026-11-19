from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Meter:
    label: str
    current: int
    total: int
    note: str = ""

    @property
    def share(self) -> float:
        return min(1.0, self.current / self.total) if self.total else 0.0

    @property
    def done(self) -> bool:
        return self.total > 0 and self.current >= self.total


@dataclass
class Echoes:
    season: str
    cycle: str
    stars: int
    stages: list[tuple[str, int]] = field(default_factory=list)
    ends: datetime | None = None


@dataclass
class Contract:
    name: str
    best: int
    weekly: Meter
    ends: datetime | None = None
    art: str = ""


@dataclass
class Live:
    name: str
    uid: str
    level: int
    region: str
    avatar: str
    sanity: Meter
    full_at: datetime | None
    meters: list[Meter]
    echoes: Echoes | None = None
    contract: Contract | None = None
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def urls(self) -> list[str]:
        return [u for u in (self.avatar, self.contract.art if self.contract else "") if u]


def until(when: datetime | None, now: datetime) -> str:
    if when is None:
        return ""
    seconds = int((when - now).total_seconds())
    if seconds <= 0:
        return "now"
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    if days:
        return f"{days}d {hours}h"
    return f"{hours}h {rest // 60:02d}m" if hours else f"{rest // 60}m"
