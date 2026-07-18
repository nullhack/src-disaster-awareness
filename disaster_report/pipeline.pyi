from dataclasses import dataclass
import logging

from disaster_report.models import NewsItem

logger: logging.Logger

@dataclass(frozen=True)
class IngestReport:
    source_reports_kept: int
    ai_calls: int
    ddg_calls: int

def _mint_id() -> str: ...
def _enrich_one(news: NewsItem) -> NewsItem: ...
def _enrich_news_items(items: list[NewsItem]) -> list[NewsItem]: ...
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
