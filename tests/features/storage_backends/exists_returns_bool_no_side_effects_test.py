"""Tests for exists_returns_bool_no_side_effects."""

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


def test_exists_returns_true_for_stored_incident(tmp_path: Path) -> None:
    """Exists returns true for stored incident."""
    store = JSONLStore(base_path=tmp_path)
    bundle = _make_bundle("20260514-JP-EQ")
    store.store([bundle])

    result = store.exists("20260514-JP-EQ")

    assert result is True


def test_exists_returns_false_for_unknown_incident(tmp_path: Path) -> None:
    """Exists returns false for unknown incident."""
    store = JSONLStore(base_path=tmp_path)

    result = store.exists("20260514-XX-UNK")

    assert result is False
