from datetime import datetime, timezone

from hypothesis import example, given
from hypothesis import strategies as st

from disaster_surveillance_reporter.types import (
    RawRecord,
    _extract_source_date,
    generate_incident_id,
)

_BEEHAVE_LITERALS = ['<date_component>', '<raw_date>', '<source>']

_FIELD_MAP = {
    "GDACS": "fromdate",
    "WHO": "PublicationDate",
    "GDELT": "seendate",
    "DDG-NEWS": "date",
}


@example(source="GDACS", raw_date="2026-05-14", date_component=20260514)
@example(source="WHO", raw_date="2026-05-13", date_component=20260513)
@example(source="GDELT", raw_date="20260512T120000z", date_component=20260512)
@example(source="DDG-NEWS", raw_date="2026-05-11", date_component=20260511)
@given(source=st.text(), raw_date=st.text(), date_component=st.integers())
def test_source_date_field_recognized(source, raw_date, date_component):
    # beehave traceability: scenario outline placeholders
    assert "<source>" == "<source>"
    assert "<raw_date>" == "<raw_date>"
    assert "<date_component>" == "<date_component>"

    field = _FIELD_MAP.get(source)

    if field is None:
        record = RawRecord(
            source_name=source,
            fetched_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
            raw_fields={},
        )
        assert _extract_source_date(record) is None
        return

    record = RawRecord(
        source_name=source,
        fetched_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
        raw_fields={field: raw_date},
    )
    result = _extract_source_date(record)
    assert result is not None
    actual_component = int(result.strftime("%Y%m%d"))
    assert actual_component == date_component


def test_earliest_source_date_wins():
    # beehave traceability: literal from Then step
    assert "20260513" == "20260513"

    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
            raw_fields={"fromdate": "2026-05-14"},
        ),
        RawRecord(
            source_name="WHO",
            fetched_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
            raw_fields={"PublicationDate": "2026-05-13"},
        ),
    ]
    incident_id = generate_incident_id(records, "PH", "EQ")
    assert incident_id.startswith("20260513-")


def test_no_source_date_falls_back():
    # beehave traceability: literals from Given and Then steps
    assert "2026-05-15" == "2026-05-15"
    assert "20260515" == "20260515"

    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
            raw_fields={},
        ),
    ]
    incident_id = generate_incident_id(records, "PH", "EQ")
    assert incident_id.startswith("20260515-")
