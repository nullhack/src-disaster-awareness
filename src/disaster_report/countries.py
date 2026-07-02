from __future__ import annotations

import contextlib
import io
import logging
from functools import lru_cache

import country_converter as coco
import pandas as pd
import pycountry

logging.getLogger("country_converter").setLevel(logging.ERROR)

_CC = coco.CountryConverter()

_KNOWN_CONTINENTS = frozenset(
    {"Africa", "America", "Antarctica", "Asia", "Europe", "Oceania"}
)


def _region_from_continent(continent: str) -> str:
    # country_converter labels the continent "America"; normalize to "Americas".
    # Unrecognized / NaN values fall back to "Unknown".
    if continent == "America":
        return "Americas"
    if continent in _KNOWN_CONTINENTS:
        return continent
    return "Unknown"

# ISO2 sentinel for an unrecognised / multi-country / "Unknown" place. Public so
# callers (pipeline, news_filter, store) compare against it instead of re-typing
# the literal "XX".
UNKNOWN_ISO2 = "XX"


@lru_cache(maxsize=1)
def _table() -> pd.DataFrame:
    return _CC.data[["name_short", "ISO2", "continent"]].copy()


@lru_cache(maxsize=1)
def _subdivisions() -> dict[str, tuple[str, str]]:
    index: dict[str, tuple[str, str]] = {}
    for sub in pycountry.subdivisions:
        if "-" in sub.code:
            country, sub_code = sub.code.split("-", 1)
            index[sub.name.lower()] = (country, sub_code)
            index[sub_code.lower()] = (country, sub_code)
    return index


@contextlib.contextmanager
def _silenced():
    with contextlib.redirect_stderr(io.StringIO()):
        yield


def _try_iso2(name: str) -> str | None:
    key = (name or "").strip()
    if not key:
        return None
    try:
        with _silenced():
            value = _CC.convert(names=key, to="ISO2", not_found=None)
    except (ValueError, KeyError):
        return None
    if not isinstance(value, str) or not value or value == "not found":
        return None
    if len(value) != 2 or not value.isalpha() or not value.isupper():
        return None
    return value


def all_countries() -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for _, row in _table().iterrows():
        name = str(row["name_short"])
        iso2 = str(row["ISO2"])
        region = _region_from_continent(str(row["continent"]))
        out.append((name, iso2, region))
    return out


def canonical_name(name: str) -> str:
    key = (name or "").strip()
    if not key:
        return ""
    if len(key) == 2 and key.isupper():
        try:
            with _silenced():
                short = _CC.convert(names=key, to="name_short", not_found=None)
        except (ValueError, KeyError):
            short = None
        if short and short != "not found":
            return str(short)
        return key
    try:
        with _silenced():
            short = _CC.convert(names=key, to="name_short", not_found=None)
    except (ValueError, KeyError):
        short = None
    if short and short != "not found":
        return str(short)
    return key


def country_from_place(place: str) -> tuple[str, str | None]:
    key = (place or "").strip()
    if not key:
        return (UNKNOWN_ISO2, None)
    if len(key) == 2 and key.isalpha() and key.isupper():
        return (key, None)
    iso2 = _try_iso2(key)
    if iso2:
        return (iso2, None)
    subs = _subdivisions()
    for seg in reversed([s.strip() for s in key.split(",")]):
        if not seg:
            continue
        iso2 = _try_iso2(seg)
        if iso2:
            return (iso2, None)
        hit = subs.get(seg.lower())
        if hit:
            return hit
    return (UNKNOWN_ISO2, None)


def country_iso2(name: str) -> str:
    return country_from_place(name)[0]


def is_known_country(name: str) -> bool:
    """True for a real, named country (not empty / not the Unknown sentinel).

    The pipeline uses ``"Unknown"`` as the country for WHO multi-country DONs;
    callers must not emit that token into search keys or place matching.
    """
    cleaned = (name or "").strip()
    return bool(cleaned) and cleaned.lower() != "unknown"


def country_info(name: str) -> tuple[str, str]:
    iso2 = country_iso2(name)
    if iso2 == UNKNOWN_ISO2:
        return (UNKNOWN_ISO2, "Unknown")
    try:
        with _silenced():
            continent = _CC.convert(names=iso2, to="continent", not_found=None)
    except (ValueError, KeyError):
        continent = None
    if not continent or continent == "not found":
        return (iso2, "Unknown")
    return (iso2, _region_from_continent(str(continent)))
