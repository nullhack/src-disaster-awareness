"""Tests for correlation_uses_three_matching_criteria."""

from datetime import datetime, timezone

from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.types import RawRecord


def test_date_within_one_day_passes_proximity():
    """Records within ±1 day of each other satisfy the date criterion."""
    dt1 = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=dt1,
            raw_fields={"country": "Philippines", "title": "Earthquake in Philippines"},
        ),
        RawRecord(
            source_name="WHO",
            fetched_at=dt2,
            raw_fields={"country": "Philippines", "title": "Earthquake in Philippines"},
        ),
    ]

    bundles = Correlator().correlate(records)

    assert len(bundles) == 1
    assert len(bundles[0].records) == 2


def test_shared_country_passes_overlap():
    """Records sharing a country satisfy the country overlap criterion."""
    dt = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=dt,
            raw_fields={"country": "Philippines", "title": "Earthquake strikes"},
        ),
        RawRecord(
            source_name="WHO",
            fetched_at=dt,
            raw_fields={"country": "Philippines", "title": "Typhoon warning"},
        ),
    ]

    bundles = Correlator().correlate(records)

    assert len(bundles) == 1
    assert len(bundles[0].records) == 2


def test_similar_titles_meet_levenshtein_threshold():
    """Records with title similarity ≥ 0.6 satisfy the title criterion."""
    dt = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=dt,
            raw_fields={
                "country": "Philippines",
                "title": "Earthquake strikes Philippines",
            },
        ),
        RawRecord(
            source_name="WHO",
            fetched_at=dt,
            raw_fields={
                "title": "Earthquake struck Philippines",
            },
        ),
    ]

    bundles = Correlator().correlate(records)

    assert len(bundles) == 1
    assert len(bundles[0].records) == 2
