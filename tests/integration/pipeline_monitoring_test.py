from __future__ import annotations

from unittest.mock import MagicMock

from disaster_report import pipeline
from disaster_report.ai.base import SummaryResult
from disaster_report.models import Incident, NewsItem


def _news(news_id: str) -> NewsItem:
    return NewsItem(
        url=f"https://example.com/{news_id}",
        title="El Nino update",
        body="Body",
        published_date="2026-11-20T10:00:00Z",
        source="ddg",
        domain="example.com",
        image="",
        news_id=news_id,
    )


def _incident(*, monitoring_status: str) -> Incident:
    return Incident(
        incident_id="inc-1",
        incident_category="climate",
        incident_type="El Niño",
        name="El Niño — South-Eastern Asia",
        first_seen_at="2026-09-17",
        genesis_report_id="rid-1",
        scope="regional",
        region_code="035",
        region_name="South-Eastern Asia",
        monitoring_status=monitoring_status,
        tracking_window_days=365,
    )


class TestMonitoringLogThreshold:
    def test_monitoring_incident_logs_one_news_item(self) -> None:
        store = MagicMock()
        store.read_summarized_news_ids.return_value = set()
        store.read_news.return_value = [_news("n1")]
        store.read_timeline.return_value = []
        store.read_source_report_by_id.return_value = None
        store.today_date.return_value = "2026-11-24"
        digest = MagicMock()
        digest.summarize.return_value = SummaryResult("One update", True)

        pipeline._generate_logs_for_incident(
            store, digest, _incident(monitoring_status="monitoring"), 3
        )

        digest.summarize.assert_called_once()
        store.append_timeline_with_provenance.assert_called_once()

    def test_standard_incident_still_requires_three_news_items(self) -> None:
        store = MagicMock()
        store.read_summarized_news_ids.return_value = set()
        store.read_news.return_value = [_news("n1")]
        digest = MagicMock()

        pipeline._generate_logs_for_incident(
            store, digest, _incident(monitoring_status="event"), 3
        )

        digest.summarize.assert_not_called()
        store.append_timeline_with_provenance.assert_not_called()
