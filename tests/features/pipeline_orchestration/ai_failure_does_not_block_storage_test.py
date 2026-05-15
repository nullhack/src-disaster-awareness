"""Test: AI failure does not block storage."""

from unittest.mock import MagicMock

from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_pipeline_ai_failure_stores_unenriched():
    """Given bundles, AI enrich fails completely, bundles store unenriched."""
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

    mock_extractor = MagicMock()
    mock_extractor.extract.side_effect = RuntimeError("AI timeout")

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

    mock_storage.store.assert_called_once()
    stored_bundles = mock_storage.store.call_args[0][0]
    assert len(stored_bundles) == 1
    assert stored_bundles[0].enrichment_failed is True
    assert stored_bundles[0].ai_enriched is False
    assert stored_bundles[0].summary is None
    assert stored_bundles[0].rationale is None
    assert stored_bundles[0].estimated_affected is None
    assert stored_bundles[0].estimated_deaths is None


def test_pipeline_mid_batch_failure_preserves_results():
    """Given 3 bundles, extract succeeds for first, then fails mid-batch."""
    import datetime as dt

    def make_bundle(idx: int) -> IncidentBundle:
        record = RawRecord(
            source_name="GDACS",
            fetched_at=dt.datetime(2026, 5, 15),
            raw_fields={"title": f"Test {idx}", "country": "Philippines",
                        "disaster_type": "Earthquake"},
        )
        return IncidentBundle(
            incident_id=f"2026-05-15-PH-EQ-{idx}",
            records=[record],
            country="Philippines",
            disaster_type="Earthquake",
        )

    bundles = [make_bundle(i) for i in range(3)]
    for b in bundles:
        b.should_report = True

    mock_adapter = MagicMock()
    mock_adapter.source_name = "GDACS"
    mock_adapter.fetch.return_value = [
        RawRecord(source_name="GDACS",
                  fetched_at=dt.datetime(2026, 5, 15),
                  raw_fields={"title": f"Test {i}"})
        for i in range(3)
    ]

    mock_correlator = MagicMock()
    mock_correlator.correlate.return_value = bundles

    mock_classify = MagicMock()
    mock_classify.classify.side_effect = lambda b: b
    mock_classify.reevaluate_overrides.side_effect = lambda b: b

    mock_news = MagicMock()

    # Extractor: succeeds for first bundle, then fails
    call_count = [0]

    def extract_side_effect(bundles):
        for b in bundles:
            call_count[0] += 1
            if call_count[0] > 1:
                raise RuntimeError("extractor failed mid-batch")
            b.ai_enriched = True
        return bundles

    mock_extractor = MagicMock()
    mock_extractor.extract.side_effect = extract_side_effect
    mock_classifier = MagicMock()
    mock_classifier.enrich.return_value = bundles

    mock_storage = MagicMock()
    mock_storage.store.return_value = 3

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

    mock_storage.store.assert_called_once()
    stored_bundles = mock_storage.store.call_args[0][0]
    assert len(stored_bundles) == 3

    enriched = [b for b in stored_bundles if b.ai_enriched]
    failed = [b for b in stored_bundles if b.enrichment_failed]
    assert len(enriched) > 0, "At least one bundle should be enriched"
    assert len(failed) > 0, "At least one bundle should have enrichment_failed"
