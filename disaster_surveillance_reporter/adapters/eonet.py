from datetime import datetime, timezone

import httpx

from disaster_surveillance_reporter.types import RawRecord

EONET_API = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=100"


class EONETAdapter:
    source_name = "EONET"

    _CATEGORY_MAP: dict[str, str] = {
        "Earthquakes": "EQ",
        "Floods": "FL",
        "Volcanoes": "VO",
        "Wildfires": "WF",
        "Severe Storms": "TC",
        "Drought": "DR",
        "Landslides": "LS",
    }

    _LEVEL_MAP: dict[str, int] = {
        "Volcanoes": 3,
    }

    _DEFAULT_LEVEL: int = 2

    def fetch(self, client: httpx.Client) -> list[RawRecord]:
        try:
            response = client.get(EONET_API)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return []
        except httpx.TimeoutException:
            return []
        except httpx.NetworkError:
            return []

        try:
            geojson = response.json()
        except (ValueError, TypeError):
            return []

        events = geojson.get("events", [])
        if not isinstance(events, list):
            return []

        records: list[RawRecord] = []
        fetched_at = datetime.now(tz=timezone.utc)

        for event in events:
            if not isinstance(event, dict):
                continue

            # Skip GDACS-sourced events
            if self._has_gdacs_source(event):
                continue

            # Skip prescribed fires
            title = event.get("title", "")
            if self._is_prescribed_fire(title):
                continue

            records.append(
                RawRecord(
                    source_name=self.source_name,
                    fetched_at=fetched_at,
                    raw_fields=event,
                )
            )

        return records

    def _has_gdacs_source(self, event: dict) -> bool:
        sources = event.get("sources")
        if not isinstance(sources, list):
            return False
        return any(
            isinstance(s, dict) and s.get("id") == "GDACS" for s in sources
        )

    def _is_prescribed_fire(self, title: str) -> bool:
        t = title.lower()
        return "prescribed fire" in t or "rx" in t

    def _compute_fingerprint(self, event_id: str) -> str:
        return f"EONET:{event_id}"

    def _derive_disaster_type(self, categories: list[dict]) -> str:
        for cat in categories:
            if isinstance(cat, dict):
                title = cat.get("title", "")
                if title in self._CATEGORY_MAP:
                    return self._CATEGORY_MAP[title]
        return "OTH"

    def _derive_level(self, categories: list[dict]) -> int:
        for cat in categories:
            if isinstance(cat, dict):
                title = cat.get("title", "")
                if title in self._LEVEL_MAP:
                    return self._LEVEL_MAP[title]
        return self._DEFAULT_LEVEL
