from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from disaster_report.models import Incident, IncidentLog, NewsItem
from disaster_report.store.content import ContentStore

@dataclass(frozen=True)
class ReportDocument:
    # generated_at is the ISO-8601 timestamp at which build_report ran.
    generated_at: str
    incidents: list[Incident]
    timeline: list[IncidentLog]
    news: list[NewsItem]

def build_report(
    warehouse: ContentStore,
    clock: Callable[[], datetime],
) -> ReportDocument: ...
