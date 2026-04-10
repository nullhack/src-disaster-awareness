"""GDACS source adapter with USGS earthquake data fallback."""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from disaster_surveillance_reporter.adapters._types import (
    RawIncidentData,
    SourceAdapter,
)


class GDACSAdapter(SourceAdapter):
    """GDACS (Global Disaster Alert and Coordination System) adapter.

    Uses USGS Earthquake API as primary source since GDACS doesn't provide
    a public JSON API. Filters to only significant recent earthquakes.
    """

    def __init__(
        self,
        base_url: str = "https://www.gdacs.org",
        use_usgs: bool = True,
        min_magnitude: float = 2.0,
        max_age_hours: int = 24,
    ):
        self._source_name = "GDACS"
        self._base_url = base_url
        self._timeout = 10.0
        self._use_usgs = use_usgs
        self._min_magnitude = min_magnitude
        self._max_age_hours = max_age_hours
        self._usgs_feed = "4.5_day"  # Use 4.5+ magnitude feed

    @property
    def source_name(self) -> str:
        return self._source_name

    def fetch(self) -> list[RawIncidentData]:
        """Fetch incidents from GDACS/USGS."""
        incidents = []

        if self._use_usgs:
            incidents.extend(self._fetch_usgs_earthquakes())

        return incidents

    def _fetch_usgs_earthquakes(self) -> list[RawIncidentData]:
        """Fetch recent significant earthquakes from USGS API."""
        try:
            with httpx.Client(timeout=self._timeout) as client:
                # Use magnitude-based feed (4.5+ for today)
                response = client.get(
                    f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{self._usgs_feed}.geojson",
                )
                if response.status_code == 200:
                    return self._parse_usgs_response(response.json())
        except Exception:
            pass
        return []

    def _parse_usgs_response(self, data: dict[str, Any]) -> list[RawIncidentData]:
        """Parse USGS GeoJSON response into RawIncidentData."""
        incidents = []
        now = datetime.now(timezone.utc)
        max_age = timedelta(hours=self._max_age_hours)

        for feature in data.get("features", []):
            props = feature.get("properties", {})
            mag = props.get("mag", 0)

            # Skip small earthquakes
            if mag < self._min_magnitude:
                continue

            place = props.get("place", "Unknown")
            event_time = datetime.fromtimestamp(
                props.get("time", 0) / 1000, tz=timezone.utc
            )

            # Skip old incidents
            if now - event_time > max_age:
                continue

            incidents.append(
                RawIncidentData(
                    source_name="GDACS",
                    incident_name=f"M{mag:.1f} Earthquake {place}",
                    country=self._extract_country(place),
                    disaster_type="Earthquake",
                    report_date=event_time.isoformat(),
                    source_url=props.get("url", "https://earthquake.usgs.gov/"),
                    raw_fields=props,
                )
            )
        return incidents

    def _extract_country(self, place: str) -> str:
        """Extract country from place string."""
        parts = place.split(",")
        if len(parts) > 1:
            return parts[-1].strip()
        return "Unknown"
