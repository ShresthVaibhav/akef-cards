import asyncio
import io
import ipaddress
import os
import re
import socket
import tempfile
import threading
from collections import OrderedDict
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from aiohttp.resolver import ThreadedResolver
from PIL import Image, UnidentifiedImageError
from yarl import URL

from akef_cards.errors import CardError

MAX_SIDE = 1800
DEFAULT_MB = 15
MAX_ART_BYTES = 15 * 1024 * 1024
MAX_ART_PIXELS = 40_000_000
MAX_REDIRECTS = 3


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
        self._loading: dict[str, asyncio.Task] = {}
        self._session: aiohttp.ClientSession | None = None
        self._downloads = 0
        self._trim_lock = threading.Lock()

    def _file(self, url: str) -> Path:
        return self.path / (name_of(url) + ".img")

    def _remember(self, url: str, img: Image.Image) -> None:
        key = name_of(url)
        self._memory[key] = img
        self._memory.move_to_end(key)
        while len(self._memory) > self.kept_in_memory:
            self._memory.popitem(last=False)

    def _stats(self) -> list[tuple[Path, os.stat_result]]:
        found = []
        for file in self.path.glob("*.img"):
            with suppress(FileNotFoundError):
                found.append((file, file.stat()))
        return found

    def size(self) -> int:
        return sum(info.st_size for _, info in self._stats())

    def trim(self, keep=()) -> None:
        if self.max_bytes is None or not self.path.exists():
            return
        keep = {self._file(u) for u in keep}
        with self._trim_lock:
            files = sorted(self._stats(), key=lambda f: f[1].st_mtime)
            total = sum(info.st_size for _, info in files)
            for file, info in files:
                if total <= self.max_bytes:
                    break
                if file in keep:
                    continue
                try:
                    file.unlink(missing_ok=True)
                except OSError:
                    continue
                total -= info.st_size

    def _save(self, file: Path, data: bytes) -> None:
        temp = None
        try:
            self.path.mkdir(parents=True, exist_ok=True)
            handle, temp = tempfile.mkstemp(dir=self.path, suffix=".tmp")
            with os.fdopen(handle, "wb") as out:
                out.write(data)
            os.replace(temp, file)
        except OSError:
            pass
        finally:
            if temp is not None:
                with suppress(OSError):
                    os.remove(temp)

    async def get(self, urls) -> dict[str, Image.Image]:
        wanted = {u for u in urls if u}
        out = {}
        for u in wanted:
            key = name_of(u)
            if key in self._memory:
                out[u] = self._memory[key]
                self._memory.move_to_end(key)
        async def one(url):
            task = self._loading.get(url)
            if task is None:
                task = self._loading[url] = asyncio.create_task(self._load(url))
                task.add_done_callback(lambda _: self._loading.pop(url, None))
            img = await asyncio.shield(task)
            if img is not None:
                out[url] = img

        await asyncio.gather(*(one(u) for u in wanted - out.keys()))
        await asyncio.to_thread(self.trim, wanted)
        return out

    async def _load(self, url: str) -> Image.Image | None:
        img = await asyncio.to_thread(self._read, self._file(url))
        if img is None:
            return await self._download(url)
        self._remember(url, img)
        return img

    def _read(self, file: Path) -> Image.Image | None:
        try:
            img, small = _decode(file.read_bytes())
        except OSError:
            return None
        if small is not None:
            self._save(file, small)
        else:
            with suppress(OSError):
                os.utime(file)
        return img

    def _store(self, file: Path, data: bytes) -> Image.Image:
        img, small = _decode(data)
        self._save(file, small or data)
        return img

    async def _download(self, url: str) -> Image.Image | None:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout, headers={"User-Agent": "akef-cards"})
        session = self._session
        self._downloads += 1
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
            img = await asyncio.to_thread(self._store, self._file(url), data)
            self._remember(url, img)
            return img
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
            return None
        finally:
            self._downloads -= 1
            if not self._downloads:
                self._session = None
                await session.close()

    def clear(self) -> None:
        self._memory.clear()
        if self.path.exists():
            for pattern in ("*.img", "*.png", "*.tmp"):
                for file in self.path.glob(pattern):
                    file.unlink(missing_ok=True)


