"""Tests for filter_query_by_disaster_type."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_query_filters_by_disaster_type(tmp_path: Path) -> None:
    """Query filters by disaster type."""
    record_eq = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    record_fl = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    bundle_eq = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record_eq],
        disaster_type="EQ",
        classification_date=date(2026, 5, 14),
    )
    bundle_fl = IncidentBundle(
        incident_id="20260514-PH-FL",
        records=[record_fl],
        disaster_type="FL",
        classification_date=date(2026, 5, 14),
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([bundle_eq, bundle_fl])

    results = store.query(
        date_from=date(2026, 5, 13), date_to=date(2026, 5, 15), disaster_type="EQ"
    )

    assert len(results) == 1
    assert results[0].incident_id == "20260514-JP-EQ"
