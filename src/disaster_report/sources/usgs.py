from __future__ import annotations

from datetime import UTC, datetime

import httpx

from disaster_report.sources.base import RawIncident

_DEFAULT_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"


class USGSEarthquakesAdapter:
    source_name = "USGS Earthquakes"

    def __init__(self, url: str = _DEFAULT_URL, timeout: float = 30.0) -> None:
        self.url = url
        self.timeout = timeout

    def fetch(self) -> list[RawIncident]:
        resp = httpx.get(self.url, timeout=self.timeout, follow_redirects=True)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        out: list[RawIncident] = []
        for f in features:
            p = f.get("properties", {}) or {}
            ids = f.get("id") or ""
            net = p.get("net") or ""
            code = p.get("code") or ""
            place = p.get("place", "") or ""
            country = place.strip()
            ts = p.get("time")
            report_date = (
                datetime.fromtimestamp(ts / 1000, tz=UTC).isoformat()
                if isinstance(ts, (int, float))
                else ""
            )
            event_id = ids or f"{net}{code}" or (net + "_" + code)
            coords = (f.get("geometry") or {}).get("coordinates") or []
            depth = coords[2] if len(coords) > 2 else 0
            raw_fields = dict(p)
            raw_fields["event_id"] = event_id
            raw_fields["depth"] = depth
            out.append(
                RawIncident(
                    source_name=self.source_name,
                    incident_name=p.get("title", "") or "",
                    country=country,
                    disaster_type="Earthquake",
                    report_date=report_date,
                    source_url=p.get("url", "") or "",
                    raw_fields=raw_fields,
                )
            )
        return out


UsgsAdapter = USGSEarthquakesAdapter
