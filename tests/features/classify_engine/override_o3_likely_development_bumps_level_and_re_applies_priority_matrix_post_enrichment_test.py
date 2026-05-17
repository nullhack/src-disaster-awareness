"""Tests."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_o3_bumps_level_and_reapplies_priority_matrix():
    """Test o3 bumps level and reapplies priority matrix."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Orange", "country": "Australia"},
    )
    ai_record = RawRecord(
        source_name="AI_Enrichment",
        fetched_at=now,
        raw_fields={"likely_development": True},
    )
    bundle = IncidentBundle(
        incident_id="20260514-AU-EQ",
        records=[record, ai_record],
        country="Australia",
        incident_level=3,
        country_group="B",
        ai_enriched=True,
    )

    result = ClassifyEngine().reevaluate_overrides(bundle)

    # Level 3 + O3 bump → Level 4 (capped at 4).
    # Level 4 in Group B → HIGH priority.
    assert result.incident_level == 4
    assert result.priority == "HIGH"


def test_o3_bump_is_capped_at_level_4():
    """Test o3 bump is capped at level 4."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Red", "country": "Japan"},
    )
    ai_record = RawRecord(
        source_name="AI_Enrichment",
        fetched_at=now,
        raw_fields={"likely_development": True},
    )
    bundle = IncidentBundle(
        incident_id="20260514-JP-EQ",
        records=[record, ai_record],
        country="Japan",
        incident_level=4,
        country_group="A",
        ai_enriched=True,
    )

    result = ClassifyEngine().reevaluate_overrides(bundle)

    # Already Level 4, bump capped — stays at 4.
    assert result.incident_level == 4
