from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from disaster_report.sources.base import RawArticle, RawIncident


@dataclass
class FakeDigester:
    returns: dict = field(default_factory=dict)
    queue: list = field(default_factory=list)
    calls: list = field(default_factory=list)

    def digest(self, sources: Any) -> dict:
        self.calls.append(sources)
        if self.queue:
            current = self.queue.pop(0)
        else:
            current = self.returns
        return {
            "canonical_name": current.get("canonical_name", "Synthesized Incident"),
            "summary": current.get("summary", "AI-generated summary."),
            "severity": current.get("severity", "LOW"),
            "search_keys": current.get("search_keys", ["incident"]),
        }

    @property
    def call_count(self) -> int:
        return len(self.calls)


@dataclass
class StubSource:
    source_name: str
    incidents: list[RawIncident]

    def fetch(self) -> list[RawIncident]:
        return list(self.incidents)


@dataclass
class StubNews:
    results_by_query: dict[str, list[RawArticle]]
    source_name: str = "DuckDuckGo News"
    calls: list = field(default_factory=list)

    def search(self, query: str, timelimit: str | None = None) -> list[RawArticle]:
        self.calls.append((query, timelimit))
        return list(self.results_by_query.get(query, []))


def quake(
    country: str = "Philippines",
    report_date: str = "2026-06-29T00:00:00Z",
    name: str = "M5.2 Earthquake near Sarangani",
    source: str = "USGS",
) -> RawIncident:
    return RawIncident(
        source_name=source,
        incident_name=name,
        country=country,
        disaster_type="Earthquake",
        report_date=report_date,
        source_url=f"https://{source.lower()}.example/1",
        raw_fields={"mag": 5.2, "depth": 10.0, "place": "near Sarangani, Philippines"},
    )


def article(url: str, published: str, headline: str = "Development") -> RawArticle:
    return RawArticle(
        source_name="DDG",
        headline=headline,
        body="body",
        url=url,
        outlet="Reuters",
        published_date=published,
    )
