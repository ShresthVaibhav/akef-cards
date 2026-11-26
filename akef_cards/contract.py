from dataclasses import dataclass, field
from datetime import datetime, timezone

from akef_cards.live import Meter


@dataclass
class Contract:
    name: str
    best: int
    attempts: int
    art: str
    missions: list[Meter]
    medal: str = ""
    medal_level: int = 0
    plated: bool = False
    starts: datetime | None = None
    ends: datetime | None = None


@dataclass
class Contracts:
    name: str
    uid: str
    level: int
    region: str
    avatar: str
    current: Contract | None
    past: list[Contract] = field(default_factory=list)
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def urls(self) -> list[str]:
        out = [self.avatar]
        for c in ([self.current] if self.current else []) + self.past:
            out += [c.art, c.medal]
        return [u for u in out if u]


@dataclass
class Fighter:
    name: str
    portrait: str
    art: str = ""
    element: str = ""
    element_icon: str = ""
    profession: str = ""
    rarity: int = 0
    level: int = 0
    potential: int = 0


@dataclass
class Run:
    team: list[Fighter]
    seconds: int
    waves: int
    score: int
    cleared: bool
    best: bool = False
    when: datetime | None = None


@dataclass
class Buff:
    name: str
    icon: str
    text: str
    score: int
    unlocked: bool = True

    @property
    def kind(self) -> str:
        return self.name.split(":", 1)[0].strip() if ":" in self.name else ""

    @property
    def short(self) -> str:
        return self.name.split(":", 1)[-1].strip()


@dataclass
class Foe:
    name: str
    icon: str
    level: int = 0
    ability: str = ""


@dataclass
class ContractDetail:
    name: str
    uid: str
    level: int
    region: str
    avatar: str
    contract: Contract
    runs: list[Run] = field(default_factory=list)
    buffs: list[Buff] = field(default_factory=list)
    foes: list[Foe] = field(default_factory=list)
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def best(self) -> Run | None:
        return next((r for r in self.runs if r.best), max(self.runs, key=lambda r: r.score, default=None))

    def urls(self) -> list[str]:
        out = [self.avatar, self.contract.art, self.contract.medal]
        for r in self.runs:
            out += [f.portrait for f in r.team] + [f.art for f in r.team] + [f.element_icon for f in r.team]
        out += [b.icon for b in self.buffs] + [f.icon for f in self.foes]
        return list(dict.fromkeys(u for u in out if u))
