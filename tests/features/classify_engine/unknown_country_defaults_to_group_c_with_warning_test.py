"""Tests for unknown_country_defaults_to_group_c_with_warning."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_unrecognized_country_code_assigned_to_group_c():
    """Test unrecognized country code assigned to group c."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "ZZ"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-ZZ-OTH",
        records=[record],
        country="ZZ",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.country_group == "C"
