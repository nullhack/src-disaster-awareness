"""Tests for filter_query_by_priority."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_query_filters_by_priority(tmp_path: Path) -> None:
    """Query filters by priority."""
    record_high = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    record_low = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    bundle_high = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record_high],
        priority="HIGH",
        classification_date=date(2026, 5, 14),
    )
    bundle_low = IncidentBundle(
        incident_id="20260514-PH-FL",
        records=[record_low],
        priority="LOW",
        classification_date=date(2026, 5, 14),
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([bundle_high, bundle_low])

    results = store.query(
        date_from=date(2026, 5, 13), date_to=date(2026, 5, 15), priority="HIGH"
    )

    assert len(results) == 1
    assert results[0].incident_id == "20260514-JP-EQ"
