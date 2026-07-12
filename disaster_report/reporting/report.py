
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from disaster_report.models import Incident, IncidentLog, NewsItem
from disaster_report.store.base import Warehouse


@dataclass(frozen=True)
class ReportDocument:

    generated_at: str
    incidents: list[Incident]
    timeline: list[IncidentLog]
    news: list[NewsItem]


def build_report(
    warehouse: Warehouse,
    clock: Callable[[], datetime],
) -> ReportDocument:

    incidents = warehouse.read_incidents()
    timeline: list[IncidentLog] = []
    news: list[NewsItem] = []
    for incident in incidents:
        timeline.extend(warehouse.read_timeline(incident.incident_id))
        news.extend(warehouse.read_news(incident.incident_id))
    return ReportDocument(
        generated_at=clock().isoformat(),
        incidents=incidents,
        timeline=timeline,
        news=news,
    )
