"""Test: AI failure does not block storage."""

from unittest.mock import MagicMock

import pytest

from disaster_surveillance_reporter.pipeline import Pipeline


def test_pipeline_ai_failure_stores_unenriched():
    """Given incident bundles pending AI enrichment
    When the AI enrichment step fails completely
    Then the bundle stores without AI enrichment."""
    import datetime as dt

    from disaster_surveillance_reporter.adapters._types import RawIncidentData
    from disaster_surveillance_reporter.types import IncidentBundle, RawRecord

    record = RawRecord(
        source_name="GDACS",
        fetched_at=dt.datetime(2026, 5, 15),
        raw_fields={
            "title": "Test Incident",
            "country": "Philippines",
            "disaster_type": "Earthquake",
        },
    )
    bundle = IncidentBundle(
        incident_id="2026-05-15-PH-EQ",
        records=[record],
        country="Philippines",
        disaster_type="Earthquake",
    )

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

    mock_correlator = MagicMock()
    mock_correlator.correlate.return_value = [bundle]

    mock_classify = MagicMock()
    mock_classify.classify.return_value = bundle
    mock_classify.reevaluate_overrides.return_value = bundle

    mock_news = MagicMock()
    mock_ai = MagicMock()
    mock_ai.chat.side_effect = RuntimeError("AI timeout")

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

    # Bundle should be stored even though AI failed
    mock_storage.store.assert_called_once()
    stored_bundles = mock_storage.store.call_args[0][0]
    assert len(stored_bundles) == 1
    assert stored_bundles[0].enrichment_failed is True
    assert stored_bundles[0].ai_enriched is False
    # AI fields should be None
    assert stored_bundles[0].summary is None
    assert stored_bundles[0].rationale is None
    assert stored_bundles[0].estimated_affected is None
    assert stored_bundles[0].estimated_deaths is None


def test_pipeline_mid_batch_failure_preserves_results():
    """Given a batch of three incident bundles needing AI enrichment
    When AI enrichment fails after the first bundle processes
    Then successfully enriched bundles are preserved despite batch failure."""
    import datetime as dt

    from disaster_surveillance_reporter.adapters._types import RawIncidentData
    from disaster_surveillance_reporter.types import IncidentBundle, RawRecord

    def make_bundle(idx: int) -> IncidentBundle:
        record = RawRecord(
            source_name="GDACS",
            fetched_at=dt.datetime(2026, 5, 15),
            raw_fields={
                "title": f"Test Incident {idx}",
                "country": "Philippines",
                "disaster_type": "Earthquake",
            },
        )
        return IncidentBundle(
            incident_id=f"2026-05-15-PH-EQ-{idx}",
            records=[record],
            country="Philippines",
            disaster_type="Earthquake",
        )

    bundles = [make_bundle(i) for i in range(3)]

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
        for _ in range(3)
    ]

    mock_correlator = MagicMock()
    mock_correlator.correlate.return_value = bundles

    mock_classify = MagicMock()
    mock_classify.classify.side_effect = lambda b: b
    mock_classify.reevaluate_overrides.side_effect = lambda b: b

    mock_news = MagicMock()

    # AI succeeds for first bundle (2 calls: extract + classify), fails after
    call_count = [0]

    def ai_side_effect(prompt, *, model):
        call_count[0] += 1
        if call_count[0] > 2:  # fails after first bundle's extract + classify
            raise RuntimeError("AI failure mid-batch")
        return '{"summary": "enriched"}'

    mock_ai = MagicMock()
    mock_ai.chat.side_effect = ai_side_effect

    mock_storage = MagicMock()
    mock_storage.store.return_value = 3

    pipeline = Pipeline(
        adapters=[mock_adapter],
        correlator=mock_correlator,
        classify_engine=mock_classify,
        news_searcher=mock_news,
        ai_provider=mock_ai,
        storage_backend=mock_storage,
    )
    pipeline.run()

    # All bundles should be stored
    mock_storage.store.assert_called_once()
    stored_bundles = mock_storage.store.call_args[0][0]
    assert len(stored_bundles) == 3

    # At least one enriched, at least one failed
    enriched = [b for b in stored_bundles if b.ai_enriched]
    failed = [b for b in stored_bundles if b.enrichment_failed]
    assert len(enriched) > 0, "At least one bundle should be enriched"
    assert len(failed) > 0, "At least one bundle should have enrichment_failed"
