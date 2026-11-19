from __future__ import annotations

import asyncio
import io
import warnings

from PIL import Image

from akef.enka import Build, Enka, EnkaProfile, GameData, Player
from akef.enka.gamedata import language as language_code
from akef.wiki import WikiPage, WikiPart, wiki_page

from akef_cards.contract import ContractDetail, Contracts
from akef_cards.draw import blur_uid
from akef_cards.errors import CardError
from akef_cards.factory import Factory
from akef_cards.framing import pages
from akef_cards.gacha import PullHistory
from akef_cards.i18n import language, supported
from akef_cards.images import DEFAULT_MB, ImageCache, load_art
from akef_cards.live import Live
from akef_cards.memo import Recent
from akef_cards.monument import Event, Monument
from akef_cards.roster import Roster
from akef_cards.sources.skport import (
    contract_detail_from_skport,
    contracts_from_skport,
    factory_from_skport,
    live_from_skport,
    monument_from_skport,
    pulls_from_skport,
    roster_from_skport,
)
from akef_cards.templates import CONTRACT, FACTORY, LIVE, PROFILES, PULLS, TEMPLATES, COMPARE, contract_detail, monument_board, monument_event, roster_board, wiki_board, wiki_pages


def _short(lang: str) -> str:
    try:
        return language_code(lang)[0]
    except ValueError:
        return lang


WIKI_PARTS = {
    WikiPart.OVERVIEW: wiki_board.render,
    WikiPart.SKILLS: wiki_pages.render_skills,
    WikiPart.TALENTS: wiki_pages.render_talents,
    WikiPart.GROWTH: wiki_pages.render_growth,
    WikiPart.PROFILE: wiki_pages.render_profile,
    WikiPart.LORE: wiki_pages.render_lore,
}


