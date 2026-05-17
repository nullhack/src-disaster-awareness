"""Tests for unmatched_records_create_singleton_bundles."""

from datetime import datetime, timezone

from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.types import RawRecord


def test_unmatched_record_creates_singleton_bundle():
    """A single record with no matching peers becomes its own bundle."""
    dt = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        RawRecord(
            source_name="WHO",
            fetched_at=dt,
            raw_fields={"title": "Avian influenza in Egypt", "country": "Egypt"},
        )
    ]

    bundles = Correlator().correlate(records)

    assert len(bundles) == 1
    assert len(bundles[0].records) == 1
    assert bundles[0].records[0] is records[0]
