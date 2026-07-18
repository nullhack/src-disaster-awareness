
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportPlace:

    country_code: str
    subdivision: str
    locality: str


@dataclass(frozen=True)
class SourceReport:

    source: str
    source_id: str
    incident_type: str
    name: str
    places: list[ReportPlace]
    report_date: str
    raw_fields: dict[str, object]
    news_searched_at: str = ""


@dataclass(frozen=True)
class NewsItem:

    url: str
    title: str
    body: str
    published_date: str
    source: str
    domain: str
    image: str
    news_id: str = ""


@dataclass(frozen=True)
class IncidentLog:

    incident_id: str
    log_date: str
    summary: str


@dataclass(frozen=True)
class Incident:

    incident_id: str
    incident_category: str
    incident_type: str
    name: str
    first_seen_at: str
    genesis_report_id: str
