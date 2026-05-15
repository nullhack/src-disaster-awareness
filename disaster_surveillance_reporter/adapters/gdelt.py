from datetime import datetime, timezone

import httpx

from disaster_surveillance_reporter.types import RawRecord

GDELT_API = (
    "https://api.gdeltproject.org/api/v2/doc/doc"
    "?query=disaster&format=ArtList&timespan=24h&maxrecords=50"
)


class GDELTAdapter:
    source_name = "GDELT"

    def fetch(self, client: httpx.Client) -> list[RawRecord]:
        try:
            response = client.get(GDELT_API)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return []
        except httpx.TimeoutException:
            return []
        except httpx.NetworkError:
            return []

        try:
            data = response.json()
        except (ValueError, TypeError):
            return []

        articles = data.get("articles", [])
        if not isinstance(articles, list):
            return []

        records: list[RawRecord] = []
        fetched_at = datetime.now(tz=timezone.utc)

        for article in articles:
            if not isinstance(article, dict):
                continue
            if not article:
                continue

            records.append(
                RawRecord(
                    source_name=self.source_name,
                    fetched_at=fetched_at,
                    raw_fields=article,
                )
            )

        return records
