from __future__ import annotations

from datetime import datetime

from ddgs import DDGS
from ddgs.exceptions import DDGSException

from disaster_report.sources.base import RawArticle

_DEFAULT_QUERY = "disaster"
_DEFAULT_MAX_RESULTS = 25
_DEFAULT_REGION = "wt-wt"


def _to_iso(s: str) -> str:
    if not s:
        return ""
    try:
        return datetime.fromisoformat(s).isoformat()
    except ValueError:
        return s


class DdgNewsAdapter:
    source_name = "DuckDuckGo News"

    def __init__(
        self,
        query: str = _DEFAULT_QUERY,
        max_results: int = _DEFAULT_MAX_RESULTS,
        region: str = _DEFAULT_REGION,
        timelimit: str | None = None,
    ) -> None:
        self.query = query
        self.max_results = max_results
        self.region = region
        self.timelimit = timelimit

    def fetch(self) -> list[RawArticle]:
        try:
            results = DDGS().news(
                query=self.query,
                region=self.region,
                safesearch="on",
                timelimit=self.timelimit,
                max_results=self.max_results,
            )
        except DDGSException:
            return []
        return self._build(results)

    def search(self, query: str, timelimit: str | None = None) -> list[RawArticle]:
        try:
            results = DDGS().news(
                query=query,
                region=self.region,
                safesearch="on",
                timelimit=timelimit,
                max_results=self.max_results,
            )
        except DDGSException:
            return []
        return self._build(results)

    def _build(self, results: list[dict]) -> list[RawArticle]:
        out: list[RawArticle] = []
        for r in results:
            out.append(
                RawArticle(
                    source_name=self.source_name,
                    headline=r.get("title", "") or "",
                    body=r.get("body", "") or "",
                    url=r.get("url", "") or "",
                    outlet=r.get("source", "") or "",
                    published_date=_to_iso(r.get("date", "") or ""),
                    image=r.get("image", "") or "",
                    raw_fields=r,
                )
            )
        return out
