"""Tests for IncidentBundle minimum record count constraint."""

from datetime import datetime, timezone

import pytest

from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_singleton_bundle_created_from_a_single_uncorrelated_record():
    """Verify that a single record can form a valid IncidentBundle."""
    # Given a single RawRecord from GDELT with no matching records from other sources
    record = RawRecord(
        source_name="GDELT",
        fetched_at=datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc),
        raw_fields={"id": 1},
    )

    # When the correlator processes the record
    # Then an IncidentBundle is created containing that one RawRecord
    bundle = IncidentBundle(
        incident_id="20260514-UNX-OTH",
        records=[record],
    )
    assert len(bundle.records) == 1
    assert bundle.records[0] is record

    # Constraint: an IncidentBundle with zero records is invalid
    with pytest.raises(ValueError, match="at least one RawRecord"):
        IncidentBundle(
            incident_id="20260514-UNX-OTH",
            records=[],
        )
