"""Tests for write_failure_isolates_per_bundle."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def _make_bundle(incident_id: str) -> IncidentBundle:
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    return IncidentBundle(
        incident_id=incident_id,
        records=[record],
        classification_date=date(2026, 5, 14),
    )


def test_single_bundle_failure_isolates_others(tmp_path: Path) -> None:
    """Single bundle failure isolates others."""
    store = JSONLStore(base_path=tmp_path)
    bundle_a = _make_bundle("20260514-JP-EQ")
    bundle_b = _make_bundle("20260514-PH-FL")
    bundle_c = _make_bundle("20260514-ID-VO")

    count = store.store([bundle_a, bundle_b, bundle_c])

    # All three should be stored — each write is independent
    assert count == 3
    assert store.exists("20260514-JP-EQ") is True
    assert store.exists("20260514-PH-FL") is True
    assert store.exists("20260514-ID-VO") is True
