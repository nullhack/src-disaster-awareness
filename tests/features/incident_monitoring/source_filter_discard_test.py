from datetime import datetime, timezone
from unittest.mock import MagicMock

from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.types import RawRecord


def _make_pipeline(storage_backend):
    return Pipeline(
        adapters=[],
        correlator=MagicMock(),
        classify_engine=MagicMock(),
        news_searcher=MagicMock(),
        extractor=MagicMock(),
        classifier=MagicMock(),
        storage_backend=storage_backend,
    )


def test_seen_fingerprint_is_discarded():
    storage = MagicMock()
    storage.get_active_bundles.return_value = []
    storage.exists_by_source_fingerprint.return_value = True
    pipeline = _make_pipeline(storage)

    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime.now(tz=timezone.utc),
        raw_fields={"eventid": "12345", "title": "Test Earthquake"},
    )
    result = pipeline._pre_filter([record])
    assert result == []
    storage.exists_by_source_fingerprint.assert_called_once_with(
        "GDACS:12345"
    )


def test_new_fingerprint_passes_prefilter():
    storage = MagicMock()
    storage.get_active_bundles.return_value = []
    storage.exists_by_source_fingerprint.return_value = False
    pipeline = _make_pipeline(storage)

    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime.now(tz=timezone.utc),
        raw_fields={"eventid": "99999", "title": "New Earthquake"},
    )
    result = pipeline._pre_filter([record])
    assert result == [record]
    storage.exists_by_source_fingerprint.assert_called_once_with(
        "GDACS:99999"
    )
