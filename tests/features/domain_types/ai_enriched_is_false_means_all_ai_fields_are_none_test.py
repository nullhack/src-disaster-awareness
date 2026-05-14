"""Tests for ai_enriched=False invariant on IncidentBundle."""

from datetime import datetime, timezone

import pytest

from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_unenriched_bundle_has_no_ai_generated_values():
    """Verify that an unenriched bundle has all AI fields set to None."""
    # Given an IncidentBundle where ai_enriched is False
    record = RawRecord(
        source_name="GDACS",
        fetched_at=datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc),
        raw_fields={"eventtype": "EQ", "alertlevel": "Orange"},
    )

    # Default construction: ai_enriched is False, all AI fields are None
    bundle = IncidentBundle(
        incident_id="20260514-PH-EQ",
        records=[record],
    )
    assert bundle.ai_enriched is False
    assert bundle.summary is None
    assert bundle.rationale is None
    assert bundle.estimated_affected is None
    assert bundle.estimated_deaths is None

    # The invariant must be enforced: ai_enriched=False with non-None AI
    # fields is an invalid state and must be rejected at construction.
    with pytest.raises(ValueError, match="ai_enriched=False"):
        IncidentBundle(
            incident_id="20260514-PH-EQ",
            records=[record],
            ai_enriched=False,
            summary="An AI-generated summary",
        )
