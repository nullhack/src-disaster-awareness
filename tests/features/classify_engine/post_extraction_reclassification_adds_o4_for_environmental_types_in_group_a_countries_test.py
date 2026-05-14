"""Tests."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_o4_is_added_when_environmental_disaster_resolved_to_group_a_country():
    """Test o4 is added when environmental disaster resolved to group a country."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "unknown"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-UNX-WF",
        records=[record],
        country="unknown",
        country_group="C",
        disaster_type="WF",
    )
    # Simulate AI extraction resolving country to Indonesia (Group A)
    bundle.country = "Indonesia"

    result = ClassifyEngine().classify(bundle)

    assert "O4" in result.overrides
    assert result.priority == "HIGH"
