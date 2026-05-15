"""Tests for incident_id_generated_from_earliest_record_data."""

from datetime import datetime, timezone

from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.types import RawRecord


def test_incident_id_generated_from_earliest_date():
    """Incident ID generated from earliest record data."""
    # beehave traceability: Given step literals from the scenario
    _earliest_date = "2026-05-13"  # noqa: RUF052
    _country_code = "PH"  # noqa: RUF052
    _disaster_type_code = "EQ"  # noqa: RUF052
    assert isinstance(_earliest_date, str)
    assert isinstance(_country_code, str)
    assert isinstance(_disaster_type_code, str)
    dt_earlier = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
    dt_later = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=dt_earlier,
            raw_fields={
                "country": "Philippines",
                "disaster_type": "Earthquake",
                "title": "Earthquake in Philippines",
            },
        ),
        RawRecord(
            source_name="WHO",
            fetched_at=dt_later,
            raw_fields={
                "country": "Philippines",
                "disaster_type": "Earthquake",
                "title": "Quake hits Philippines",
            },
        ),
    ]

    bundles = Correlator().correlate(records)

    assert len(bundles) == 1
    bundle = bundles[0]
    assert bundle.incident_id == "20260513-PH-EQ"
    # Incident ID is stable — must not be empty or placeholder
    assert len(bundle.incident_id) >= 13  # YYYYMMDD-CC-TTT minimum
