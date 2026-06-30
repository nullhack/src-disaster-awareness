from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from disaster_report.sources.base import RawArticle, RawIncident


@dataclass(frozen=True)
class IncidentRecord:
    incident_id: str
    canonical_name: str
    summary: str
    country: str
    incident_type: str
    priority: str
    severity_level: int
    event_date: str
    first_reported_date: str
    last_updated_date: str
    should_report: bool = True
    search_keys: list[str] = field(default_factory=list)
    disease: str | None = None


@dataclass(frozen=True)
class IncidentView:
    incident_key: int
    incident_id: str
    canonical_name: str
    last_updated: date
    event_date: date
    search_keys: list[str]
    source_count: int
    country_name: str = ""
    country_iso2: str = ""
    ai_digest_date_key: int | None = None
    summary: str = ""
    incident_type: str = ""


@dataclass(frozen=True)
class SourceView:
    source_name: str
    report_date: str
    source_url: str


@dataclass(frozen=True)
class NewsView:
    headline: str
    url: str
    published_date: str


class IncidentStore(Protocol):
    def count_incidents(self) -> int: ...
    def all_incident_ids(self) -> list[str]: ...
    def find_by_incident_id(self, incident_id: str) -> IncidentView | None: ...
    def get_incident_sources(self, incident_key: int) -> list[SourceView]: ...
    def get_incident_news(self, incident_key: int) -> list[NewsView]: ...
    def get_active_incidents(self, as_of: date, within_days: int) -> list[IncidentView]: ...
    def get_source_records(self, incident_key: int) -> list[dict]: ...
    def find_disease_name(self, incident_key: int) -> str | None: ...
    def upsert_incident(self, record: IncidentRecord) -> int: ...
    def link_source_record(self, incident_key: int, raw_incident: RawIncident) -> bool: ...
    def link_news(self, incident_key: int, article: RawArticle) -> bool: ...
    def set_last_updated(self, incident_key: int, last_updated_date: str) -> None: ...
    def set_digest(
        self,
        incident_key: int,
        digest: dict[str, Any],
        digested_on: date,
        country: str,
    ) -> None: ...
