"""Tests for level_4_always_produces_should_report_true_regardless_of_country_group."""

import datetime

from hypothesis import example, given
from hypothesis import strategies as st

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


@example(country="Japan")
@example(country="Australia")
@example(country="France")
@given(country=st.text())
def test_level_4_incident_is_always_reportable_across_all_groups(country):
    """Test level 4 incident is always reportable across all groups."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Red", "country": country},
    )
    bundle = IncidentBundle(
        incident_id="20260514-XX-EQ",
        records=[record],
        country=country,
    )

    result = ClassifyEngine().classify(bundle)

    assert result.should_report is True
