
from __future__ import annotations

import datetime
import json
import logging
from typing import Any

import httpx
import country_converter as coco
from iso3166_2 import Subdivisions

from disaster_report._country_names import country_name
from disaster_report._regions import subregion_for_country
from disaster_report._search_keys import derive_repoll_keys, derive_search_keys
from disaster_report._title_format import format_place, format_title, smallest_place
from disaster_report.models import ReportPlace, SourceReport
from disaster_report.sources.errors import SourceFetchError

_BASE_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/"
_DEFAULT_SLUG = "4.5_month.geojson"
_SIGNIFICANT_MAGNITUDE = 5.5
_LOOKUP_RADIUS_KM = 500
_OCEAN_LOOKUP_RADIUS_KM = 2000
_NOT_FOUND = "not found"

_iso = Subdivisions()
_cc = coco.CountryConverter()
logger = logging.getLogger(__name__)


class USGSAdapter:

    source = "USGS"

    def __init__(
        self,
        slug: str = _DEFAULT_SLUG,
    ) -> None:
        self._slug = slug

    def fetch(self) -> list[SourceReport]:

        url = f"{_BASE_URL}{self._slug}"
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        body = response.text
        if not body.lstrip().startswith("{"):
            raise SourceFetchError(
                f"USGS feed returned a non-JSON response for slug {self._slug!r}"
            )
        payload = _as_dict(json.loads(body))
        features = payload.get("features")
        if not isinstance(features, list):
            return []
        return [_feature_to_report(feature) for feature in features]

    def should_monitor(self, report: SourceReport) -> bool:

        mag = report.raw_fields.get("mag")
        if isinstance(mag, bool) or not isinstance(mag, int | float):
            return False
        return mag >= _SIGNIFICANT_MAGNITUDE

    def derive_keys(self, report: SourceReport) -> tuple[str, str]:

        return derive_search_keys(report)

    def derive_repoll_keys(self, report: SourceReport) -> list[str]:

        return derive_repoll_keys(report)


def _feature_to_report(
    feature: Any,
) -> SourceReport:
    feature_dict = _as_dict(feature)
    properties = _as_dict(feature_dict.get("properties"))
    geometry = _as_dict(feature_dict.get("geometry"))
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list):
        coordinates = []
    depth: object = coordinates[2] if len(coordinates) >= 3 else None
    lat = coordinates[1] if len(coordinates) >= 2 else None
    lon = coordinates[0] if len(coordinates) >= 1 else None
    feature_id = feature_dict.get("id")
    code = properties.get("code")
    source_id = str(feature_id or code or "")
    place = str(properties.get("place") or "")
    places = _extract_places(lat, lon, place)
    raw_fields = {
        **properties,
        "geometry": {
            "type": geometry.get("type"),
            "coordinates": coordinates,
        }
        if coordinates
        else {},
        "depth": depth,
        "place": place,
    }
    return SourceReport(
        source="USGS",
        source_id=source_id,
        incident_type="Earthquake",
        name=_extract_canonical_name(raw_fields, places, _to_iso_date(properties.get("time")), "Earthquake"),
        places=places,
        report_date=_to_iso_date(properties.get("time")),
        raw_fields=raw_fields,
    )


def _extract_canonical_name(
    raw_fields: dict[str, object],
    places: list[ReportPlace],
    report_date: str,
    incident_type: str,
) -> str:
    mag = raw_fields.get("mag")
    mag_str = ""
    if isinstance(mag, int | float) and not isinstance(mag, bool):
        mag_str = f"M{float(mag):.1f}"
    smallest, country = smallest_place(places)
    return format_title(incident_type, mag_str, format_place(smallest, country), report_date)


def _extract_places(
    lat: Any,
    lon: Any,
    place: str,
) -> list[ReportPlace]:

    subdivision = ""
    country_code = ""
    if isinstance(lat, int | float) and isinstance(lon, int | float):
        matches = _iso.reverse_lookup(
            latitude=float(lat),
            longitude=float(lon),
            radius_km=_LOOKUP_RADIUS_KM,
            max_results=1,
        )
        if matches:
            first = matches[0]
            country_code = str(first.get("countryCode") or "")
            subdivision = str(first.get("name") or "")
    if not country_code:
        _, country_code = _country_from_place_text(place)
    if country_code:
        return [
            ReportPlace(
                country_code=country_code,
                subdivision=subdivision,
                locality=_clean_locality(place),
            )
        ]
    return [
        ReportPlace(
            country_code="",
            subdivision="",
            locality="Ocean",
        )
    ]


def _nearest_subregion(lat: Any, lon: Any) -> str:

    if not (isinstance(lat, int | float) and isinstance(lon, int | float)):
        return ""
    matches = _iso.reverse_lookup(
        latitude=float(lat),
        longitude=float(lon),
        radius_km=_OCEAN_LOOKUP_RADIUS_KM,
        max_results=1,
    )
    if not matches:
        return ""
    country_code = str(matches[0].get("countryCode") or "")
    return subregion_for_country(country_code)


def _clean_locality(place: str) -> str:

    if not place:
        return ""
    if " of " in place:
        after = place.split(" of ", 1)[1]
        return after.split(",")[0].strip()
    return place.split(",")[0].strip()


def _country_from_place_text(place: str) -> tuple[str, str]:

    if not place:
        return "", ""
    last = place.split(",")[-1].strip()
    if not last:
        return "", ""
    code = str(_cc.convert(names=last, to="ISO2"))
    if not code or code == _NOT_FOUND:
        return "", ""
    return country_name(code), code


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _to_iso_date(epoch_ms: object) -> str:
    if isinstance(epoch_ms, bool) or not isinstance(epoch_ms, int | float):
        return ""
    try:
        return (
            datetime.datetime.fromtimestamp(epoch_ms / 1000, tz=datetime.timezone.utc)
            .date()
            .isoformat()
        )
    except (OverflowError, OSError, ValueError):
        return ""
