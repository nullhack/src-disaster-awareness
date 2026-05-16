from datetime import datetime, timedelta, timezone

from hypothesis import assume, example, given
from hypothesis import strategies as st

from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


@given(
    should_report=st.booleans(),
    active=st.booleans(),
    missing_fields=st.booleans(),
    triggered=st.sampled_from(["triggered", "not triggered"]),
)
@example(should_report=True, active=True, missing_fields=False, triggered="triggered")
@example(should_report=True, active=False, missing_fields=True, triggered="triggered")
@example(should_report=True, active=True, missing_fields=True, triggered="triggered")
@example(should_report=False, active=True, missing_fields=False, triggered="not triggered")
@example(should_report=True, active=False, missing_fields=False, triggered="not triggered")
@example(should_report=False, active=False, missing_fields=True, triggered="not triggered")
def test_ddg_search_triggered_by_gate_condition(
    should_report, active, missing_fields, triggered
):
    _should_report = "<should_report>"
    _active = "<active>"
    _missing_fields = "<missing_fields>"
    _triggered = "<triggered>"
    expected = (
        "triggered"
        if (should_report and (active or missing_fields))
        else "not triggered"
    )
    assume(triggered == expected)

    now = datetime.now(tz=timezone.utc)
    last_updated = now - timedelta(days=3 if active else 10)
    bundle = IncidentBundle(
        incident_id="test-gate",
        records=[
            RawRecord(
                source_name="GDACS",
                fetched_at=now,
                raw_fields={"eventid": "456"},
            )
        ],
        should_report=should_report,
        country=None if missing_fields else "Philippines",
        disaster_type=None if missing_fields else "Earthquake",
        last_updated=last_updated,
    )
    result = Pipeline._should_supplementary_search(bundle)
    assert result == (triggered == "triggered")
