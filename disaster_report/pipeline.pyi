from dataclasses import dataclass
import logging

from disaster_report.models import NewsItem, SourceReport
from disaster_report.store.content import ContentStore

logger: logging.Logger

@dataclass(frozen=True)
class IngestReport:
    source_reports_kept: int
    ai_calls: int
    ddg_calls: int

def _mint_id() -> str: ...
def _enrich_one(news: NewsItem) -> NewsItem: ...
def _enrich_news_items(items: list[NewsItem]) -> list[NewsItem]: ...
def _normalize_incident_name(name: str) -> str: ...
def _parse_usgs_ids(value: object) -> set[str]: ...
def _match_usgs_event_family(wh: ContentStore, report: SourceReport) -> str | None: ...
def _find_existing_incident(wh: ContentStore, report: SourceReport) -> str | None: ...
def _commit_news_for_report(
    wh: ContentStore,
    adapter: object,
    report: SourceReport,
    report_id: str,
    selected_news: list[NewsItem],
) -> None: ...
def ingest_source_reports(adapters: object, warehouse: object) -> int: ...
def search_news(
    warehouse: object,
    adapters: object,
    ddg: object,
    digester: object,
    clock: object,
    news_timelimit: str = "w",
    source_id: str | None = None,
    active_window_days: int = 7,
    repoll: bool = False,
) -> None: ...
def generate_logs(
    warehouse: object, digester: object, min_news_threshold: int = 3
) -> None: ...
def run_pipeline(
    adapters: object,
    warehouse: object,
    ddg: object,
    digester: object,
    clock: object,
    min_news_threshold: int = 3,
) -> IngestReport: ...
