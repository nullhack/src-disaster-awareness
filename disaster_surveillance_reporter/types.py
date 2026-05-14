from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class RawRecord:
    source_name: str
    fetched_at: datetime
    raw_fields: dict


@dataclass
class IncidentBundle:
    incident_id: str
    records: list[RawRecord]
    country: str | None = None
    country_code: str | None = None
    country_group: str | None = None
    disaster_type: str | None = None
    incident_level: int | None = None
    priority: str | None = None
    should_report: bool = False
    overrides: list[str] = field(default_factory=list)
    summary: str | None = None
    rationale: str | None = None
    estimated_affected: int | None = None
    estimated_deaths: int | None = None
    ai_enriched: bool = False
    enrichment_failed: bool = False
    classified_at: datetime | None = None
    classification_date: date | None = None


@dataclass(frozen=True)
class Incident:
    incident_id: str
    source_names: list[str]
    incident_name: str
    country: str | None = None
    country_code: str | None = None
    country_group: str = "C"
    disaster_type: str | None = None
    incident_level: int = 1
    priority: str = "LOW"
    should_report: bool = False
    overrides: list[str] = field(default_factory=list)
    report_date: date = field(default_factory=date.today)
    source_urls: list[str] = field(default_factory=list)
    summary: str | None = None
    rationale: str | None = None
    estimated_affected: int | None = None
    estimated_deaths: int | None = None
    ai_enriched: bool = False
    record_count: int = 0
