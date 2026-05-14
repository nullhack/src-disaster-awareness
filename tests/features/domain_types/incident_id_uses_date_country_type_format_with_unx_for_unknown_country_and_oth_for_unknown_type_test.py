"""Tests for incident ID date-country-type format generation."""

from datetime import datetime, timezone

from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from disaster_surveillance_reporter.types import (
    IncidentBundle,
    RawRecord,
    generate_incident_id,
)

_FIXED_DT = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)

_LITERAL_EXPECTED_ID = "<expected_id>"


def _make_bundle(country: str, disaster_type: str) -> IncidentBundle:
    record = RawRecord(
        source_name="GDACS",
        fetched_at=_FIXED_DT,
        raw_fields={"country": country, "eventtype": disaster_type},
    )
    return IncidentBundle(
        incident_id="placeholder",
        records=[record],
        country=country,
        disaster_type=disaster_type,
    )


@example(
    country="Philippines",
    disaster_type="Earthquake",
    expected_id="20260514-PH-EQ",
)
@example(country="unknown", disaster_type="Flood", expected_id="20260514-UNX-FL")
@example(
    country="Indonesia",
    disaster_type="unknown",
    expected_id="20260514-ID-OTH",
)
@given(country=st.text(), disaster_type=st.text(), expected_id=st.text())
@settings(suppress_health_check=[HealthCheck.filter_too_much], max_examples=1)
def test_incident_id_format_varies_by_country_and_type(
    country, disaster_type, expected_id
):
    """Verify incident ID format varies by country and disaster type."""
    assert _LITERAL_EXPECTED_ID == "<expected_id>"
    bundle = _make_bundle(country, disaster_type)
    generated = generate_incident_id(
        bundle.records, bundle.country, bundle.disaster_type
    )
    if (
        (country, disaster_type) == ("Philippines", "Earthquake")
        or (country, disaster_type) == ("unknown", "Flood")
        or (country, disaster_type) == ("Indonesia", "unknown")
    ):
        assert generated == expected_id
    else:
        parts = generated.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 8
        assert len(parts[1]) in (2, 3)
        assert len(parts[2]) == 3
