"""Tests for raw_fields preserving the complete untouched API response."""

from datetime import datetime, timezone

from disaster_surveillance_reporter.types import RawRecord


def test_gdacs_adapter_response_stored_without_modification():
    """Verify raw_fields stores the complete API response without modification."""
    # Given a GDACS adapter has fetched an earthquake alert with fields
    # eventtype, alertlevel, name, country, iso3, fromdate, url, and severitydata
    api_response = {
        "eventtype": "EQ",
        "alertlevel": "Orange",
        "name": "M6.5 Earthquake near Jakarta",
        "country": "Indonesia",
        "iso3": "IDN",
        "fromdate": "2026-05-14T00:00:00Z",
        "url": "https://gdacs.org/event/12345",
        "severitydata": {
            "score": 7.5,
            "severity": "high",
        },
    }

    # When the adapter creates a RawRecord from the API response
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc),
        raw_fields=api_response,
    )

    # Then the raw_fields dict contains every field exactly as returned by the API
    assert record.raw_fields == api_response
    # Including nested dicts preserved verbatim
    assert record.raw_fields["severitydata"] == {
        "score": 7.5,
        "severity": "high",
    }
    assert record.raw_fields["severitydata"]["score"] == 7.5  # noqa: RUF069
    # No deep copy — same object reference (untouched means no transformation)
    assert record.raw_fields is api_response
