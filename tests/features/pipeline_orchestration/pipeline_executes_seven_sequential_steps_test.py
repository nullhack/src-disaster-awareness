"""Test: Pipeline executes seven sequential steps."""

from unittest.mock import MagicMock

import pytest

from disaster_surveillance_reporter.pipeline import Pipeline


def test_pipeline_completes_all_seven_steps():
    """Given raw records from all three primary sources
    When the pipeline orchestrator runs
    Then seven pipeline steps execute in specified order."""
    from disaster_surveillance_reporter.adapters._types import RawIncidentData
    from disaster_surveillance_reporter.types import IncidentBundle, RawRecord
    import datetime as dt

    # -- mock adapter returns RawIncidentData --
    mock_adapter = MagicMock()
    mock_adapter.source_name = "GDACS"
    mock_adapter.fetch.return_value = [
        RawIncidentData(
            source_name="GDACS",
            incident_name="Test Incident",
            country="Philippines",
            disaster_type="Earthquake",
            report_date="2026-05-15",
            source_url="http://example.com",
            raw_fields={},
        )
    ]

    record = RawRecord(
        source_name="GDACS",
        fetched_at=dt.datetime(2026, 5, 15),
        raw_fields={"title": "Test Incident", "country": "Philippines", "disaster_type": "Earthquake"},
    )
    bundle = IncidentBundle(
        incident_id="2026-05-15-PH-EQ",
        records=[record],
        country="Philippines",
        disaster_type="Earthquake",
    )

    mock_correlator = MagicMock()
    mock_correlator.correlate.return_value = [bundle]

    mock_classify = MagicMock()
    mock_classify.classify.return_value = bundle
    mock_classify.reevaluate_overrides.return_value = bundle

    mock_news = MagicMock()
    mock_ai = MagicMock()
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
    result = pipeline.run()

    # Step 1: Fetch
    mock_adapter.fetch.assert_called_once()
    # Step 2: Correlate
    mock_correlator.correlate.assert_called_once()
    # Step 3: Initial Classify (called once in step 3, again in step 5 post-extraction)
    mock_classify.classify.assert_called()
    assert mock_classify.classify.call_count >= 1
    # Step 4: Supplementary Search - no missing fields, no search triggered
    mock_news.search.assert_not_called()
    # Step 5: AI Enrich
    mock_ai.chat.assert_called()
    # Step 6: Override Re-evaluation
    mock_classify.reevaluate_overrides.assert_called_once_with(bundle)
    # Step 7: Store
    mock_storage.store.assert_called_once()

    assert result is not None
