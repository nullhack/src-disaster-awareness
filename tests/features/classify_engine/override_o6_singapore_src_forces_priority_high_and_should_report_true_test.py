"""Tests for override_o6_singapore_src_forces_priority_high_and_should_report_true."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_o6_triggers_on_singapore_keyword_and_forces_high_priority():
    """Test o6 triggers on singapore keyword and forces high priority."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="SRC",
        fetched_at=now,
        raw_fields={
            "text": "Alert for Singapore region regarding seismic activity",
            "country": "Singapore",
        },
    )
    bundle = IncidentBundle(
        incident_id="20260514-SG-EQ",
        records=[record],
        country="Singapore",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.priority == "HIGH"


def test_o6_forces_should_report_true_regardless_of_level():
    """Test o6 forces should report true regardless of level."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="SRC",
        fetched_at=now,
        raw_fields={
            "text": "SRC monitoring alert raised for the region",
            "country": "France",
        },
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-EQ",
        records=[record],
        country="France",
        incident_level=1,
        country_group="C",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.should_report is True
