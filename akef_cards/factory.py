from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Post:
    name: str
    level: int
    maxed: bool
    exp: int
    exp_next: int
    stock: int
    stock_max: int
    officer: str = ""

    @property
    def stock_share(self) -> float:
        return min(1.0, self.stock / self.stock_max) if self.stock_max else 0.0

    @property
    def exp_share(self) -> float:
        return 1.0 if self.maxed else (min(1.0, self.exp / self.exp_next) if self.exp_next else 0.0)


@dataclass
class Area:
    name: str
    found: int
    total: int
    kinds: list[tuple[int, int]] = field(default_factory=list)

    @property
    def share(self) -> float:
        return min(1.0, self.found / self.total) if self.total else 0.0


@dataclass
class Region:
    name: str
    level: int
    stock: int
    stock_max: int
    posts: list[Post] = field(default_factory=list)
    areas: list[Area] = field(default_factory=list)

    @property
    def explored(self) -> float:
        total = sum(a.total for a in self.areas)
        return sum(a.found for a in self.areas) / total if total else 0.0

    @property
    def stock_share(self) -> float:
        return min(1.0, self.stock / self.stock_max) if self.stock_max else 0.0


@dataclass
class Cabin:
    kind: int
    level: int
    crew: list[str] = field(default_factory=list)
    name: str = "Cabin"


@dataclass
class Factory:
    name: str
    uid: str
    level: int
    server: str
    avatar: str
    regions: list[Region]
    cabins: list[Cabin] = field(default_factory=list)
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def urls(self) -> list[str]:
        out = [self.avatar] + [p.officer for r in self.regions for p in r.posts]
        out += [a for c in self.cabins for a in c.crew]
        return [u for u in out if u]


def money(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M".replace(".00M", "M")
    if value >= 10_000:
        return f"{value / 1000:.1f}K".replace(".0K", "K")
    return f"{value:,}"
