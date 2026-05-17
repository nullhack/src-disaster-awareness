"""Tests."""

import datetime

from hypothesis import example, given
from hypothesis import strategies as st

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


@example(disaster_type="WF")
@example(disaster_type="DR")
@example(disaster_type="FL")
@given(disaster_type=st.sampled_from(["WF", "DR", "FL"]))
def test_o4_triggers_for_environmental_disaster_type_in_group_a_country(disaster_type):
    """Test o4 triggers for environmental disaster type in group a country."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "Japan"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-JP-XX",
        records=[record],
        country="Japan",
        disaster_type=disaster_type,
    )

    result = ClassifyEngine().classify(bundle)

    assert "O4" in result.overrides


def test_o4_does_not_trigger_for_environmental_disaster_in_group_b_country():
    """Test o4 does not trigger for environmental disaster in group b country."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "Australia"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-AU-FL",
        records=[record],
        country="Australia",
        disaster_type="FL",
    )

    result = ClassifyEngine().classify(bundle)

    assert "O4" not in result.overrides
