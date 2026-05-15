"""Tests for filter_query_by_source_name."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_query_filters_by_source_name(tmp_path: Path) -> None:
    """Query filters by source name."""
    record_gdacs = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    record_who = RawRecord(
        source_name="WHO",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    bundle_gdacs = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record_gdacs],
        classification_date=date(2026, 5, 14),
    )
    bundle_who = IncidentBundle(
        incident_id="20260514-PH-FL",
        records=[record_who],
        classification_date=date(2026, 5, 14),
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([bundle_gdacs, bundle_who])

    results = store.query(
        date_from=date(2026, 5, 13), date_to=date(2026, 5, 15), source_name="GDACS"
    )

    assert len(results) == 1
    assert results[0].incident_id == "20260514-JP-EQ"
