"""Tests for filter_query_by_country_group."""

from datetime import date, datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage.store import JSONLStore
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_query_filters_by_country_group(tmp_path: Path) -> None:
    """Query filters by country group."""
    record_a = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    record_b = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        raw_fields={},
    )
    bundle_a = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record_a],
        country_group="A",
        classification_date=date(2026, 5, 14),
    )
    bundle_b = IncidentBundle(
        incident_id="20260514-PH-FL",
        records=[record_b],
        country_group="B",
        classification_date=date(2026, 5, 14),
    )
    store = JSONLStore(base_path=tmp_path)
    store.store([bundle_a, bundle_b])

    results = store.query(
        date_from=date(2026, 5, 13), date_to=date(2026, 5, 15), country_group="A"
    )

    assert len(results) == 1
    assert results[0].incident_id == "20260514-JP-EQ"
