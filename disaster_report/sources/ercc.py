
from __future__ import annotations

import html
import logging
import re
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

import country_converter as coco
import httpx

from disaster_report._search_keys import derive_repoll_keys as _derive_repoll_keys
from disaster_report._search_keys import derive_search_keys
from disaster_report._title_format import format_place, format_title, smallest_place
from disaster_report.models import ReportPlace, SourceReport
from disaster_report.sources.errors import SourceFetchError

_BASE_URL = "https://erccportal.jrc.ec.europa.eu/API/ERCC/Maps/"
_DEFAULT_PATH = "GetLatestDailyMapRss"
_NOT_FOUND = "not found"

_TYPE_MAP: dict[str, str] = {
    "Earthquake": "Earthquake",
    "Flood": "Flood",
    "Wild fire": "Forest Fire",
    "Wildfire": "Forest Fire",
    "Forest fire": "Forest Fire",
    "Tropical Cyclone": "Tropical Cyclone",
    "Tropical cyclone": "Tropical Cyclone",
    "Volcano": "Volcano",
    "Volcanic eruption": "Volcano",
    "Drought": "Drought",
    "Tsunami": "Tsunami",
    "Heat Wave": "Severe Weather",
    "Severe Weather": "Severe Weather",
    "Storm": "Severe Weather",
    "Conflict": "Conflict",
}

_TYPE_PRIORITY: tuple[str, ...] = (
    "Tropical Cyclone",
    "Earthquake",
    "Volcano",
    "Tsunami",
    "Conflict",
    "Forest Fire",
    "Flood",
    "Drought",
    "Severe Weather",
)

_GUID_PREFIX = "ERCC_Map_"
_TAG_RE = re.compile(r"<[^>]+>")
_MAGNITUDE_RE = re.compile(r"(\d+\.?\d*)\s*M\b", re.IGNORECASE)
_STORM_NAME_RE = re.compile(
    r"(?:Tropical cyclone|Typhoon|Hurricane|Cyclone)\s+([A-Z][A-Z]*-?\d*)",
)
_cc = coco.CountryConverter()
logger = logging.getLogger(__name__)


class ERCCAdapter:

    source = "ERCC"

    def __init__(self, path: str = _DEFAULT_PATH) -> None:
        self._path = path

    def fetch(self) -> list[SourceReport]:

        url = f"{_BASE_URL}{self._path}"
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SourceFetchError(
                f"ERCC feed returned HTTP {exc.response.status_code} for path {self._path!r}"
            ) from exc
        content_type = response.headers.get("content-type", "")
        if "xml" not in content_type.lower():
            raise SourceFetchError(
                f"ERCC feed returned a non-XML response for path {self._path!r}"
            )
        root = ET.fromstring(response.content)  # noqa: S314
        items = root.findall(".//item")
        return [_item_to_report(item) for item in items]

    def derive_keys(self, report: SourceReport) -> tuple[str, str]:

        return derive_search_keys(report)

    def derive_repoll_keys(self, report: SourceReport) -> list[str]:

        if report.places:
            return _derive_repoll_keys(report)
        year = report.report_date[:4] if report.report_date else ""
        incident_type = report.incident_type
        if not incident_type:
            return []
        return [
            f"{incident_type} latest {year}",
            f"{incident_type} {year}",
        ]


def _item_to_report(item: Any) -> SourceReport:
    raw_fields = _build_raw_fields(item)
    guid = str(raw_fields.get("guid") or "")
    source_id = guid.replace(_GUID_PREFIX, "").strip()
    event_types_raw = str(raw_fields.get("eventTypes") or "")
    incident_type = _resolve_incident_type(event_types_raw)
    pub_date = str(raw_fields.get("pubDate") or "")
    report_date = _to_iso_date(pub_date)
    main_country = str(raw_fields.get("mainCountry") or "")
    countries_iso3 = str(raw_fields.get("countries") or "")
    places = _extract_places(main_country, countries_iso3)
    name = _extract_canonical_name(raw_fields, places, report_date, incident_type)
    return SourceReport(
        source="ERCC",
        source_id=source_id,
        incident_type=incident_type,
        name=name,
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
    description = str(raw_fields.get("description") or "")
    identifier = _extract_identifier(incident_type, description)
    smallest, country = smallest_place(places)
    return format_title(
        incident_type,
        identifier,
        format_place(smallest, country),
        report_date,
    )


def _extract_identifier(incident_type: str, description: str) -> str:
    if incident_type == "Earthquake":
        return _extract_magnitude(description)
    if incident_type == "Tropical Cyclone":
        return _extract_storm_name(description)
    return ""


def _extract_magnitude(description: str) -> str:
    match = _MAGNITUDE_RE.search(description)
    if not match:
        return ""
    try:
        return f"M{float(match.group(1)):.1f}"
    except ValueError:
        return ""


def _extract_storm_name(description: str) -> str:
    match = _STORM_NAME_RE.search(description)
    return match.group(1).strip() if match else ""


def _resolve_incident_type(event_types_raw: str) -> str:
    tokens = [t.strip() for t in event_types_raw.split(",") if t.strip()]
    mapped: list[str] = []
    for token in tokens:
        canonical = _TYPE_MAP.get(token)
        if canonical and canonical not in mapped:
            mapped.append(canonical)
    if not mapped:
        return ""
    if len(mapped) == 1:
        return mapped[0]
    for priority_type in _TYPE_PRIORITY:
        if priority_type in mapped:
            return priority_type
    return mapped[0]


def _build_raw_fields(item: Any) -> dict[str, object]:
    raw: dict[str, object] = {}
    for child in item:
        tag = _local_tag(child.tag)
        if tag == "image":
            url_elem = child.findtext(_local_url_tag(child))
            if url_elem:
                raw["image_url"] = url_elem.strip()
            continue
        text = (child.text or "").strip()
        if tag == "description":
            raw["description"] = _clean_html(text)
        else:
            raw[tag] = text
    return raw


def _local_url_tag(image_elem: Any) -> str:
    for child in image_elem:
        if _local_tag(child.tag) == "url":
            return child.tag
    return "url"


def _clean_html(raw: str) -> str:
    text = _TAG_RE.sub("", raw)
    return html.unescape(text).strip()


def _extract_places(
    main_country: str,
    countries_iso3: str,
) -> list[ReportPlace]:

    codes: list[str] = []
    if main_country:
        code = _country_to_iso2(main_country)
        if code:
            codes.append(code)
    if countries_iso3:
        for iso3 in (s.strip() for s in countries_iso3.split(",") if s.strip()):
            code = _iso3_to_iso2(iso3)
            if code and code not in codes:
                codes.append(code)
    return [ReportPlace(country_code=code, subdivision="", locality="") for code in codes]


def _country_to_iso2(name: str) -> str:
    if not name:
        return ""
    code = str(_cc.convert(names=name, to="ISO2"))
    if not code or code == _NOT_FOUND:
        return ""
    return code


def _iso3_to_iso2(iso3: str) -> str:
    if not iso3:
        return ""
    code = str(_cc.convert(names=iso3, src="ISO3", to="ISO2"))
    if not code or code == _NOT_FOUND:
        return ""
    return code


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _to_iso_date(rfc822: str) -> str:
    if not rfc822:
        return ""
    try:
        dt = parsedate_to_datetime(rfc822)
    except (TypeError, ValueError):
        return ""
    if dt is None:
        return ""
    return dt.date().isoformat()
