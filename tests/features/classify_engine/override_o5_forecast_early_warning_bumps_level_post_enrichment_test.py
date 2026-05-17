"""Tests for override_o5_forecast_early_warning_bumps_level_post_enrichment."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_o5_bumps_level_by_one_via_gdacs_istemporary_flag():
    """Test o5 bumps level by one via gdacs istemporary flag."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "France", "istemporary": True},
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-EQ",
        records=[record],
        country="France",
        incident_level=2,
        country_group="C",
        ai_enriched=True,
    )

    result = ClassifyEngine().reevaluate_overrides(bundle)

    assert result.incident_level == 3


def test_o5_forces_should_report_true():
    """Test o5 forces should report true."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "France", "istemporary": True},
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-EQ",
        records=[record],
        country="France",
        incident_level=1,
        country_group="C",
        ai_enriched=True,
    )

    result = ClassifyEngine().reevaluate_overrides(bundle)

    assert result.should_report is True
