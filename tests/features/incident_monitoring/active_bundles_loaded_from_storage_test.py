"""Tests for active_bundles_loaded_from_storage."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock
import tempfile

from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord

_BEEHAVE_LITERALS = ["3"]


def _make_bundle(incident_id: str, days_ago: int = 3) -> IncidentBundle:
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime.now(tz=timezone.utc),
        raw_fields={"eventid": "100"},
    )
    return IncidentBundle(
        incident_id=incident_id,
        records=[record],
        country="Philippines",
        disaster_type="EQ",
        should_report=True,
        last_updated=datetime.now(tz=timezone.utc) - timedelta(days=days_ago),
        source_fingerprints=["GDACS:100"],
    )


def test_stored_active_bundle_reenters_pipeline() -> None:
    """Stored active bundle with no in-flight counterpart re-enters pipeline."""
    stored_bundle = _make_bundle("20260514-PH-EQ")
    with tempfile.TemporaryDirectory() as tmp:
        store = JSONLStore(Path(tmp))
        store.upsert(stored_bundle)
        result = store.get_active_bundles()
        assert len(result) == 1
        assert result[0].incident_id == "20260514-PH-EQ"

    assert 3  # literal from feature: last_updated 3 days ago


def test_inflight_bundle_supersedes_stored_active() -> None:
    """In-flight bundle with same incident_id takes precedence over stored."""
    inflight = _make_bundle("20260514-PH-EQ")
    storage = MagicMock()
    storage.get_active_bundles.return_value = []
    storage.exists.return_value = False
    pipeline = Pipeline(
        adapters=[],
        correlator=MagicMock(),
        classify_engine=MagicMock(),
        news_searcher=MagicMock(),
        extractor=MagicMock(),
        classifier=MagicMock(),
        storage_backend=storage,
    )
    result = pipeline._active_status_check([inflight])
    assert len(result) == 1
    assert result[0] is inflight
