from datetime import datetime, timedelta, timezone

import httpx

from disaster_surveillance_reporter.types import RawRecord

WHO_API = (
    "https://www.who.int/api/emergencies/diseaseoutbreaknews"
    "?$orderby=PublicationDate%20desc"
)
MAX_AGE_DAYS = 30


class WHOAdapter:
    source_name = "WHO"

    def fetch(self, client: httpx.Client) -> list[RawRecord]:
        try:
            response = client.get(WHO_API)
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

        articles = data.get("value", [])
        if not isinstance(articles, list):
            return []

        records: list[RawRecord] = []
        fetched_at = datetime.now(tz=timezone.utc)
        cutoff = fetched_at - timedelta(days=MAX_AGE_DAYS)

        for article in articles:
            if not isinstance(article, dict):
                continue
            if not article:
                continue

            pub_date_str = article.get("PublicationDate", "")
            try:
                pub_date = datetime.fromisoformat(
                    pub_date_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                continue
            if pub_date < cutoff:
                continue

            records.append(
                RawRecord(
                    source_name=self.source_name,
                    fetched_at=fetched_at,
                    raw_fields=article,
                )
            )

        return records
