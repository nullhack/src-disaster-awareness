from __future__ import annotations

from dataclasses import dataclass, field, replace
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
    disease_name: str | None = None

    def with_ratcheted_priority(
        self, new_priority: str, new_should_report: bool
    ) -> "IncidentRecord":
        """Return an immutable copy with priority escalated + should_report latched.

        Mirrors the store's monotonic ratchet: callers must pre-compute the
        escalated priority (priority only ever rises) and OR the should_report
        flag (once True, stays True). No persistence happens here — this is a
        value-object transform, not an ActiveRecord ``.save()``.
        """
        return replace(
            self,
            priority=new_priority,
            should_report=self.should_report or new_should_report,
        )


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
    severity: str = ""
    priority: str = ""
    priority_rank: int | None = None
    pandemic_potential: str = ""
    event_status: str = ""
    disease_name: str | None = None
    days_since_event: int | None = None

    def is_stale(self, today: date, window: int) -> bool:
        """True when this incident is older than ``window`` days past ``today``."""
        return (today - self.last_updated).days > window

    def is_reportable(self, today: date, window: int) -> bool:
        """True when this incident should appear in the active report.

        Combines the classification verdict (``should_report``) with the
        freshness window (not stale). Report rendering and develop-eligibility
        both reduce to this single predicate.
        """
        return self.should_report and not self.is_stale(today, window)


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
    outlet: str = ""


class IncidentStore(Protocol):
    def count_incidents(self) -> int: ...
    def all_incident_ids(self) -> list[str]: ...
    def undigested_incident_ids(self) -> list[str]: ...
    def find_by_incident_id(self, incident_id: str) -> IncidentView | None: ...
    def get_incident_sources(self, incident_key: int) -> list[SourceView]: ...
    def get_incident_news(self, incident_key: int) -> list[NewsView]: ...
    def get_incident_news_full(self, incident_key: int) -> list[dict]: ...
    def get_active_incidents(self, as_of: date, within_days: int) -> list[IncidentView]: ...

    # --- report read-port ------------------------------------------------------
    def incident_source_counts(
        self, incident_key: int
    ) -> tuple[int, int, int, int, int]:
        """Per-source fact counts for one incident.

        Returns ``(who_don, usgs, gdacs, healthmap, news)``.
        """
        ...

    def incident_news_capped(self, incident_key: int, cap: int) -> list[NewsView]:
        """News for one incident, newest-first, limited to ``cap`` items."""
        ...

    def usgs_max_magnitude(self, incident_key: int) -> float | None:
        """Max USGS magnitude across the incident's linked earthquakes."""
        ...

    def gdacs_alert(self, incident_key: int) -> tuple[str | None, int] | None:
        """``(alertlevel, max_population)`` for the incident's GDACS events.

        ``alertlevel`` is the distinct alert levels joined (``","``) or ``None``;
        ``None`` overall when the incident has no GDACS rows.
        """
        ...

    def who_don_range(self) -> tuple[str, str, int]:
        """``(min_date_iso, max_date_iso, count)`` over all WHO DON rows.

        ``("", "", 0)`` when there are no WHO DONs.
        """
        ...

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
        disease_name: str,
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
