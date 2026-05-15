"""Test: Extractor runs before Classifier."""

from unittest.mock import MagicMock

import pytest

from disaster_surveillance_reporter.pipeline import Pipeline


def test_pipeline_extraction_precedes_classification():
    """Given incident bundles needing both extraction and classification
    When the AI enrichment step runs
    Then the Extractor agent processes before the Classifier agent."""
    import datetime as dt

    from disaster_surveillance_reporter.adapters._types import RawIncidentData
    from disaster_surveillance_reporter.types import IncidentBundle, RawRecord

    record = RawRecord(
        source_name="GDACS",
        fetched_at=dt.datetime(2026, 5, 15),
        raw_fields={"title": "Test Incident"},
    )
    bundle = IncidentBundle(
        incident_id="2026-05-15-PH-EQ",
        records=[record],
        country=None,
        disaster_type=None,
    )

    mock_adapter = MagicMock()
    mock_adapter.source_name = "GDACS"
    mock_adapter.fetch.return_value = [
        RawIncidentData(
            source_name="GDACS",
            incident_name="Test Incident",
            country="",
            disaster_type="",
            report_date="2026-05-15",
            source_url="http://example.com",
            raw_fields={},
        )
    ]

    mock_correlator = MagicMock()
    mock_correlator.correlate.return_value = [bundle]

    mock_classify = MagicMock()
    mock_classify.classify.return_value = bundle
    mock_classify.reevaluate_overrides.return_value = bundle

    mock_news = MagicMock()

    # Track call order
    call_log = []

    def ai_chat(prompt, *, model):
        call_log.append(prompt[:50])
        return '{"summary": "test"}'

    mock_ai = MagicMock()
    mock_ai.chat.side_effect = ai_chat

    mock_storage = MagicMock()
    mock_storage.store.return_value = 1

    pipeline = Pipeline(
        adapters=[mock_adapter],
        correlator=mock_correlator,
        classify_engine=mock_classify,
        news_searcher=mock_news,
        ai_provider=mock_ai,
        storage_backend=mock_storage,
    )
    pipeline.run()

    # AI was called at least twice (extract then classify)
    assert len(call_log) >= 2, f"Expected at least 2 AI calls, got {len(call_log)}"
    assert "Extract" in call_log[0], (
        f"First AI call should be extractor, got: {call_log[0]!r}"
    )
    assert "Classif" in call_log[1], (
        f"Second AI call should be classifier, got: {call_log[1]!r}"
    )
