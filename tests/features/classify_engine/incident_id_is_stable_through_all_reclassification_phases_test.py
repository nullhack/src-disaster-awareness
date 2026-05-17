"""Tests for incident_id_is_stable_through_all_reclassification_phases."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_incident_id_does_not_change_during_reclassification():
    """Test incident id does not change during reclassification."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "unknown"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-UNX-FL",
        records=[record],
        country="unknown",
        disaster_type="FL",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.incident_id == "20260514-UNX-FL"
