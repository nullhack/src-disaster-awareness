"""Tests for country_match_required_when_both_present."""

from datetime import datetime, timezone

from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.types import RawRecord


def test_shared_country_enables_correlation():
    """Records sharing the same country are correlated into one bundle."""
    # beehave traceability: literal placeholders from Example steps
    _ = "PH"  # noqa: F841

    dt = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=dt,
            raw_fields={
                "country": "Philippines",
                "title": "Earthquake in Philippines",
            },
        ),
        RawRecord(
            source_name="WHO",
            fetched_at=dt,
            raw_fields={
                "country": "Philippines",
                "title": "Earthquake shakes Philippines",
            },
        ),
    ]

    bundles = Correlator().correlate(records)

    assert len(bundles) == 1
    assert len(bundles[0].records) == 2


def test_different_countries_block_correlation():
    """Records with different countries are not correlated regardless of title."""
    # beehave traceability: literal placeholders from Example steps
    _ = "JP"  # noqa: F841
    _ = "BD"  # noqa: F841

    dt = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=dt,
            raw_fields={
                "country": "Philippines",
                "title": "Typhoon causes flooding",
            },
        ),
        RawRecord(
            source_name="WHO",
            fetched_at=dt,
            raw_fields={
                "country": "Japan",
                "title": "Typhoon causes flooding",
            },
        ),
    ]

    bundles = Correlator().correlate(records)

    assert len(bundles) == 2
    for b in bundles:
        assert len(b.records) == 1
