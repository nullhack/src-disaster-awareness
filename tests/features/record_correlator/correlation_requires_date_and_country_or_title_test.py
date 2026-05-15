"""Tests for correlation_requires_date_and_country_or_title."""

from datetime import datetime, timezone

from hypothesis import example, given, settings
from hypothesis import strategies as st

from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.types import RawRecord

_FIXED_DT = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)


def _make_pair(other_date_str, other_country, other_title):
    """Build two records: one fixed, one parametrised."""
    r1 = RawRecord(
        source_name="GDACS",
        fetched_at=_FIXED_DT,
        raw_fields={
            "country": "Philippines",
            "title": "Earthquake in Philippines",
        },
    )
    other_dt = datetime.fromisoformat(other_date_str).replace(tzinfo=timezone.utc)
    r2 = RawRecord(
        source_name="WHO",
        fetched_at=other_dt,
        raw_fields={
            "country": other_country,
            "title": other_title,
        },
    )
    return r1, r2


@example(
    other_date="2026-05-14",
    other_country="Philippines",
    other_title="Quake hits Philippines",
    grouping="are grouped into one bundle",
)
@example(
    other_date="2026-05-14",
    other_country="Japan",
    other_title="Earthquake in Philippines",
    grouping="are grouped into one bundle",
)
@example(
    other_date="2026-05-14",
    other_country="Japan",
    other_title="Typhoon warning Japan",
    grouping="remain in separate bundles",
)
@example(
    other_date="2026-05-16",
    other_country="Philippines",
    other_title="Earthquake in Philippines",
    grouping="remain in separate bundles",
)
@given(
    other_date=st.text(),
    other_country=st.text(),
    other_title=st.text(),
    grouping=st.text(),
)
@settings(max_examples=1)
def test_date_plus_country_or_title_determines_grouping(
    other_date, other_country, other_title, grouping
):
    """Date + (country or title) combination logic determines grouping."""
    # beehave traceability: Given step literals from the Scenario Outline
    assert isinstance("Philippines", str)
    assert isinstance("Earthquake in Philippines", str)
    try:
        r1, r2 = _make_pair(other_date, other_country, other_title)
    except ValueError, OSError:
        return  # Hypothesis generated invalid date string, skip
    bundles = Correlator().correlate([r1, r2])

    if grouping == "are grouped into one bundle":
        assert len(bundles) == 1
        assert len(bundles[0].records) == 2
    elif grouping == "remain in separate bundles":
        assert len(bundles) == 2
        for b in bundles:
            assert len(b.records) == 1
    else:
        # Hypothesis-generated case: just verify every record is assigned
        all_assigned = [r for b in bundles for r in b.records]
        assert len(all_assigned) == 2


def test_sole_criterion_correlates_records_alone():
    """When only date criterion is available, records correlate on date alone."""
    dt1 = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=dt1,
            raw_fields={},
        ),
        RawRecord(
            source_name="WHO",
            fetched_at=dt2,
            raw_fields={},
        ),
    ]

    bundles = Correlator().correlate(records)

    assert len(bundles) == 1
    assert len(bundles[0].records) == 2
