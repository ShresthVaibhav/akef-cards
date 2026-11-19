from __future__ import annotations

import asyncio
import io
import os
import re
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from PIL import Image

from akef_cards.errors import CardError

MAX_SIDE = 1800
DEFAULT_MB = 15


def default_path() -> Path:
    if os.environ.get("AKEF_CARDS_CACHE"):
        return Path(os.environ["AKEF_CARDS_CACHE"])
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(root) / "akef" / "images"


class ImageCache:
    def __init__(self, path: str | Path | None = None, *, timeout: float = 40, max_mb: float | None = DEFAULT_MB,
                 kept_in_memory: int = 200):
        self.path = Path(path) if path else default_path()
        self.max_bytes = None if max_mb is None else int(max_mb * 1024 * 1024)
        self.kept_in_memory = kept_in_memory
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._memory: OrderedDict[str, Image.Image] = OrderedDict()

    def _file(self, url: str) -> Path:
        return self.path / (name_of(url) + ".img")

    def _remember(self, url: str, img: Image.Image) -> None:
        key = name_of(url)
        self._memory[key] = img
        self._memory.move_to_end(key)
        while len(self._memory) > self.kept_in_memory:
            self._memory.popitem(last=False)

    def size(self) -> int:
        return sum(f.stat().st_size for f in self.path.glob("*.img")) if self.path.exists() else 0

    def trim(self, keep=()) -> None:
        if self.max_bytes is None or not self.path.exists():
            return
        keep = {self._file(u) for u in keep}
        files = sorted(self.path.glob("*.img"), key=lambda f: f.stat().st_mtime)
        total = sum(f.stat().st_size for f in files)
        for file in files:
            if total <= self.max_bytes:
                break
            if file in keep:
                continue
            total -= file.stat().st_size
            file.unlink(missing_ok=True)

    async def get(self, urls) -> dict[str, Image.Image]:
        wanted = {u for u in urls if u}
        out = {}
        for u in wanted:
            key = name_of(u)
            if key in self._memory:
                out[u] = self._memory[key]
                self._memory.move_to_end(key)
        on_disk, todo = [], []
        for url in wanted - out.keys():
            (on_disk if self._file(url).exists() else todo).append(url)

        async def read(url):
            file = self._file(url)
            try:
                img, small = await asyncio.to_thread(_decode, file.read_bytes())
            except OSError:
                todo.append(url)
                return
            if small is not None:
                file.write_bytes(small)
            else:
                os.utime(file)
            out[url] = img
            self._remember(url, img)

        await asyncio.gather(*(read(u) for u in on_disk))
        if not todo:
            await asyncio.to_thread(self.trim, wanted)
            return out

        self.path.mkdir(parents=True, exist_ok=True)
        async with aiohttp.ClientSession(timeout=self._timeout, headers={"User-Agent": "akef-cards"}) as session:
            async def one(url):
                try:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            return
                        data = await resp.read()
                    img, small = await asyncio.to_thread(_decode, data)
                except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
                    return
                self._file(url).write_bytes(small or data)
                out[url] = img
                self._remember(url, img)

            await asyncio.gather(*(one(u) for u in todo))
        await asyncio.to_thread(self.trim, wanted)
        return out

    def clear(self) -> None:
        self._memory.clear()
        if self.path.exists():
            for pattern in ("*.img", "*.png"):
                for file in self.path.glob(pattern):
                    file.unlink()


def name_of(url: str) -> str:
    # keyed by the file's own name: links can move to a new folder, host or signed query and still be the same art
    name = os.path.basename(urlparse(url).path) or url
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:150]


def _decode(data: bytes) -> tuple[Image.Image, bytes | None]:
    img = Image.open(io.BytesIO(data))
    img.load()
    img = img.convert("RGBA")
    if max(img.size) <= MAX_SIDE:
        return img, None
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG", compress_level=1)
    return img, out.getvalue()


async def load_art(art) -> Image.Image | None:
    if art is None:
        return None
    if isinstance(art, Image.Image):
        return art.convert("RGBA")
    if isinstance(art, (bytes, bytearray)):
        return Image.open(io.BytesIO(art)).convert("RGBA")
    text = str(art)
    if text.startswith(("http://", "https://")):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=40),
                                             headers={"User-Agent": "akef-cards"}) as session:
                async with session.get(text) as resp:
                    resp.raise_for_status()
                    data = await resp.read()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise CardError(f"couldn't download the art ({exc.__class__.__name__}), some hosts block scripts. "
                            "download it yourself and pass the bytes instead") from exc
        return Image.open(io.BytesIO(data)).convert("RGBA")
    return Image.open(text).convert("RGBA")
