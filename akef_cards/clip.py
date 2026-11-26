from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

from PIL import Image

from akef_cards import animate
from akef_cards.errors import CardError


@dataclass(frozen=True)
class AnimationInfo:
    width: int
    height: int
    frames: int
    duration: float
    fit: str


@dataclass(frozen=True, eq=False)
class AnimatedCard:

    frames: tuple[Image.Image, ...] = field(repr=False)
    times: tuple[int, ...] = field(repr=False)
    run: Callable = field(repr=False)
    loop: int = 0
    width: int | None = None

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def duration(self) -> float:
        return sum(self.times) / 1000

    @property
    def size(self) -> tuple[int, int]:
        w, h = self.frames[0].size
        if not self.width or self.width >= w:
            return w, h
        return self.width, round(h * self.width / w)

    def _with(self, frames, times) -> AnimatedCard:
        if len(frames) < 2:
            raise ValueError("that leaves less than 2 frames")
        return replace(self, frames=tuple(frames), times=tuple(times))

    def trim(self, start: float = 0, end: float | None = None) -> AnimatedCard:
        first = round(start * 1000)
        last = sum(self.times) if end is None else min(round(end * 1000), sum(self.times))
        if last <= first:
            raise ValueError("trim: end has to be after start")
        frames, times, clock = [], [], 0
        for frame, took in zip(self.frames, self.times):
            part = min(clock + took, last) - max(clock, first)
            if part > 0:
                frames.append(frame)
                times.append(part)
            clock += took
        return self._with(frames, times)

    def speed(self, factor: float) -> AnimatedCard:
        if factor <= 0:
            raise ValueError("speed has to be above 0")
        return self._with(self.frames, [max(1, round(t / factor)) for t in self.times])

    def reverse(self) -> AnimatedCard:
        return self._with(self.frames[::-1], self.times[::-1])

    def bounce(self) -> AnimatedCard:
        return self._with(self.frames + self.frames[-2:0:-1], self.times + self.times[-2:0:-1])

    def hold(self, seconds: float, at: str = "end") -> AnimatedCard:
        times = list(self.times)
        times[0 if at == "start" else -1] += round(seconds * 1000)
        return self._with(self.frames, times)

    def loops(self, count: int) -> AnimatedCard:
        return replace(self, loop=count)

    def resize(self, width: int) -> AnimatedCard:
        return replace(self, width=width)

    def still(self, at: float = 0) -> Image.Image:
        clock = 0
        for frame, took in zip(self.frames, self.times):
            clock += took
            if at * 1000 < clock:
                break
        return frame.copy() if frame.size == self.size else frame.resize(self.size, Image.LANCZOS)

    def _halved(self) -> AnimatedCard:
        frames = self.frames[::2]
        times = [sum(self.times[i:i + 2]) for i in range(0, self.frame_count, 2)]
        return self._with(frames, times)

    def _encode(self, format: str, quality: int) -> bytes:
        frames = self.frames
        if frames[0].size != self.size:
            frames = [f.resize(self.size, Image.LANCZOS) for f in frames]
        return animate.encode(list(frames), list(self.times), format, quality, self.loop)

    async def to_bytes(self, format: str = "WEBP", quality: int = 80) -> io.BytesIO:
        format = format.upper()
        if format not in animate.FORMATS:
            raise ValueError(f"format has to be one of {animate.FORMATS}")
        return _file(await self.run(self._encode, format, quality), format)

    async def save(self, path: str | Path, quality: int = 80) -> Path:
        path = Path(path)
        data = await self.to_bytes(path.suffix.lstrip("."), quality)
        await self.run(path.write_bytes, data.getvalue())
        return path

    def _smaller(self, format: str, min_width: int):
        card, quality = self, 80
        yield card, quality
        if format == "WEBP":
            quality = 70
            yield card, quality
        if card.frame_count >= 16:
            card = card._halved()
            yield card, quality
        width = card.size[0]
        while width > min_width:
            width = max(min_width, int(width * 0.85))
            card = card.resize(width)
            yield card, quality
        if card.frame_count >= 16:
            yield card._halved(), quality

    async def fit_under(self, max_mb: float, format: str = "WEBP", min_width: int = 500) -> io.BytesIO:
        format = format.upper()
        best = None
        for card, quality in self._smaller(format, min_width):
            data = await card.to_bytes(format, quality)
            size = len(data.getvalue())
            best = size if best is None else min(best, size)
            if size <= max_mb * 1_000_000:
                data.settings = {"width": card.size[0], "frames": card.frame_count, "quality": quality}
                return data
        raise CardError(f"couldn't get it under {max_mb} MB, smallest was {best / 1_000_000:.2f} MB. "
                        "trim() it or lower min_width")


def _file(data: bytes, format: str) -> io.BytesIO:
    out = io.BytesIO(data)
    out.name = f"card.{format.lower()}"
    return out
