from dataclasses import dataclass

from disaster_report.models import NewsItem

@dataclass(frozen=True)
class FilterResult:
    selected_news: list[NewsItem]
    relevance_scores: dict[str, float]

@dataclass(frozen=True)
class SummaryResult:
    summary: str
    has_relevant_updates: bool

@dataclass(frozen=True)
class SubmissionClassification:
    is_disaster: bool
    incident_type: str
    country_code: str
    country_name: str
    summary: str
    event_date: str
