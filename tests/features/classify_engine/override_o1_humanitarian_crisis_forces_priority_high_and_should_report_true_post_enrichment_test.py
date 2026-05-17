"""Tests."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_o1_forces_high_priority_after_ai_enrichment_detects_humanitarian_crisis():
    """Test o1 forces high priority after ai enrichment detects humanitarian crisis."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "France"},
    )
    ai_record = RawRecord(
        source_name="AI_Enrichment",
        fetched_at=now,
        raw_fields={"humanitarian_crisis": True},
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-EQ",
        records=[record, ai_record],
        country="France",
        ai_enriched=True,
    )

    result = ClassifyEngine().reevaluate_overrides(bundle)

    assert result.priority == "HIGH"


def test_o1_forces_should_report_true_post_enrichment():
    """Test o1 forces should report true post enrichment."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Green", "country": "France"},
    )
    ai_record = RawRecord(
        source_name="AI_Enrichment",
        fetched_at=now,
        raw_fields={"humanitarian_crisis": True},
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-EQ",
        records=[record, ai_record],
        country="France",
        incident_level=1,
        country_group="C",
        ai_enriched=True,
    )

    result = ClassifyEngine().reevaluate_overrides(bundle)

    assert result.should_report is True
