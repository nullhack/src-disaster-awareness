from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


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


def test_active_bundle_merges_fingerprints():
    now = datetime.now(tz=timezone.utc)
    storage = MagicMock()
    storage.get_active_bundles.return_value = []
    storage.exists.return_value = True
    storage.get_last_updated.return_value = now - timedelta(days=3)
    storage.get_source_fingerprints.return_value = ["WHO:old-123"]

    pipeline = _make_pipeline(storage)

    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"eventid": "12345"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-PH-EQ",
        records=[record],
        source_fingerprints=["GDACS:12345"],
        last_updated=None,
    )
    result = pipeline._active_status_check([bundle])
    assert len(result) == 1
    merged = set(result[0].source_fingerprints)
    assert "GDACS:12345" in merged
    assert "WHO:old-123" in merged
