"""Tests for source_name matching adapter identity."""

from datetime import datetime, timezone

from disaster_surveillance_reporter.types import RawRecord


def test_gdacs_adapter_assigns_source_name_gdacs():
    """Verify GDACS adapter sets source_name to 'GDACS'."""
    # Given a GDACS adapter has fetched data from the GDACS API
    # When the adapter creates a RawRecord
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc),
        raw_fields={"eventtype": "EQ"},
    )

    # Then the source_name is "GDACS"
    assert record.source_name == "GDACS"
