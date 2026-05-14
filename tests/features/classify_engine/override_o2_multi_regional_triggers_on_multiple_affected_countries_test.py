"""Tests for override_o2_multi_regional_triggers_on_multiple_affected_countries."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_o2_triggers_when_gdacs_alert_affects_multiple_countries():
    """Test o2 triggers when gdacs alert affects multiple countries."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    # "more than 1 affected country"
    affected = ["France", "Germany", "Italy"]
    affected_count = 1 + 2  # noqa: F841
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={
            "alertlevel": "Green",
            "country": "France",
            "affectedcountries": affected,
        },
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-EQ",
        records=[record],
        country="France",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.priority == "HIGH"


def test_o2_forces_should_report_true_on_multi_regional_alert():
    """Test o2 forces should report true on multi regional alert."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    # "affecting 3 countries"
    affected_countries = ["France", "Germany", "Spain"]
    num_affected = 3  # noqa: F841
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={
            "alertlevel": "Green",
            "country": "France",
            "affectedcountries": affected_countries,
        },
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-EQ",
        records=[record],
        country="France",
        incident_level=2,
        country_group="C",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.should_report is True
