
from __future__ import annotations

import dspy

from disaster_report.ai.base import FilterResult, SubmissionClassification, SummaryResult
from disaster_report.models import IncidentLog, NewsItem


class FilterDigest(dspy.Signature):

    incident_type: str = dspy.InputField(desc="Type of disaster event")
    incident_name: str = dspy.InputField(desc="Title/name of the source report")
    incident_places: list = dspy.InputField(desc="Places the incident touches")
    incident_date: str = dspy.InputField(desc="Report date ISO")
    candidate_news: list = dspy.InputField(
        desc="List of {url,title,body_excerpt,domain}"
    )
    judgements: list = dspy.OutputField(
        desc="One per candidate news item: {url: str, relevant: bool, reason: str}"
    )


class SummaryDigest(dspy.Signature):

    incident_type: str = dspy.InputField(desc="Type of disaster event")
    incident_name: str = dspy.InputField(desc="Title/name of the source report")
    incident_places: list = dspy.InputField(desc="Places the incident touches")
    incident_date: str = dspy.InputField(desc="Report date ISO")
    prior_summaries: list = dspy.InputField(
        desc="Prior timeline entries for THIS incident, oldest-first: "
        "list of {log_date, summary}. Empty for a brand-new incident."
    )
    selected_news: list = dspy.InputField(
        desc="List of {url,title,body_excerpt,domain}"
    )
    summary: str = dspy.OutputField(
        desc="2-3 sentence summary of what happened in this batch, "
        "grounded ONLY in the selected_news. Do not restate prior content. "
        "Do not reference 'prior summary' or 'since'. "
        "If nothing new is relevant, say so."
    )
    has_relevant_updates: bool = dspy.OutputField(
        desc="True if the selected_news contains relevant updates about THIS incident. "
        "False if the news is not about this incident, has no new information, "
        "or only mentions the incident in passing."
    )


class SubmissionClassifier(dspy.Signature):

    url: str = dspy.InputField(desc="URL of the submitted article")
    title: str = dspy.InputField(desc="Article title")
    body: str = dspy.InputField(desc="Article description / snippet")
    is_disaster: bool = dspy.OutputField(
        desc="True if this article reports an ongoing or recent disaster / outbreak / hazard event"
    )
    incident_type: str = dspy.OutputField(
        desc="Short incident type label (e.g. Earthquake, Flood, Ebola). Empty if not a disaster."
    )
    country_code: str = dspy.OutputField(
        desc="ISO-3166-1 alpha-2 country code where the event is occurring. Empty if unknown."
    )
    country_name: str = dspy.OutputField(
        desc="Country name in English. Empty if unknown."
    )
    summary: str = dspy.OutputField(
        desc="One-sentence summary of the event. Empty if not a disaster."
    )
    event_date: str = dspy.OutputField(
        desc="Event date as YYYY-MM-DD if discoverable, else empty."
    )


class OpenRouterDigester:

    def __init__(self, model: str, api_key: str) -> None:
        self._lm = dspy.LM(model=model, api_key=api_key)
        dspy.configure(lm=self._lm)
        self._filter_cot = dspy.ChainOfThought(FilterDigest)
        self._summary_cot = dspy.ChainOfThought(SummaryDigest)
        self._submission_cot = dspy.ChainOfThought(SubmissionClassifier)

    def filter(
        self,
        candidate_news: list[NewsItem],
        *,
        incident_type: str,
        incident_name: str,
        incident_places: list,
        incident_date: str,
    ) -> FilterResult:
        result = self._filter_cot(
            incident_type=incident_type,
            incident_name=incident_name,
            incident_places=incident_places,
            incident_date=incident_date,
            candidate_news=_to_news_payload(candidate_news),
        )
        kept_urls: set[str] = set()
        for judgement in result.judgements or []:
            if isinstance(judgement, dict) and judgement.get("relevant"):
                kept_urls.add(str(judgement.get("url", "")))
        selected = [item for item in candidate_news if item.url in kept_urls]
        scores = {
            item.url: (1.0 if item.url in kept_urls else 0.0) for item in candidate_news
        }
        return FilterResult(selected_news=selected, relevance_scores=scores)

    def summarize(
        self,
        selected_news: list[NewsItem],
        prior_summaries: list[IncidentLog],
        *,
        incident_type: str,
        incident_name: str,
        incident_places: list,
        incident_date: str,
    ) -> SummaryResult:
        prior_payload = [
            {"log_date": log.log_date, "summary": log.summary}
            for log in prior_summaries
        ]
        result = self._summary_cot(
            incident_type=incident_type,
            incident_name=incident_name,
            incident_places=incident_places,
            incident_date=incident_date,
            prior_summaries=prior_payload,
            selected_news=_to_news_payload(selected_news),
        )
        return SummaryResult(
            summary=str(result.summary or ""),
            has_relevant_updates=bool(result.has_relevant_updates),
        )

    def classify_submission(
        self, *, url: str, title: str, body: str
    ) -> SubmissionClassification:
        result = self._submission_cot(url=url, title=title, body=body)
        return SubmissionClassification(
            is_disaster=bool(result.is_disaster),
            incident_type=str(getattr(result, "incident_type", "") or ""),
            country_code=str(getattr(result, "country_code", "") or "").upper(),
            country_name=str(getattr(result, "country_name", "") or ""),
            summary=str(getattr(result, "summary", "") or ""),
            event_date=str(getattr(result, "event_date", "") or ""),
        )


def _to_news_payload(news: list[NewsItem]) -> list[dict[str, str]]:
    return [
        {
            "url": item.url,
            "title": item.title,
            "body_excerpt": item.body[:500],
            "domain": item.domain,
        }
        for item in news
    ]
