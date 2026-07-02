from __future__ import annotations

import httpx

from disaster_report.sources._dates import parse_date
from disaster_report.sources.base import RawIncident, json_list

_DEFAULT_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"


class USGSEarthquakesAdapter:
    source_name = "USGS Earthquakes"

    def __init__(self, url: str = _DEFAULT_URL, timeout: float = 30.0) -> None:
        self.url = url
        self.timeout = timeout

    def fetch(self) -> list[RawIncident]:
        response = httpx.get(self.url, timeout=self.timeout, follow_redirects=True)
        response.raise_for_status()
        out: list[RawIncident] = []
        for feature in json_list(response, "features"):
            properties = feature.get("properties", {}) or {}
            feature_id = feature.get("id") or ""
            net = properties.get("net") or ""
            code = properties.get("code") or ""
            place = properties.get("place", "") or ""
            country = place.strip()
            timestamp = properties.get("time")
            parsed_timestamp = (
                parse_date(str(timestamp)) if isinstance(timestamp, (int, float)) else None
            )
            report_date = parsed_timestamp.isoformat() if parsed_timestamp else ""
            event_id = feature_id or f"{net}{code}" or (net + "_" + code)
            coordinates = (feature.get("geometry") or {}).get("coordinates") or []
            depth = coordinates[2] if len(coordinates) > 2 else 0
            raw_fields = dict(properties)
            raw_fields["event_id"] = event_id
            raw_fields["depth"] = depth
            out.append(
                RawIncident(
                    source_name=self.source_name,
                    incident_name=properties.get("title", "") or "",
                    country=country,
                    disaster_type="Earthquake",
                    report_date=report_date,
                    source_url=properties.get("url", "") or "",
                    raw_fields=raw_fields,
                )
            )
        return out


UsgsAdapter = USGSEarthquakesAdapter
