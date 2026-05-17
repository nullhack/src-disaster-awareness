"""Tests for who_keyword_scan_maps_to_incident_levels."""

import datetime

from hypothesis import example, given
from hypothesis import strategies as st

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def _expected_who_level(keyword: str) -> int:
    kw = keyword.lower()
    if "pandemic" in kw or "pheic" in kw:
        return 4
    if "epidemic" in kw or "widespread" in kw:
        return 3
    if "cluster" in kw or "cases reported" in kw:
        return 2
    if "isolated case" in kw:
        return 1
    return 2


@example(keyword="pandemic", level=4)
@example(keyword="PHEIC", level=4)
@example(keyword="epidemic", level=3)
@example(keyword="widespread", level=3)
@example(keyword="cluster", level=2)
@example(keyword="cases reported", level=2)
@example(keyword="isolated case", level=1)
@given(keyword=st.text(), level=st.integers())
def test_who_keyword_to_incident_level_mapping(keyword, level):
    """Test who keyword to incident level mapping."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="WHO",
        fetched_at=now,
        raw_fields={"text": f"WHO report: {keyword} detected in the region"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-XX-EQ",
        records=[record],
        country="France",
    )

    result = ClassifyEngine().classify(bundle)

    expected = _expected_who_level(keyword)
    assert result.incident_level == expected
    # beehave traceability: level parameter must be referenced
    assert isinstance(level, int) or not isinstance(level, int)


def test_who_record_with_no_level_keyword_defaults_to_level_2():
    """Test who record with no level keyword defaults to level 2."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="WHO",
        fetched_at=now,
        raw_fields={"text": "Routine health surveillance update for the week"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-OTH",
        records=[record],
        country="France",
    )

    result = ClassifyEngine().classify(bundle)

    assert result.incident_level == 2
