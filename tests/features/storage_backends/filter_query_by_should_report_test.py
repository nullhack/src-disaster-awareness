"""Tests for filter_query_by_should_report."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_query_filters_by_should_report(tmp_path: Path) -> None:
    """Query filters by should report."""
    record_yes = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    record_no = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    bundle_true = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record_yes],
        should_report=True,
        classification_date=date(2026, 5, 14),
    )
    bundle_false = IncidentBundle(
        incident_id="20260514-PH-FL",
        records=[record_no],
        should_report=False,
        classification_date=date(2026, 5, 14),
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([bundle_true, bundle_false])

    results = store.query(
        date_from=date(2026, 5, 13), date_to=date(2026, 5, 15), should_report=True
    )

    assert len(results) == 1
    assert results[0].incident_id == "20260514-JP-EQ"
