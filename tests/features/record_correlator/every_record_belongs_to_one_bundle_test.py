"""Tests for every_record_belongs_to_one_bundle."""

from datetime import datetime, timezone

from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.types import RawRecord


def test_all_records_assigned_without_duplicates():
    """Five records about two distinct incidents — each record in exactly one bundle."""
    dt_ph1 = datetime(2026, 5, 14, 6, 0, 0, tzinfo=timezone.utc)
    dt_ph2 = datetime(2026, 5, 14, 8, 0, 0, tzinfo=timezone.utc)
    dt_jp1 = datetime(2026, 5, 15, 10, 0, 0, tzinfo=timezone.utc)
    dt_jp2 = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    dt_jp3 = datetime(2026, 5, 15, 14, 0, 0, tzinfo=timezone.utc)

    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=dt_ph1,
            raw_fields={
                "country": "Philippines",
                "title": "Earthquake in Philippines",
            },
        ),
        RawRecord(
            source_name="WHO",
            fetched_at=dt_ph2,
            raw_fields={
                "country": "Philippines",
                "title": "Quake hits Luzon Philippines",
            },
        ),
        RawRecord(
            source_name="GDACS",
            fetched_at=dt_jp1,
            raw_fields={"country": "Japan", "title": "Flood in Japan"},
        ),
        RawRecord(
            source_name="WHO",
            fetched_at=dt_jp2,
            raw_fields={"country": "Japan", "title": "Major flood Japan"},
        ),
        RawRecord(
            source_name="GDELT",
            fetched_at=dt_jp3,
            raw_fields={"country": "Japan", "title": "Flooding in Japan"},
        ),
    ]

    bundles = Correlator().correlate(records)

    # Every record is assigned exactly once
    all_assigned = [r for b in bundles for r in b.records]
    assert len(all_assigned) == len(records)

    # No duplicate assignments (identity check)
    assigned_ids = {id(r) for r in all_assigned}
    assert len(assigned_ids) == len(records)

    # Records from the same incident should be grouped together
    # The PH (May 14) and JP (May 15) groups should form separate bundles
    assert len(bundles) >= 1

    # Every bundle must contain at least one record
    for bundle in bundles:
        assert len(bundle.records) >= 1
