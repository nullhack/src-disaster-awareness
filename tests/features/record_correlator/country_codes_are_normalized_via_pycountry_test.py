"""Tests for country codes are normalized via pycountry."""

import datetime

from disaster_surveillance_reporter.correlation.correlate import _normalize_country
from disaster_surveillance_reporter.types import RawRecord


def test_country_name_normalized_to_iso_code():
    """Country name 'Philippines' normalizes to ISO code 'PH'."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="WHO",
        fetched_at=now,
        raw_fields={"country": "Philippines"},
    )

    result = _normalize_country(record)

    assert result == "PH"


def test_unknown_country_name_treated_as_no_country():
    """Unknown country name returns None when pycountry cannot resolve it."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="WHO",
        fetched_at=now,
        raw_fields={"country": "NonExistentia"},
    )

    result = _normalize_country(record)

    assert result is None
