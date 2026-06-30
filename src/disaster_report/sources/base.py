from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class RawIncident:
    source_name: str
    incident_name: str
    country: str
    disaster_type: str
    report_date: str
    source_url: str
    raw_fields: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    source_name: str

    def fetch(self) -> list[RawIncident]: ...


@dataclass(frozen=True)
class RawArticle:
    source_name: str
    headline: str
    body: str
    url: str
    outlet: str
    published_date: str
    image: str = ""
    raw_fields: dict[str, Any] = field(default_factory=dict)


class NewsAdapter(Protocol):
    source_name: str

    def fetch(self) -> list[RawArticle]: ...

    def search(self, query: str, timelimit: str | None = None) -> list[RawArticle]: ...
