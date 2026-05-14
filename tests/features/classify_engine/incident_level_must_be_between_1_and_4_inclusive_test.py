"""Tests for incident_level_must_be_between_1_and_4_inclusive."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_classified_bundle_always_has_a_valid_incident_level():
    """Test classified bundle always has a valid incident level."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Orange", "country": "Japan"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record],
        country="Japan",
    )

    result = ClassifyEngine().classify(bundle)

    assert 1 <= result.incident_level <= 4
