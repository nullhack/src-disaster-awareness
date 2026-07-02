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
    should_report: bool = True

    def is_stale(self, today: date, window: int) -> bool:
        """True when this incident is older than ``window`` days past ``today``."""
        return (today - self.last_updated).days > window


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
    def undigested_incident_ids(self) -> list[str]: ...
    def find_by_incident_id(self, incident_id: str) -> IncidentView | None: ...
    def get_incident_sources(self, incident_key: int) -> list[SourceView]: ...
    def get_incident_news(self, incident_key: int) -> list[NewsView]: ...
    def get_incident_news_full(self, incident_key: int) -> list[dict]: ...
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

    # --- classification support -------------------------------------------------
    def country_context(self, country_name: str) -> tuple[str, str]:
        """Return ``(country_group, region)`` resolved from ``dim_country``."""
        ...

    def source_tiers(self, source_names: list[str]) -> tuple[str, ...]:
        """Return the ``reliability_tier`` of each named source from ``dim_source``."""
        ...

    def reclassify_all(self, dry_run: bool = True) -> list[dict[str, Any]]:
        """Recompute priority + should_report for every incident (monotonic).

        Never demotes severity/priority; never clears ``should_report``.
        Returns a delta per incident whose classification actually changes.
        """
        ...

    # --- disease dedup ---------------------------------------------------------
    def find_recent_disease_incident(
        self,
        disease: str,
        country: str,
        as_of: date,
        within_days: int,
    ) -> int | None:
        """Find the most-recent disease incident matching (disease, country)
        updated within ``within_days`` of ``as_of``; return its key or None."""
        ...

    def merge_duplicate_disease_incidents(
        self, dry_run: bool = True, window_days: int = 30
    ) -> list[dict[str, Any]]:
        """Collapse existing (disease, country) duplicates into one survivor.

        Returns a delta per merged incident. Idempotent. NOT a CLI command —
        one-time cleanup invoked from a throwaway script.
        """
        ...
