"""Tests for priority_must_be_one_of_high_med_or_low."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_classified_bundle_always_has_a_valid_priority():
    """Test classified bundle always has a valid priority."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Red", "country": "Philippines"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-PH-EQ",
        records=[record],
        country="Philippines",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.priority in ("HIGH", "MED", "LOW")
