from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from datetime import datetime
from functools import lru_cache
from importlib import resources

language: ContextVar[str] = ContextVar("akef_cards_language", default="en")
log = logging.getLogger("akef_cards")

MONTHS = {
    "en": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec",
    "es": "ene feb mar abr may jun jul ago sep oct nov dic",
    "de": "Jan. Feb. März Apr. Mai Juni Juli Aug. Sep. Okt. Nov. Dez.",
    "fr": "janv. févr. mars avr. mai juin juil. août sept. oct. nov. déc.",
    "id": "Jan Feb Mar Apr Mei Jun Jul Agu Sep Okt Nov Des",
    "pt": "jan fev mar abr mai jun jul ago set out nov dez",
    "ru": "янв фев мар апр мая июн июл авг сен окт ноя дек",
    "th": "ม.ค. ก.พ. มี.ค. เม.ย. พ.ค. มิ.ย. ก.ค. ส.ค. ก.ย. ต.ค. พ.ย. ธ.ค.",
    "it": "gen feb mar apr mag giu lug ago set ott nov dic",
    "vi": "Th1 Th2 Th3 Th4 Th5 Th6 Th7 Th8 Th9 Th10 Th11 Th12",
}
SEPARATOR = re.compile(r"(\s+[·/]\s+)")
UNITS = {"ja": ("日", "時間", "分"), "ko": ("일 ", "시간 ", "분"), "zh-tw": ("天", "小時", "分"), "zh-cn": ("天", "小时", "分")}


@lru_cache(maxsize=1)
def _table() -> dict[str, dict[str, str]]:
    return {key.casefold(): value for key, value in _raw().items() if not key.startswith("_")}


@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads((resources.files("akef_cards") / "data" / "text.json").read_text(encoding="utf-8"))


def supported() -> list[str]:
    # a language joins this list in text.json once every label in it has been translated
    return list(_raw().get("_complete", ["en"]))


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[re.Pattern, str, dict[str, str]]]:
    out = []
    for key, value in _raw().items():
        if "{}" in key and not key.startswith("_"):
            body = re.escape(key).replace(r"\{\}", "(.+?)")
            out.append((re.compile(f"^{body}$", re.IGNORECASE | re.DOTALL), key, value))
    return sorted(out, key=lambda p: -len(p[0].pattern))


def _missing(label: str, lang: str, value: dict[str, str]) -> bool:
    if value.get(lang, label).casefold() != label.casefold():
        return False
    log.warning("no %s translation for %r, drawing it in English", lang, label)
    return True


def _cased(source: str, text: str) -> str:
    return text.upper() if source.isupper() and any(c.isalpha() for c in source) else text


def duration(text: str, lang: str | None = None) -> str:
    lang = lang or language.get()
    units = UNITS.get(lang)
    if not units:
        return text
    found = re.fullmatch(r"(?:(\d+)d)?\s*(?:(\d+)h)?\s*(?:(\d+)m)?", text.strip(), re.IGNORECASE)
    if not found or not any(found.groups()):
        return text
    # a lone "2M" is two million, not two minutes
    if not found.group(1) and not found.group(2) and not text.strip().endswith("m"):
        return text
    return "".join(f"{n}{u}" for n, u in zip(found.groups(), units) if n).strip()


@lru_cache(maxsize=8192)
def _translate(text: str, lang: str) -> str:
    entry = _table().get(text.casefold())
    if entry is not None:
        return text if _missing(text, lang, entry) else _cased(text, entry[lang])
    if "{}" in text or not any(c.isalpha() for c in text):
        return text
    for pattern, key, value in _patterns():
        found = pattern.match(text)
        if found:
            parts = [duration(_translate(g, lang), lang) for g in found.groups()]
            if _missing(key, lang, value):
                return text
            return _cased(text, value[lang].format(*parts))
    pieces = SEPARATOR.split(text)
    if len(pieces) > 1:
        return "".join(p if SEPARATOR.fullmatch(p) else _translate(p, lang) for p in pieces)
    return text


def t(text: str) -> str:
    lang = language.get()
    if lang == "en" or not text:
        return text
    return _translate(text, lang)


def short_date(when: datetime | None) -> str:
    if when is None:
        return ""
    lang = language.get()
    if lang in ("ja", "zh-tw", "zh-cn"):
        return f"{when.month}月{when.day}日"
    if lang == "ko":
        return f"{when.month}월 {when.day}일"
    return f"{when.day:02d} {MONTHS.get(lang, MONTHS['en']).split()[when.month - 1]}"


def long_date(when: datetime | None) -> str:
    if when is None:
        return ""
    lang = language.get()
    if lang in ("ja", "zh-tw", "zh-cn"):
        return f"{when.year}年{when.month}月{when.day}日"
    if lang == "ko":
        return f"{when.year}년 {when.month}월 {when.day}일"
    return f"{short_date(when)} {when.year}"
