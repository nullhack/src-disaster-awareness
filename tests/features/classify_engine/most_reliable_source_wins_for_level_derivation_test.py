import pytest

"""Tests for most_reliable_source_wins_for_level_derivation."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_gdacs_level_wins_over_who_gdelt_and_eonet_levels():
    """Test gdacs level wins over who gdelt and eonet levels."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    gdacs_record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": "Orange", "country": "Australia"},
    )
    who_record = RawRecord(
        source_name="WHO",
        fetched_at=now,
        raw_fields={"text": "pandemic declared in the region"},
    )
    gdelt_record = RawRecord(
        source_name="GDELT",
        fetched_at=now,
        raw_fields={"title": "devastating disaster hits continent"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-AU-EQ",
        records=[gdacs_record, who_record, gdelt_record],
        country="Australia",
    )

    result = ClassifyEngine().classify(bundle)

    # GDACS Orange→3 (Group B). WHO pandemic→4, GDELT devastating→4.
    # Most reliable source (GDACS) wins → level 3.
    assert result.incident_level == 3


def test_who_level_wins_over_eonet_when_gdacs_provides_no_level():
    """Test who level wins over eonet when gdacs provides no level."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    gdacs_record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"country": "France"},  # No alertlevel
    )
    who_record = RawRecord(
        source_name="WHO",
        fetched_at=now,
        raw_fields={"text": "pandemic alert issued by WHO"},
    )
    gdelt_record = RawRecord(
        source_name="GDELT",
        fetched_at=now,
        raw_fields={"title": "major disruption reported"},
    )
    bundle = IncidentBundle(
        incident_id="20260514-FR-EQ",
        records=[gdacs_record, who_record, gdelt_record],
        country="France",
    )

    result = ClassifyEngine().classify(bundle)

    # GDACS has no level → fall through to WHO (pandemic → 4).
    # EONET volcano → 3.  WHO wins → level 4.
    assert result.incident_level == 4

