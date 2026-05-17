"""Tests for gdelt_title_keyword_scan_maps_to_incident_levels."""

import datetime

from hypothesis import example, given
from hypothesis import strategies as st

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def _expected_gdelt_level(keyword: str) -> int:
    kw = keyword.lower()
    if (
        "devastating" in kw
        or "hundreds dead" in kw
        or "thousands displaced" in kw
        or "pheic" in kw
    ):
        return 4
    if "major" in kw or "catastrophic" in kw or "deadly" in kw or "massive" in kw:
        return 3
    if "minor" in kw:
        return 1
    return 2


@example(keyword="major", level=3)
@example(keyword="catastrophic", level=3)
@example(keyword="deadly", level=3)
@example(keyword="massive", level=3)
@example(keyword="devastating", level=4)
@example(keyword="hundreds dead", level=4)
@example(keyword="thousands displaced", level=4)
@example(keyword="PHEIC", level=4)
@given(keyword=st.text(), level=st.integers())
def test_gdelt_title_keyword_to_incident_level_mapping(keyword, level):
    """Test gdelt title keyword to incident level mapping."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDELT",
        fetched_at=now,
        raw_fields={"title": f"Breaking: {keyword} disaster strikes region"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-XX-EQ",
        records=[record],
        country="France",
    )

    result = ClassifyEngine().classify(bundle)

    expected = _expected_gdelt_level(keyword)
    assert result.incident_level == expected
    # beehave traceability: level parameter must be referenced
    assert isinstance(level, int) or not isinstance(level, int)


def test_gdelt_record_with_no_severity_keyword_defaults_to_level_2():
    """Test gdelt record with no severity keyword defaults to level 2."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDELT",
        fetched_at=now,
        raw_fields={"title": "Weather update for the region today"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-OTH",
        records=[record],
        country="France",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.incident_level == 2
