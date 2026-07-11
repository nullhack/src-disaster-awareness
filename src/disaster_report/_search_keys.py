
from __future__ import annotations

import datetime
import re

from disaster_report._country_names import country_name
from disaster_report._regions import subregion_for_country
from disaster_report.models import ReportPlace, SourceReport

_DISEASE_SPLIT_RE = re.compile(
    r"\s+(?:virus|disease|outbreak|infection|caused)\b",
    re.IGNORECASE,
)
_MONTHS: tuple[str, ...] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def disease_from_title(title: str) -> str:
    if not title:
        return ""
    head = re.split(r"\s[-–]\s", title, maxsplit=1)[0].strip()  # noqa: RUF001
    parts = _DISEASE_SPLIT_RE.split(head, maxsplit=1)
    return parts[0].strip()


def derive_search_keys(
    report: SourceReport,
    *,
    disease: str = "",
) -> tuple[str, str]:
    incident_type = report.incident_type
    month_year_label = _month_year(report.report_date)
    year_label = _year(report.report_date)

    if len(report.places) == 1 and report.places[0].country_code:
        place = report.places[0]
        country = country_name(place.country_code)
        token = _place_token(place)
        place_str = f"{token}, {country}" if token else country
        strict = " ".join(
            p for p in (incident_type, place_str, month_year_label, disease) if p
        )
        loose = " ".join(p for p in (incident_type, country, year_label, disease) if p)
        return strict, loose

    primary_region = _shared_continent_tokens(
        [subregion_for_country(p.country_code) for p in report.places]
    )
    loose = " ".join(
        p for p in (incident_type, primary_region, disease, year_label) if p
    )
    return "", loose


def derive_repoll_keys(report: SourceReport) -> list[str]:
    year_label = _year(report.report_date)
    places = report.places or []
    place_name = country_name(places[0].country_code) if places else ""
    is_disease = report.source == "WHO"

    if is_disease:
        disease = report.incident_type
        if disease and disease != "Disease" and place_name:
            return [
                f"{disease} {place_name} update {year_label}",
                f"{disease} {place_name} {year_label}",
            ]
        if disease and disease != "Disease":
            return [f"{disease} update {year_label}"]
        return [f"disease {place_name} update {year_label}"] if place_name else []

    incident_type = report.incident_type
    if place_name and incident_type:
        return [
            f"{place_name} {incident_type} latest {year_label}",
            f"{place_name} {incident_type} {year_label}",
        ]
    return []


_CONTINENT_WORDS: frozenset[str] = frozenset(
    {"africa", "asia", "europe", "america", "oceania"}
)


def _shared_continent_tokens(regions: list[str]) -> str:
    counts: dict[str, int] = {}
    for region in regions:
        for token in (region or "").lower().split():
            if token in _CONTINENT_WORDS:
                counts[token] = counts.get(token, 0) + 1
    if not counts:
        return ""
    peak = max(counts.values())
    winners = sorted(token for token, count in counts.items() if count == peak)
    return " ".join(winners)


def _place_token(place: ReportPlace) -> str:
    locality = place.locality
    if not locality:
        return ""
    if " of " in locality:
        after = locality.split(" of ", 1)[1]
        return after.split(",")[0].strip()
    return locality.split(",")[0].strip()


def _month_year(iso_date: str) -> str:
    parsed = _parse_iso_date(iso_date)
    if parsed is None:
        return ""
    return f"{_MONTHS[parsed.month - 1]} {parsed.year}"


def _year(iso_date: str) -> str:
    parsed = _parse_iso_date(iso_date)
    if parsed is None:
        return ""
    return str(parsed.year)


def _parse_iso_date(iso_date: str) -> datetime.date | None:
    if not isinstance(iso_date, str) or not iso_date:
        return None
    try:
        return datetime.date.fromisoformat(iso_date[:10])
    except ValueError:
        return None
