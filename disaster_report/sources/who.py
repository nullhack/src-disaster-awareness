
from __future__ import annotations

import re
from typing import Any

import httpx

from disaster_report._countries import extract_places_from_text, scan_countries
from disaster_report._country_names import country_name
from disaster_report._search_keys import derive_search_keys, disease_from_title
from disaster_report._title_format import (
    format_place,
    format_title,
    normalise_subdivision,
    smallest_place,
)
from disaster_report.models import ReportPlace, SourceReport
from disaster_report.sources.errors import SourceFetchError

_BASE_URL = "https://www.who.int/api/news/diseaseoutbreaknews"
_DEFAULT_ORDERBY = "PublicationDateAndTime"
_TOP = 25
_TITLE_SPLIT_RE = re.compile(r"\s[-–]\s|(?<=[a-z])[-–](?=\s|[A-Z])")

# DON OData prose sections scanned for country/subdivision names.
_BODY_SECTIONS: tuple[str, ...] = (
    "Summary",
    "Overview",
    "Epidemiology",
    "Assessment",
    "Response",
)

_DISEASE_PREFIX_MAP: tuple[tuple[str, str], ...] = (
    ("Avian Influenza", "Avian Influenza"),
    ("Broader transmission of mpox", "Mpox"),
    ("Mpox", "Mpox"),
    ("Circulating vaccine-derived poliovirus", "Poliovirus"),
    ("COVID-19", "COVID-19"),
    ("Ebola", "Ebola"),
    ("Marburg", "Marburg"),
    ("Nipah", "Nipah"),
    ("Cholera", "Cholera"),
    ("Oropouche", "Oropouche"),
    ("Measles", "Measles"),
    ("Yellow fever", "Yellow fever"),
    ("Hantavirus", "Hantavirus"),
    ("Chikungunya", "Chikungunya"),
    ("Anthrax", "Anthrax"),
    ("Rift Valley fever", "Rift Valley fever"),
    ("Dengue", "Dengue"),
    ("Lassa fever", "Lassa fever"),
    ("Meningococcal", "Meningococcal"),
    ("Seasonal influenza", "Seasonal influenza"),
    ("Acute respiratory", "Acute Respiratory"),
    ("Trends of acute respiratory", "Acute Respiratory"),
    ("Antimicrobial Resistance", "AMR"),
    ("International food safety", "Food Safety Event"),
    ("Undiagnosed", "Undiagnosed"),
)


class WHODiseaseOutbreakAdapter:

    source = "WHO"

    def __init__(self, orderby: str = _DEFAULT_ORDERBY) -> None:
        self._orderby = orderby

    def fetch(self) -> list[SourceReport]:

        url = f"{_BASE_URL}?$orderby={self._orderby}%20desc&$top={_TOP}"
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SourceFetchError(
                f"WHO DON feed returned HTTP {response.status_code}"
                f" for orderby {self._orderby!r}"
            ) from exc
        payload = _as_dict(response.json())
        records = payload.get("value")
        if not isinstance(records, list):
            return []
        return [_record_to_report(record) for record in records]

    def derive_keys(self, report: SourceReport) -> tuple[str, str]:

        return derive_search_keys(report)

    def derive_repoll_keys(self, report: SourceReport) -> list[str]:

        disease = _short_disease_name(report.incident_type)
        year = report.report_date[:4] if report.report_date else ""
        country = _resolve_disease_country(
            report.raw_fields.get("title", ""), report.places
        )
        if not country:
            return [f"{disease} update {year}"] if disease else []
        return [
            f"{disease} {country} update {year}",
            f"{disease} {country} {year}",
        ]


def _record_to_report(record: Any) -> SourceReport:
    record_dict = _as_dict(record)
    use_override = bool(record_dict.get("UseOverrideTitle"))
    title_key = "OverrideTitle" if use_override else "Title"
    name = str(record_dict.get(title_key) or "")
    body_sections = {
        key: str(record_dict.get(key) or "")
        for key in _BODY_SECTIONS
        if record_dict.get(key)
    }
    raw_places = extract_places_from_text(title=name, body_sections=body_sections)
    places = [
        ReportPlace(
            country_code=p.get("country_code", ""),
            subdivision=p.get("subdivision", ""),
            locality=p.get("locality", ""),
        )
        for p in raw_places
    ]
    incident_type = disease_from_title(name) or "Disease"
    report_date = _to_iso_date(record_dict.get("PublicationDateAndTime"))
    raw_fields = {key: value for key, value in record_dict.items() if key != title_key}
    raw_fields["title"] = name
    return SourceReport(
        source="WHO",
        source_id=str(record_dict.get("Id") or ""),
        incident_type=incident_type,
        name=_extract_canonical_name(raw_fields, places, report_date, incident_type),
        places=places,
        report_date=report_date,
        raw_fields=raw_fields,
    )


def _extract_canonical_name(
    raw_fields: dict[str, object],
    places: list[ReportPlace],
    report_date: str,
    incident_type: str,
) -> str:
    disease = _short_disease_name(incident_type)
    place = _resolve_disease_place(raw_fields.get("title", ""), places)
    return format_title(disease, place, report_date)


def _resolve_disease_place(title: object, places: list[ReportPlace]) -> str:
    suffix = _title_suffix(title)
    if suffix:
        lowered = suffix.lower()
        if "global" in lowered:
            return "Global"
        matches = scan_countries(suffix)
        if matches:
            code = matches[0][1]
            country = country_name(code)
            for place in places:
                if place.country_code == code and place.subdivision:
                    return format_place(normalise_subdivision(place.subdivision), country)
            return country
    smallest, country = smallest_place(places)
    if not smallest and not country:
        return "Global"
    return format_place(smallest, country)


def _resolve_disease_country(title: object, places: list[ReportPlace]) -> str:
    if isinstance(title, str) and title:
        suffix = _title_suffix(title)
        if suffix and "global" in suffix.lower():
            return ""
        scan_text = suffix or title
        matches = scan_countries(scan_text)
        if matches:
            return country_name(matches[0][1])
    return ""


def _title_suffix(title: object) -> str:
    if not isinstance(title, str) or not title:
        return ""
    parts = _TITLE_SPLIT_RE.split(title, maxsplit=1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()


def _short_disease_name(incident_type: str) -> str:
    if not incident_type:
        return "Disease"
    lowered = incident_type.lower()
    for prefix, short in _DISEASE_PREFIX_MAP:
        if lowered.startswith(prefix.lower()):
            return short
    first = incident_type.split()[0].strip()
    return first or "Disease"


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _to_iso_date(value: object) -> str:
    if not isinstance(value, str) or not value:
        return ""
    return value[:10]
