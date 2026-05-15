"""Test: Supplementary search triggers on missing fields.

beehave traceability: "<field>"
"""

from hypothesis import given, example, strategies as st

from disaster_surveillance_reporter.pipeline import Pipeline


@example(field="country")
@example(field="disaster_type")
@example(field="country and type")
@given(field=st.sampled_from(["country", "disaster_type", "country and type", "none"]))
def test_pipeline_missing_field_triggers_search(field):
    """Given a bundle missing "<field>" after initial classification
    When the supplementary search trigger is evaluated
    Then supplementary search is triggered."""
    # beehave traceability: literal placeholder from the Scenario Outline step
    _ = "<field>"  # noqa: F841

    from disaster_surveillance_reporter.types import IncidentBundle, RawRecord
    import datetime as dt

    record = RawRecord(
        source_name="GDACS",
        fetched_at=dt.datetime(2026, 5, 15),
        raw_fields={"title": "Test Incident"},
    )

    if field == "country":
        bundle = IncidentBundle(
            incident_id="2026-05-15-UNX-OTH",
            records=[record],
            country=None,
            disaster_type="Earthquake",
        )
    elif field == "disaster_type":
        bundle = IncidentBundle(
            incident_id="2026-05-15-UNX-OTH",
            records=[record],
            country="Philippines",
            disaster_type=None,
        )
    elif field == "country and type":
        bundle = IncidentBundle(
            incident_id="2026-05-15-UNX-OTH",
            records=[record],
            country=None,
            disaster_type=None,
        )
    else:  # "none"
        bundle = IncidentBundle(
            incident_id="2026-05-15-UNX-OTH",
            records=[record],
            country="Philippines",
            disaster_type="Earthquake",
        )

    should_trigger = field in ("country", "disaster_type", "country and type")
    assert Pipeline._should_supplementary_search(bundle) is should_trigger
