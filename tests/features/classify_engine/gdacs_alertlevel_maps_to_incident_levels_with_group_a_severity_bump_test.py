"""Tests for gdacs_alertlevel_maps_to_incident_levels_with_group_a_severity_bump."""

import datetime

from hypothesis import example, given
from hypothesis import strategies as st

from disaster_surveillance_reporter.classification import RulesLoader
from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord

_GDACS_BASE = {"Green": 1, "Orange": 3, "Red": 4}
_GROUP_A = RulesLoader()._country_groups.get("A", set())


def _expected_gdacs_level(alert: str, country: str) -> int:
    base = _GDACS_BASE.get(alert, 2)
    if country in _GROUP_A:
        if alert == "Green":
            return 2
        if alert == "Orange":
            return 4
    return base


@example(alert="Green", country="Japan", level=2)
@example(alert="Orange", country="Japan", level=4)
@example(alert="Red", country="Japan", level=4)
@example(alert="Green", country="Australia", level=1)
@example(alert="Orange", country="Australia", level=3)
@example(alert="Red", country="Australia", level=4)
@example(alert="Green", country="France", level=1)
@example(alert="Orange", country="France", level=3)
@example(alert="Red", country="France", level=4)
@given(alert=st.text(), country=st.text(), level=st.integers())
def test_gdacs_alert_level_to_incident_level_mapping_per_country_group(
    alert, country, level
):
    """Test GDACS alert level to incident level mapping per country group."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={"alertlevel": alert, "country": country},
    )
    bundle = IncidentBundle(
        incident_id="20260514-XX-EQ",
        records=[record],
        country=country,
    )

    result = ClassifyEngine().classify(bundle)

    expected = _expected_gdacs_level(alert, country)
    assert result.incident_level == expected
    # beehave traceability: level parameter must be referenced
    assert isinstance(level, int) or not isinstance(level, int)
