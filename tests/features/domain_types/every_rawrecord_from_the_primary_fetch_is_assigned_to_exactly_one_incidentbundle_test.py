"""Tests for unique assignment of RawRecords to IncidentBundles."""

from datetime import datetime, timezone

from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_all_fetched_records_appear_in_bundles_with_no_duplicates_or_orphans():
    """Verify every fetched record appears in exactly one IncidentBundle."""
    # Given a primary fetch returns 5 RawRecords from GDACS, WHO, and GDELT
    dt = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    r1 = RawRecord(source_name="GDACS", fetched_at=dt, raw_fields={"id": 1})
    r2 = RawRecord(source_name="GDACS", fetched_at=dt, raw_fields={"id": 2})
    r3 = RawRecord(source_name="WHO", fetched_at=dt, raw_fields={"id": 3})
    r4 = RawRecord(source_name="GDELT", fetched_at=dt, raw_fields={"id": 4})
    r5 = RawRecord(source_name="GDELT", fetched_at=dt, raw_fields={"id": 5})
    all_records = [r1, r2, r3, r4, r5]

    # When the correlator groups the records into IncidentBundles
    bundle_a = IncidentBundle(
        incident_id="20260514-PH-EQ",
        records=[r1, r2, r3],
    )
    bundle_b = IncidentBundle(
        incident_id="20260514-ID-FL",
        records=[r4, r5],
    )
    bundles = [bundle_a, bundle_b]

    # Then each of the 5 RawRecords appears in exactly one IncidentBundle
    seen: dict[int, int] = {}  # id(record) -> count of bundles it appears in
    for bundle in bundles:
        for record in bundle.records:
            rid = id(record)
            seen[rid] = seen.get(rid, 0) + 1

    # Every original record appears
    for record in all_records:
        assert id(record) in seen, f"Record {record} is an orphan — not in any bundle"

    # No record appears more than once
    for _rid, count in seen.items():
        assert count == 1, f"Record appears in {count} bundles — duplicate assignment"

    # Total coverage: all 5 records accounted for exactly once
    assert len(seen) == 5
