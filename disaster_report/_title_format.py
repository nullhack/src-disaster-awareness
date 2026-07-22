from __future__ import annotations

import unicodedata

from disaster_report._country_names import country_name
from disaster_report._search_keys import place_token
from disaster_report.models import ReportPlace

_ADMIN_SUFFIXES: tuple[str, ...] = (
    " Zhuangzu Zizhiqu",
    " Autonomous Region",
    " Special Administrative Region",
    " SAR",
    " Sheng",
    " Province",
    " State",
    " Prefecture",
    " Department",
    " Region",
    " District",
    " Territory",
)

_COUNTRY_ALIASES: dict[str, str] = {
    "democratic republic of the congo": "DR Congo",
    "united kingdom": "UK",
    "united states of america": "United States",
    "republic of korea": "South Korea",
    "democratic people's republic of korea": "North Korea",
    "russian federation": "Russia",
    "islamic republic of iran": "Iran",
    "syrian arab republic": "Syria",
    "czech republic": "Czechia",
    "united republic of tanzania": "Tanzania",
    "republic of north macedonia": "North Macedonia",
    "bolivarian republic of venezuela": "Venezuela",
    "brunei darussalam": "Brunei",
    "lao people's democratic republic": "Laos",
    "socialist republic of viet nam": "Vietnam",
    "republic of moldova": "Moldova",
    "state of palestine": "Palestine",
}


def format_title(*parts: str) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def normalise_subdivision(name: str) -> str:
    if not name:
        return ""
    stripped = _strip_accents(name)
    lowered = stripped.lower()
    for suffix in _ADMIN_SUFFIXES:
        if lowered.endswith(suffix.lower()):
            stripped = stripped[: -len(suffix)].strip()
            break
    return stripped.strip()


def normalise_country(name: str) -> str:
    if not name:
        return ""
    return _COUNTRY_ALIASES.get(name.lower().strip(), name.strip())


def smallest_place(places: list[ReportPlace]) -> tuple[str, str]:
    if not places:
        return ("", "")
    place = places[0]
    country = country_name(place.country_code)
    locality_token = place_token(place)
    if locality_token:
        return (locality_token, country)
    if place.subdivision:
        return (normalise_subdivision(place.subdivision), country)
    return (country, country)


def format_place(smallest: str, country: str) -> str:
    smallest = (smallest or "").strip()
    country = (country or "").strip()
    if not smallest and not country:
        return ""
    if not country:
        return smallest
    if smallest and smallest != country:
        return f"{smallest}, {country}"
    return country


def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


