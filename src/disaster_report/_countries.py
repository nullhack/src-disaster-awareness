
from __future__ import annotations

import re
from typing import Any, cast

import pycountry
from iso3166_2 import Subdivisions
from iso3166_2.exceptions import InvalidCountryCode

from disaster_report._country_names import country_name
from disaster_report._regions import subregion_for_country


_iso = Subdivisions()


def _safe_subdivision_names(alpha_2: str) -> list[str]:

    try:
        names = _iso.subdivision_names(alpha_2)
    except InvalidCountryCode:
        return []
    if isinstance(names, dict):
        return [
            n
            for sub in names.values()
            for n in (sub if isinstance(sub, list) else [sub])
        ]
    return names


# Country-name aliases that pycountry's canonical names miss.  Keys are
# the strings that appear in WHO prose; values are the alpha_2 codes.
# Longest-first matching at the regex level ensures multi-word aliases
# (``"Democratic Republic of the Congo"``) win over their substrings
# (``"Congo"``).
_ALIASES: dict[str, str] = {
    "Democratic Republic of the Congo": "CD",
    "Democratic Republic of Congo": "CD",
    "Republic of the Congo": "CG",
    "DRC": "CD",
    "South Korea": "KR",
    "Republic of Korea": "KR",
    "North Korea": "KP",
    "Iran": "IR",
    "Russia": "RU",
    "Russian Federation": "RU",
    "Vietnam": "VN",
    "Syria": "SY",
    "Venezuela": "VE",
    "Bolivia": "BO",
    "Taiwan": "TW",
    "United States": "US",
    "USA": "US",
    "United Kingdom": "GB",
    "UK": "GB",
    "Czech Republic": "CZ",
    "Cape Verde": "CV",
    "Burma": "MM",
    "Macedonia": "MK",
    "North Macedonia": "MK",
    "Hong Kong": "HK",
    "Congo": "CG",
}

# Uninhabited / external territories without a UN M49 subregion; the
# scanner resolves them via pycountry but they carry no disaster-relevant
# signal and are dropped before returning.
_DROPPED_ALPHA2: frozenset[str] = frozenset(
    {
        "AQ",
        "BV",
        "GS",
        "HM",
        "UM",
        "CC",
        "CX",
        "IO",
        "TF",
    }
)


def _build_alias_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for country in cast("list[Any]", pycountry.countries):
        for attr in ("name", "common_name", "official_name"):
            value = getattr(country, attr, None)
            if value:
                out[value] = country.alpha_2
    out.update(_ALIASES)
    return out


_ALIAS_MAP: dict[str, str] = _build_alias_map()
_NAMES_SORTED: list[str] = sorted(_ALIAS_MAP.keys(), key=len, reverse=True)
_COUNTRY_PATTERN: re.Pattern[str] = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in _NAMES_SORTED) + r")\b",
    re.IGNORECASE,
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_ENTITY_RE = re.compile(r"&[a-z]+;")
_WS_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    text = _HTML_TAG_RE.sub(" ", text or "")
    text = _ENTITY_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


# Phrases that suppress a country match at the same position.  "South
# Georgia" names a UK territory, not the country Georgia (GE).
_SUPPRESSORS: dict[str, re.Pattern[str]] = {
    "Georgia": re.compile(r"South\s+Georgia\b", re.IGNORECASE),
}


def _resolve_alpha2(raw: str) -> str:
    code = _ALIAS_MAP.get(raw)
    if code:
        return code
    code = _ALIAS_MAP.get(raw.title())
    if code:
        return code
    return _ALIAS_MAP.get(raw.upper(), "")


def scan_countries(text: str) -> list[tuple[str, str]]:

    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in _COUNTRY_PATTERN.finditer(text or ""):
        raw = match.group(1)
        alpha_2 = _resolve_alpha2(raw)
        if not alpha_2 or alpha_2 in seen or alpha_2 in _DROPPED_ALPHA2:
            continue
        suppressor = _SUPPRESSORS.get(raw)
        if suppressor and suppressor.search(text):
            continue
        seen.add(alpha_2)
        out.append((country_name(alpha_2), alpha_2))
    return out


def scan_subdivision(text: str, alpha_2: str) -> str:

    names = _safe_subdivision_names(alpha_2)
    if not names:
        return ""
    lowered = (text or "").lower()
    for name in names:
        if name and re.search(r"\b" + re.escape(name.lower()) + r"\b", lowered):
            return name
    return ""


def extract_places_from_text(
    *, title: str, body_sections: dict[str, str]
) -> list[dict[str, str]]:

    if "global" in (title or "").lower():
        return []
    body = _strip_html(" ".join(body_sections.values()))
    countries = scan_countries(body)
    places: list[dict[str, str]] = []
    for name, alpha_2 in countries:
        subdivision = scan_subdivision(body, alpha_2)
        places.append(
            {
                "name": name,
                "country_code": alpha_2,
                "subdivision": subdivision,
                "locality": "",
                "region": subregion_for_country(alpha_2),
            }
        )
    return places
