"""Tests for overrides_are_independent_and_cumulative."""

import datetime

from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


def test_multiple_overrides_stack_on_the_same_bundle():
    """Test multiple overrides stack on the same bundle."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    # "affecting 3 countries": Philippines + Indonesia + Malaysia
    affected = ["Philippines", "Indonesia", "Malaysia"]
    num_affected = 3  # noqa: F841
    record = RawRecord(
        source_name="GDACS",
        fetched_at=now,
        raw_fields={
            "alertlevel": "Green",
            "country": "Philippines",
            "affectedcountries": affected,
        },
    )
    bundle = IncidentBundle(
        incident_id="20260514-PH-WF",
        records=[record],
        country="Philippines",
        disaster_type="WF",
    )

    result = ClassifyEngine().classify(bundle)

    # O2: multi-regional (3 countries) → HIGH
    # O4: environmental (WF) in Group A (Philippines) → HIGH
    assert "O2" in result.overrides
    assert "O4" in result.overrides
    assert result.priority == "HIGH"
