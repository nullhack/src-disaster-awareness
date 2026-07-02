from __future__ import annotations

import time

from ddgs import DDGS
from ddgs.exceptions import DDGSException

from disaster_report.sources._dates import parse_date
from disaster_report.sources.base import RawArticle

_DEFAULT_QUERY = "disaster"
_DEFAULT_MAX_RESULTS = 25
_DEFAULT_REGION = "wt-wt"
# DDG's yahoo_news engine intermittently swallows an internal IndexError during
# rapid successive calls and returns [] with a warning log (looks like an empty
# result). Retry with a short backoff so a transient failure does not silently
# starve an incident of news.
_DEFAULT_RETRY_ATTEMPTS = 3
_DEFAULT_RETRY_BACKOFF = 1.5


def _to_iso(s: str) -> str:
    parsed = parse_date(s)
    return parsed.isoformat() if parsed is not None else s


class DdgNewsAdapter:
    source_name = "DuckDuckGo News"

    def __init__(
        self,
        query: str = _DEFAULT_QUERY,
        max_results: int = _DEFAULT_MAX_RESULTS,
        region: str = _DEFAULT_REGION,
        timelimit: str | None = None,
        retries: int = _DEFAULT_RETRY_ATTEMPTS,
        backoff: float = _DEFAULT_RETRY_BACKOFF,
    ) -> None:
        self.query = query
        self.max_results = max_results
        self.region = region
        self.timelimit = timelimit
        self.retries = max(1, retries)
        self.backoff = backoff

    def fetch(self) -> list[RawArticle]:
        return self.search(self.query, timelimit=self.timelimit)

    def search(self, query: str, timelimit: str | None = None) -> list[RawArticle]:
        results: list[dict] = []
        for attempt in range(self.retries):
            try:
                results = DDGS().news(
                    query=query,
                    region=self.region,
                    safesearch="on",
                    timelimit=timelimit,
                    max_results=self.max_results,
                )
            except DDGSException:
                results = []
            if results:
                break
            if attempt < self.retries - 1:
                time.sleep(self.backoff)
        return self._build(results)

    def _build(self, results: list[dict]) -> list[RawArticle]:
        out: list[RawArticle] = []
        for result in results:
            out.append(
                RawArticle(
                    source_name=self.source_name,
                    headline=result.get("title", "") or "",
                    body=result.get("body", "") or "",
                    url=result.get("url", "") or "",
                    outlet=result.get("source", "") or "",
                    published_date=_to_iso(result.get("date", "") or ""),
                    image=result.get("image", "") or "",
                    raw_fields=result,
                )
            )
        return out
