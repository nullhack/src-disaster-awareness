"""Test: Pipeline executes seven sequential steps."""

from unittest.mock import MagicMock

from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_pipeline_completes_all_seven_steps():
    """Given raw records, pipeline runs all 7 steps in specified order."""
    import datetime as dt

    record = RawRecord(
        source_name="GDACS",
        fetched_at=dt.datetime(2026, 5, 15),
        raw_fields={"title": "Test Incident", "country": "Philippines",
                     "disaster_type": "Earthquake"},
    )
    bundle = IncidentBundle(
        incident_id="2026-05-15-PH-EQ",
        records=[record],
        country="Philippines",
        disaster_type="Earthquake",
    )

    mock_adapter = MagicMock()
    mock_adapter.source_name = "GDACS"
    mock_adapter.fetch.return_value = [record]

    mock_correlator = MagicMock()
    mock_correlator.correlate.return_value = [bundle]

    mock_classify = MagicMock()
    mock_classify.classify.return_value = bundle
    mock_classify.reevaluate_overrides.return_value = bundle

    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = [bundle]

    mock_classifier = MagicMock()
    mock_classifier.enrich.return_value = [bundle]

    mock_news = MagicMock()
    mock_storage = MagicMock()
    mock_storage.store.return_value = 1

    pipeline = Pipeline(
        adapters=[mock_adapter],
        correlator=mock_correlator,
        classify_engine=mock_classify,
        news_searcher=mock_news,
        extractor=mock_extractor,
        classifier=mock_classifier,
        storage_backend=mock_storage,
    )
    result = pipeline.run()

    # Step 1: Fetch
    mock_adapter.fetch.assert_called_once()
    # Step 2: Correlate
    mock_correlator.correlate.assert_called_once()
    # Step 3: Initial Classify
    mock_classify.classify.assert_called()
    # Step 4: Supplementary Search - no missing fields, no search triggered
    mock_news.search.assert_not_called()
    # Step 5: AI Enrich (extractor -> re-classify -> classifier)
    mock_extractor.extract.assert_called_once()
    assert mock_classify.classify.call_count >= 2
    mock_classifier.enrich.assert_called_once()
    # Step 6: Override Re-evaluation
    mock_classify.reevaluate_overrides.assert_called_once()
    # Step 7: Store
    mock_storage.store.assert_called_once()

    assert result is not None
