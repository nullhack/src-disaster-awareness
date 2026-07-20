
from __future__ import annotations

import logging
import re
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

import httpx
import pycountry
from iso3166_2 import Subdivisions

from disaster_report._country_names import country_name
from disaster_report._search_keys import derive_search_keys
from disaster_report.models import ReportPlace, SourceReport
from disaster_report.sources.errors import SourceFetchError

_BASE_URL = "https://www.gdacs.org/xml/"
_DEFAULT_PATH = "rss_7d.xml"
_G = "{http://www.gdacs.org}"
_GEO = "{http://www.w3.org/2003/01/geo/wgs84_pos#}"
_DC = "{http://purl.org/dc/elements/1.1/}"
_EVENTID_RE = re.compile(r"[?&]eventid=(\d+)", re.IGNORECASE)
_TYPES: dict[str, str] = {
    "TC": "Tropical Cyclone",
    "EQ": "Earthquake",
    "FL": "Flood",
    "WF": "Forest Fire",
    "DR": "Drought",
    "TS": "Tsunami",
    "VO": "Volcano",
    "Wildfire": "Forest Fire",
}
_SIGNIFICANT_ALERTLEVELS = {"Orange", "Red"}
_LOOKUP_RADIUS_KM = 200
_OCEAN_FALLBACK_RADIUS_KM = 200

_iso = Subdivisions()
logger = logging.getLogger(__name__)


class GDACSAdapter:

    def __init__(
        self,
        path: str = _DEFAULT_PATH,
    ) -> None:
        self._path = path

    def fetch(self) -> list[SourceReport]:

        url = f"{_BASE_URL}{self._path}"
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if not content_type.lower().startswith("application/xml"):
            raise SourceFetchError(
                f"GDACS feed returned a non-XML response for path {self._path!r}"
            )
        # ET.fromstring is safe here: Python 3.7.1+ does not resolve external
        # entities by default (no XXE vector), expat bounds entity expansion,
        # and the body comes from the trusted public GDACS endpoint. defusedxml
        # would require a new dependency, forbidden by the build-target.
        root = ET.fromstring(response.content)  # noqa: S314
        items = root.findall(".//item")
        return [_item_to_report(item) for item in items]

    def should_monitor(self, report: SourceReport) -> bool:

        alertlevel = report.raw_fields.get("alertlevel")
        if not isinstance(alertlevel, str):
            return False
        return alertlevel in _SIGNIFICANT_ALERTLEVELS

    def derive_keys(self, report: SourceReport) -> tuple[str, str]:

        return derive_search_keys(report)


def _item_to_report(item: Any) -> SourceReport:
    raw_fields = _build_raw_fields(item)
    title = str(raw_fields.get("title") or "")
    link = str(raw_fields.get("link") or "")
    eventtype = str(raw_fields.get("eventtype") or "")
    fromdate = str(raw_fields.get("fromdate") or "")
    iso3 = str(raw_fields.get("iso3") or "")
    country_text = str(raw_fields.get("country") or "")
    lat = raw_fields.get("geo_lat")
    lon = raw_fields.get("geo_long")
    places = _extract_places(iso3, country_text, lat, lon)
    return SourceReport(
        source="GDACS",
        source_id=_extract_event_id(link),
        incident_type=_TYPES.get(eventtype, eventtype),
        name=title,
        places=places,
        report_date=_to_iso_date(fromdate),
        raw_fields=raw_fields,
    )


def _build_raw_fields(item: Any) -> dict[str, object]:

    raw: dict[str, object] = {}
    resources: list[dict[str, object]] = []
    for child in item:
        tag = _local_tag(child.tag)
        if tag == "resource":
            resources.append(_resource_dict(child))
            continue
        if tag == "Point":
            lat = child.findtext(f"{_GEO}lat")
            lon = child.findtext(f"{_GEO}long")
            raw["geo_lat"] = _to_float(lat)
            raw["geo_long"] = _to_float(lon)
            continue
        text = (child.text or "").strip()
        if child.attrib:
            raw[tag] = text
            for attr_key, attr_val in child.attrib.items():
                raw[f"{tag}_{attr_key}"] = attr_val
        else:
            raw[tag] = text
    if resources:
        raw["resources"] = resources
    return raw


def _resource_dict(elem: Any) -> dict[str, object]:
    out: dict[str, object] = {}
    for attr_key, attr_val in elem.attrib.items():
        out[attr_key] = attr_val
    for child in elem:
        out[_local_tag(child.tag)] = (child.text or "").strip()
    return out


def _extract_places(
    iso3: str,
    country_text: str,
    lat: Any,
    lon: Any,
) -> list[ReportPlace]:

    primary = _country_name_and_alpha2_from_iso3(iso3)
    secondaries = _country_names_and_alpha2_from_text(country_text)
    codes: list[str] = []
    if primary[1]:
        codes.append(primary[1])
    for _, code in secondaries:
        if code and code not in codes:
            codes.append(code)
    subdivision = ""
    geo_country = ""
    if isinstance(lat, int | float) and isinstance(lon, int | float):
        matches = _iso.reverse_lookup(
            latitude=float(lat),
            longitude=float(lon),
            radius_km=_LOOKUP_RADIUS_KM,
            max_results=1,
        )
        if matches:
            subdivision = str(matches[0].get("name") or "")
            geo_country = str(matches[0].get("countryCode") or "")
    if not codes and geo_country:
        codes.append(geo_country)
    if not codes:
        return []
    places: list[ReportPlace] = []
    for i, code in enumerate(codes):
        places.append(
            ReportPlace(
                country_code=code,
                subdivision=subdivision if i == 0 else "",
                locality="",
            )
        )
    return places


def _country_name_and_alpha2_from_iso3(iso3: str) -> tuple[str, str]:
    if not iso3:
        return "", ""
    country = pycountry.countries.get(alpha_3=iso3)
    if country is None:
        return "", ""
    code = str(country.alpha_2)
    return country_name(code), code


def _country_names_and_alpha2_from_text(
    country_text: str,
) -> list[tuple[str, str]]:

    out: list[tuple[str, str]] = []
    if not country_text:
        return out
    for segment in country_text.split(","):
        seg = segment.strip()
        if not seg:
            continue
        try:
            results = pycountry.countries.search_fuzzy(seg)
        except LookupError:
            continue
        if results:
            code = str(getattr(results[0], "alpha_2", ""))
            name = country_name(code)
            if name and not any(c == code for _, c in out):
                out.append((name, code))
    return out


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _extract_event_id(link: str) -> str:
    match = _EVENTID_RE.search(link)
    return match.group(1) if match else ""


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


def _to_float(value: object) -> object:
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return value
    return value
