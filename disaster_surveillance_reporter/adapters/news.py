from datetime import datetime, timezone

from ddgs import DDGS

from disaster_surveillance_reporter.types import RawRecord


class NewsSearcher:
    source_name = "DDG-NEWS"

    @staticmethod
    def _build_query(title=None, country=None, disaster_type=None):
        title = title or "disaster incident"
        country = country or "disaster"
        disaster_type = disaster_type or "emergency"
        return f"{title} {country} {disaster_type} latest news"

    def search(self, query, *, region, timelimit, max_results):
        try:
            results = DDGS().news(query)
        except Exception:
            return []

        records = []
        fetched_at = datetime.now(tz=timezone.utc)
        for article in results:
            if not isinstance(article, dict):
                continue
            records.append(
                RawRecord(
                    source_name=self.source_name,
                    fetched_at=fetched_at,
                    raw_fields=article,
                )
            )

        return records[:max_results]
