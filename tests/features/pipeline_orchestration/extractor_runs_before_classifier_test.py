"""Test: Extractor runs before Classifier."""

from unittest.mock import MagicMock

from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_pipeline_extraction_precedes_classification():
    """Extractor agent processes before Classifier agent in AI enrich step."""
    import datetime as dt

    record = RawRecord(
        source_name="GDACS",
        fetched_at=dt.datetime(2026, 5, 15),
        raw_fields={"title": "Test Incident"},
    )
    bundle = IncidentBundle(
        incident_id="2026-05-15-PH-EQ",
        records=[record],
        country="Philippines",
        disaster_type="Earthquake",
        should_report=True,
    )

    mock_adapter = MagicMock()
    mock_adapter.source_name = "GDACS"
    mock_adapter.fetch.return_value = [record]

    mock_correlator = MagicMock()
    mock_correlator.correlate.return_value = [bundle]

    mock_classify = MagicMock()
    mock_classify.classify.return_value = bundle
    mock_classify.reevaluate_overrides.return_value = bundle

    mock_news = MagicMock()

    call_log = []

    def extract_side_effect(bundles):
        call_log.append("extractor")
        return bundles

    def classify_side_effect(bundles):
        call_log.append("classifier")
        return bundles

    mock_extractor = MagicMock()
    mock_extractor.extract.side_effect = extract_side_effect
    mock_classifier = MagicMock()

    def classify_side_effect(bundles):
        call_log.append("classifier")
        return bundles

    mock_classifier.enrich.side_effect = classify_side_effect

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
    pipeline.run()

    assert "extractor" in call_log
    assert "classifier" in call_log
    assert call_log.index("extractor") < call_log.index("classifier"), (
        "Extractor must run before Classifier"
    )