def name_of(url: str) -> str:
    # keyed by file name, the host or folder in the link can change for the same art
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


def _is_public(host: str) -> bool:
    ip = ipaddress.ip_address(host.split("%")[0])
    ip = getattr(ip, "ipv4_mapped", None) or ip
    return ip.is_global and not ip.is_multicast


def _check_url(url: URL) -> None:
    if url.scheme not in ("http", "https") or not url.host:
        raise CardError("art url has to be http or https")
    try:
        ok = _is_public(url.host)
    except ValueError:
        return
    if not ok:
        raise CardError("art url points to a private address")


class _PublicResolver(ThreadedResolver):
    async def resolve(self, host, port=0, family=socket.AF_INET):
        found = await super().resolve(host, port, family)
        if not all(_is_public(r["host"]) for r in found):
            raise CardError("art url points to a private address")
        return found


async def _download_art(link: str) -> bytes:
    too_big = f"art is too big, max is {MAX_ART_BYTES // (1024 * 1024)} MB"
    try:
        url = URL(link)
        connector = aiohttp.TCPConnector(resolver=_PublicResolver())
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=40),
                                         headers={"User-Agent": "akef-cards"}) as session:
            for _ in range(MAX_REDIRECTS + 1):
                _check_url(url)
                async with session.get(url, allow_redirects=False) as resp:
                    if resp.status in (301, 302, 303, 307, 308) and "Location" in resp.headers:
                        url = url.join(URL(resp.headers["Location"]))
                        continue
                    resp.raise_for_status()
                    data = bytearray()
                    async for chunk in resp.content.iter_chunked(65536):
                        data += chunk
                        if len(data) > MAX_ART_BYTES:
                            raise CardError(too_big)
                    return bytes(data)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        raise CardError(f"couldn't download the art ({exc.__class__.__name__}), some hosts block scripts. "
                        "download it yourself and pass the bytes instead") from exc
    raise CardError("art url redirects too many times")


def _open_art(source) -> Image.Image:
    try:
        with Image.open(source) as img:
            if img.width * img.height > MAX_ART_PIXELS:
                raise CardError("art has too many pixels")
            return img.convert("RGBA")
    except (UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise CardError("couldn't read the art, is it an image?") from exc


async def art_bytes(art, *, allow_remote: bool = False, allow_local: bool = False) -> bytes:
    if isinstance(art, (bytes, bytearray)):
        return bytes(art)
    if not isinstance(art, os.PathLike):
        text = str(art)
        if text.lower().startswith(("http://", "https://")):
            if not allow_remote:
                raise CardError("art urls are off by default, pass allow_remote=True if you trust it")
            return await _download_art(text)
        if not allow_local:
            raise CardError("file paths as text are off by default, pass allow_local=True or use pathlib.Path "
                            "(only for paths you trust)")
    return await asyncio.to_thread(_read_capped, Path(art))


def _read_capped(path: Path) -> bytes:
    with path.open("rb") as file:
        data = file.read(MAX_ART_BYTES + 1)
    if len(data) > MAX_ART_BYTES:
        raise CardError(f"art is too big, max is {MAX_ART_BYTES // (1024 * 1024)} MB")
    return data


async def load_art(art, *, allow_remote: bool = False, allow_local: bool = False) -> Image.Image | None:
    if art is None:
        return None
    if isinstance(art, Image.Image):
        return await asyncio.to_thread(art.convert, "RGBA")
    data = await art_bytes(art, allow_remote=allow_remote, allow_local=allow_local)
    return await asyncio.to_thread(_open_art, io.BytesIO(data))
