"""Tests for inverted_date_range_returns_empty_list."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_inverted_date_range_returns_empty_list(tmp_path: Path) -> None:
    """Inverted date range returns empty list."""
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    bundle = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record],
        classification_date=date(2026, 5, 14),
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([bundle])

    date_from_str = "2026-05-20"
    date_to_str = "2026-05-10"
    results = store.query(
        date_from=date.fromisoformat(date_from_str),
        date_to=date.fromisoformat(date_to_str),
    )

    assert isinstance(results, list)
    assert len(results) == 0
