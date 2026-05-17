"""Tests for blank_records_get_default_classification."""

from datetime import datetime, timezone

from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.types import RawRecord


def test_blank_records_receive_default_classification():
    """A record with no date, country, or title gets default classification."""
    dt = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        RawRecord(
            source_name="GDELT",
            fetched_at=dt,
            raw_fields={},
        )
    ]

    bundles = Correlator().correlate(records)

    assert len(bundles) == 1
    bundle = bundles[0]
    assert len(bundle.records) == 1
    assert bundle.country_group == "C"
    assert bundle.incident_level == 1
    assert bundle.priority == "LOW"
    assert bundle.should_report is False
