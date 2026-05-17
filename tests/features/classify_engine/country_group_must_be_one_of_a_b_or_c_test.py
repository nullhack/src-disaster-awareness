"""Tests for country_group_must_be_one_of_a_b_or_c."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_classified_bundle_always_has_a_valid_country_group():
    """Test classified bundle always has a valid country group."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "Japan"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record],
        country="Japan",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.country_group in ("A", "B", "C")
