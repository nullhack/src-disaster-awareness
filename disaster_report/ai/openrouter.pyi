from disaster_report.ai.base import FilterResult, SubmissionClassification, SummaryResult
from disaster_report.models import IncidentLog, NewsItem

class OpenRouterDigester:
    def __init__(self, model: str, api_key: str) -> None: ...
    def filter(
        self,
        candidate_news: list[NewsItem],
        *,
        incident_type: str,
        incident_name: str,
        incident_places: list,
        incident_date: str,
    ) -> FilterResult: ...
    def summarize(
        self,
        selected_news: list[NewsItem],
        prior_summaries: list[IncidentLog],
        *,
        incident_type: str,
        incident_name: str,
        incident_places: list,
        incident_date: str,
    ) -> SummaryResult: ...
    def classify_submission(
        self, *, url: str, title: str, body: str
    ) -> SubmissionClassification: ...
