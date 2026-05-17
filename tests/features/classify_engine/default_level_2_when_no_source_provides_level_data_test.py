"""Tests for default_level_2_when_no_source_provides_level_data."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_bundle_with_no_source_level_data_defaults_to_level_2():
    """Test bundle with no source level data defaults to level 2."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    # Records with no level-relevant fields
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"country": "France", "population": 65_000_000},
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-OTH",
        records=[record],
        country="France",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.incident_level == 2
