
from __future__ import annotations

from typing import Any

import httpx

from disaster_report._countries import extract_places_from_text
from disaster_report._search_keys import derive_search_keys, disease_from_title
from disaster_report.models import ReportPlace, SourceReport
from disaster_report.sources.errors import SourceFetchError

_BASE_URL = "https://www.who.int/api/news/diseaseoutbreaknews"
_DEFAULT_ORDERBY = "PublicationDateAndTime"
_TOP = 25

# DON OData prose sections scanned for country/subdivision names.
_BODY_SECTIONS: tuple[str, ...] = (
    "Summary",
    "Overview",
    "Epidemiology",
    "Assessment",
    "Response",
)


class WHODiseaseOutbreakAdapter:

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
    return SourceReport(
        source="WHO",
        source_id=str(record_dict.get("Id") or ""),
        incident_type=disease_from_title(name) or "Disease",
        name=name,
        places=places,
        report_date=_to_iso_date(record_dict.get("PublicationDateAndTime")),
        raw_fields={
            key: value for key, value in record_dict.items() if key != title_key
        },
    )


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _to_iso_date(value: object) -> str:
    if not isinstance(value, str) or not value:
        return ""
    return value[:10]
