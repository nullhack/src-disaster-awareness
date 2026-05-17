from datetime import datetime, timezone

import httpx

from disaster_surveillance_reporter.types import RawRecord

GDACS_API = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"


class GDACSAdapter:
    source_name = "GDACS"

    def fetch(self, client: httpx.Client) -> list[RawRecord]:
        try:
            response = client.get(GDACS_API)
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

        features = geojson.get("features", [])
        if not isinstance(features, list):
            return []

        records: list[RawRecord] = []
        fetched_at = datetime.now(tz=timezone.utc)

        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties")
            if not isinstance(properties, dict):
                continue

            records.append(
                RawRecord(
                    source_name=self.source_name,
                    fetched_at=fetched_at,
                    raw_fields=properties,
                )
            )

        return records
