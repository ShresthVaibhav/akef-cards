from dataclasses import dataclass

from akef_cards.factory import Region

KINDS = ("Puzzles", "Chests", "Gear Chests", "Fragments", "Blackboxes", "Aurylenes")


def share(found: int, total: int) -> float:
    return min(1.0, found / total) if total else 0.0


def counted(n: int, kind: str) -> str:
    if n == 1:
        kind = "Blackbox" if kind == "Blackboxes" else kind[:-1]
    return f"{n} {kind}"


def percent(found: int, total: int) -> str:
    if not total:
        return "-"
    return f"{int(share(found, total) * 100)}%"


@dataclass
class Exploration:
    name: str
    uid: str
    level: int
    server: str
    avatar: str
    regions: list[Region]

    @property
    def areas(self) -> list:
        return [a for r in self.regions for a in r.areas]

    @property
    def found(self) -> int:
        return sum(min(a.found, a.total) for a in self.areas)

    @property
    def total(self) -> int:
        return sum(a.total for a in self.areas)

    def kind_totals(self) -> list[tuple[str, int, int]]:
        out = []
        for i, label in enumerate(KINDS):
            counts = [a.kinds[i] for a in self.areas if a.kinds]
            out.append((label, sum(min(f, t) for f, t in counts), sum(t for _, t in counts)))
        return out

    def urls(self) -> list[str]:
        return [self.avatar] if self.avatar else []


def missing(area) -> list[tuple[str, int]]:
    return [(label, total - found) for label, (found, total) in zip(KINDS, area.kinds) if total > found]


def done(area) -> bool:
    return area.found >= area.total
