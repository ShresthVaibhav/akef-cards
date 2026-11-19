from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Member:
    avatar: str
    element: str
    rarity: int
    level: int
    name: str = ""
    art: str = ""
    profession: str = ""
    potential: int = 0
    element_icon: str = ""

    @property
    def portrait(self) -> str:
        return self.avatar


@dataclass
class Clear:
    seconds: int
    when: datetime | None
    team: list[Member] = field(default_factory=list)


@dataclass
class Stage:
    name: str
    level: int
    enemy: str = ""
    normal: Clear | None = None
    agony: Clear | None = None
    normal_done: bool = False
    agony_done: bool = False


@dataclass
class Event:
    name: str
    art: str
    stages: list[Stage]
    rules: list[str] = field(default_factory=list)
    medal: str = ""
    medal_level: int = 0
    plated: bool = False
    running: bool = False
    started: datetime | None = None

    @property
    def cleared(self) -> tuple[int, int]:
        return sum(s.normal_done for s in self.stages), sum(s.agony_done for s in self.stages)

    @property
    def fastest(self) -> Clear | None:
        clears = [c for s in self.stages for c in (s.normal, s.agony) if c and c.seconds]
        return min(clears, key=lambda c: c.seconds) if clears else None


@dataclass
class Monument:
    name: str
    uid: str
    level: int
    region: str
    avatar: str
    events: list[Event]
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def event(self, name_or_index) -> Event:
        if isinstance(name_or_index, int):
            return self.events[name_or_index]
        wanted = name_or_index.casefold()
        found = next((e for e in self.events if e.name.casefold() == wanted), None)
        if found is None:
            found = next((e for e in self.events if wanted in e.name.casefold()), None)
        if found is None:
            raise KeyError(f"no monument event called {name_or_index!r}")
        return found

    def urls(self, event: Event | None = None) -> list[str]:
        out = [self.avatar]
        for e in [event] if event else self.events:
            out += [e.art, e.medal]
            if event:
                for s in e.stages:
                    out.append(s.enemy)
                    for c in (s.normal, s.agony):
                        out += [u for m in c.team for u in (m.avatar, m.art, m.element_icon)] if c else []
        return list(dict.fromkeys(u for u in out if u))


def clock(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}:{seconds:02d}" if minutes else f"{seconds}s"