class Cards:
    def __init__(
        self,
        *,
        data: GameData | None = None,
        images: ImageCache | None = None,
        lang: str = "en",
        cache: bool = True,
        kept_cards: int = 8,
        cache_mb: float | None = DEFAULT_MB,
    ):
        try:
            language_code(lang)
        except ValueError:
            warnings.warn(f"language {lang!r} is not supported, drawing cards in English", stacklevel=2)
            lang = "en"
        else:
            if _short(lang) not in supported():
                warnings.warn(f"card labels aren't translated into {lang!r} yet, they'll be in English", stacklevel=2)
        self.source = Enka(data=data or GameData(lang=lang), cache=cache)
        self.data = self.source.data
        self.images = images or ImageCache(max_mb=cache_mb)
        self.cache = cache
        self._drawn = Recent(kept_cards if cache else 0)

    def clear_cache(self) -> None:
        self.source.clear_cache()
        self._drawn.clear()

    async def _draw(self, key, urls, fn, *args, **kwargs) -> Image.Image:
        key = (self.data.locale, key) if key is not None else None
        hit = self._drawn.get(key) if key is not None else None
        if hit is not None:
            return hit.copy()
        images = await self.images.get(urls)
        # the worker thread gets a copy of this context, so the template sees the language and the uid switch
        language.set(self.data.locale)
        blur_uid.set(bool(kwargs.get("hide_uid")))
        image = await asyncio.to_thread(fn, *args, images, **kwargs)
        if key is not None and all(u in images for u in urls if u):
            self._drawn.put(key, image)
        return image.copy()

    async def __aenter__(self) -> "Cards":
        await self.data.load()
        return self

    async def __aexit__(self, *exc) -> None:
        pass

    async def enka(self, uid: int | str) -> EnkaProfile:
        return await self.source.profile(uid)

    async def skport(self, card, character, *, stats: bool = True) -> Build:
        return await self.source.build(card, character, stats=stats)

    def skport_player(self, card) -> Player:
        return self.source.player(card)

    async def render_profile(
        self,
        player: Player,
        *,
        template: int = 1,
        grid: str = "4x2",
        hidden: bool = False,
    ) -> list[Image.Image]:
        module = _pick(PROFILES, template, "profile")
        urls = player.urls()
        return [
            await self._draw(("profile", template, grid, i, hidden, repr(player)), urls, module.render, player,
                             grid=grid, page=i, hide_uid=hidden)
            for i in range(len(pages(player, grid)))
        ]

    def skport_live(self, card) -> Live:
        return live_from_skport(card)

    async def render_live(self, live: Live, *, template: int = 1, hidden: bool = False) -> Image.Image:
        module = _pick(LIVE, template, "live")
        return await self._draw(("live", template, hidden, repr(live)), live.urls(), module, live, hide_uid=hidden)

    def skport_monument(self, card, monument) -> Monument:
        return monument_from_skport(card, monument)

    async def render_monument(self, monument: Monument, *, hidden: bool = False) -> Image.Image:
        key = ("monument", hidden, repr(monument))
        return await self._draw(key, monument.urls(), monument_board.render_overview, monument, hide_uid=hidden)

    async def render_monument_event(self, monument: Monument, event=None, *, template: int = 1,
                                    hidden: bool = False):
        draw = _pick(monument_event.TEMPLATES, template, "monument event")
        many = isinstance(event, (list, tuple))
        wanted = list(event) if many else [event]
        events = [monument_event.latest(monument) if e is None else e if isinstance(e, Event) else monument.event(e)
                  for e in wanted]
        cards = [await self._draw(("monument_event", template, e.name, hidden, repr(monument)), monument.urls(e),
                                  draw, monument, e, hide_uid=hidden) for e in events]
        return cards if many else cards[0]

    def skport_factory(self, card) -> Factory:
        return factory_from_skport(card)

    async def render_factory(self, factory: Factory, *, template: int = 1, hidden: bool = False) -> Image.Image:
        draw = _pick(FACTORY, template, "factory")
        return await self._draw(("factory", template, hidden, repr(factory)), factory.urls(), draw, factory,
                                hide_uid=hidden)

    async def skport_pulls(self, card, pulls, *, after=None) -> PullHistory:
        await self.data.load()
        return pulls_from_skport(self.data, card, pulls, after)

    async def render_pulls(self, history: PullHistory, *, template: int = 1, hidden: bool = False) -> Image.Image:
        module = _pick(PULLS, template, "pull history")
        return await self._draw(("pulls", template, hidden, repr(history)), history.urls(), module.render, history,
                                hide_uid=hidden)

    def skport_contract(self, card) -> Contracts:
        return contracts_from_skport(card)

    async def render_contract(self, contracts: Contracts, *, template: int = 1, hidden: bool = False) -> Image.Image:
        module = _pick(CONTRACT, template, "contract")
        return await self._draw(("contract", template, hidden, repr(contracts)), contracts.urls(), module.render,
                                contracts, hide_uid=hidden)

    def skport_contract_detail(self, card, detail) -> ContractDetail:
        return contract_detail_from_skport(card, detail)

    async def render_contract_detail(self, detail: ContractDetail, *, template: int = 1,
                                     hidden: bool = False) -> Image.Image:
        draw = _pick(contract_detail.TEMPLATES, template, "contract detail")
        return await self._draw(("contract_detail", template, hidden, repr(detail)), detail.urls(), draw, detail,
                                hide_uid=hidden)

    def skport_roster(self, card) -> Roster:
        return roster_from_skport(card)

    async def render_roster(self, roster: Roster, *, hidden: bool = False) -> Image.Image:
        return await self._draw(("roster", hidden, repr(roster)), roster.urls(), roster_board.render, roster,
                                hide_uid=hidden)

    def wiki(self, item, index: dict | None = None) -> WikiPage:
        return wiki_page(item, index)

    async def render_wiki(self, page: WikiPage, part: WikiPart | str = WikiPart.OVERVIEW, *,
                          template: int = 1) -> Image.Image:
        try:
            part = WikiPart(part)
        except ValueError:
            raise ValueError(f"unknown wiki part {part!r}, pick one of {[p.value for p in WikiPart]}") from None
        if template not in (1, 2):
            raise ValueError(f"unknown wiki template {template!r}, pick 1 (light) or 2 (dark)")
        return await self._draw(("wiki", part.value, template, repr(page)), page.urls(), WIKI_PARTS[part], page,
                                hide_uid=False, dark=template == 2)

    async def render_wiki_pages(self, page: WikiPage, parts=None, *, template: int = 1) -> list[Image.Image]:
        wanted = [WikiPart(p) for p in parts] if parts else page.parts
        return [await self.render_wiki(page, part, template=template) for part in wanted]

    async def render(self, build: Build, *, template: int = 1, art=None, hidden: bool = False) -> Image.Image:
        module = _pick(TEMPLATES, template, "card")
        key = ("card", template, hidden, art, repr(build)) if art is None or isinstance(art, str) else None
        return await self._draw(key, build.urls(), _with_art, module, build, await load_art(art), hide_uid=hidden)

    async def render_compare(self, first, second, characters, *, template: int = 1,
                             hidden: bool = False) -> list[Image.Image]:
        draw = _pick(COMPARE, template, "compare")
        one, two = [p if isinstance(p, EnkaProfile) else await self.enka(p) for p in (first, second)]
        wanted = [characters] if isinstance(characters, str) else list(characters)
        pairs, missing = [], []
        for name in wanted:
            a, b = one.build(str(name)), two.build(str(name))
            if a is None or b is None:
                missing.append(str(name))
            elif all(a.id != pa.id for pa, _ in pairs):
                pairs.append((a, b))
        if not pairs:
            raise CardError(f"none of {wanted} are showcased on both accounts")
        if missing:
            warnings.warn(f"not showcased on both accounts, skipped: {', '.join(missing)}", stacklevel=2)
        return [await self._draw(("compare", template, hidden, repr(a), repr(b)), a.urls() + b.urls(), draw, a, b,
                                 hide_uid=hidden) for a, b in pairs]

    async def render_bytes(self, data, *, format: str = "PNG", **kwargs):
        draws = {
            Build: (self.render, "card"),
            Live: (self.render_live, "live"),
            Roster: (self.render_roster, "roster"),
            Factory: (self.render_factory, "factory"),
            PullHistory: (self.render_pulls, "pulls"),
            Contracts: (self.render_contract, "contract"),
            ContractDetail: (self.render_contract_detail, "contract_detail"),
            Monument: (self.render_monument, "monument"),
            Player: (self.render_profile, "profile"),
            WikiPage: (self.render_wiki_pages, "wiki"),
        }
        for kind, (draw, name) in draws.items():
            if isinstance(data, kind):
                return _encode(await draw(data, **kwargs), format, name)
        raise TypeError(f"render_bytes can't draw a {type(data).__name__}")

    async def render_compare_bytes(self, first, second, characters, *, format: str = "PNG", **kwargs):
        return _encode(await self.render_compare(first, second, characters, **kwargs), format, "compare")

    async def render_monument_event_bytes(self, monument: Monument, event=None, *, format: str = "PNG", **kwargs):
        return _encode(await self.render_monument_event(monument, event, **kwargs), format, "monument_event")

    async def update(self) -> bool:
        return await self.source.update()


def _encode(drawn, format: str, name: str):
    if isinstance(drawn, list):
        return [_encode(image, format, f"{name}{i}") for i, image in enumerate(drawn, 1)]
    out = io.BytesIO()
    # jpeg has no transparency, saving rgba as jpeg raises
    if format.upper() in ("JPEG", "JPG") and drawn.mode != "RGB":
        drawn = drawn.convert("RGB")
    drawn.save(out, format="JPEG" if format.upper() == "JPG" else format, quality=92)
    out.seek(0)
    out.name = f"{name}.{format.lower()}"
    return out


def _pick(table, template, what):
    if template not in table:
        raise ValueError(f"no {what} template {template!r}, pick one of {sorted(table)}")
    return table[template]


def _with_art(render, build, art, images, *, hide_uid):
    return render(build, images, art=art, hide_uid=hide_uid)
