"""Tests."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_priority_upgrades_when_country_is_resolved_from_unknown_to_group_a():
    """Test priority upgrades when country is resolved from unknown to group a."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "unknown"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-UNX-EQ",
        records=[record],
        country="unknown",
        country_group="C",
        disaster_type="EQ",
        incident_level=2,
        priority="LOW",
    )
    # Simulate AI extraction resolving country to Philippines (Group A)
    bundle.country = "Philippines"

    result = ClassifyEngine().classify(bundle)

    assert result.country_group == "A"
    # Level 2 + Group A → MED priority
    assert result.priority == "MED"
