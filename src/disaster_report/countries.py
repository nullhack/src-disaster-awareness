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

_CONTINENT_TO_REGION = {
    "Africa": "Africa",
    "Asia": "Asia",
    "Europe": "Europe",
    "America": "Americas",
    "Americas": "Americas",
    "Oceania": "Oceania",
    "Antarctica": "Antarctica",
    "Seven seas (open ocean)": "Oceania",
}

_FALLBACK_ISO2 = "XX"


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
        region = _CONTINENT_TO_REGION.get(str(row["continent"]), "Unknown")
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
        return (_FALLBACK_ISO2, None)
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
    return (_FALLBACK_ISO2, None)


def country_iso2(name: str) -> str:
    return country_from_place(name)[0]


def country_info(name: str) -> tuple[str, str]:
    iso2 = country_iso2(name)
    if iso2 == _FALLBACK_ISO2:
        return (_FALLBACK_ISO2, "Unknown")
    try:
        with _silenced():
            continent = _CC.convert(names=iso2, to="continent", not_found=None)
    except (ValueError, KeyError):
        continent = None
    if not continent or continent == "not found":
        return (iso2, "Unknown")
    return (iso2, _CONTINENT_TO_REGION.get(str(continent), "Unknown"))
