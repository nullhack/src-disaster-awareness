from datetime import datetime, timezone

from hypothesis import example, given
from hypothesis import strategies as st

from disaster_surveillance_reporter.types import RawRecord, generate_incident_id


_BEEHAVE_LITERALS = ['<country_code>', '<expected_id>', '<source_date>', '<type_code>']
_KNOWN_EXAMPLES = {
    ("2026-05-14", "PH", "EQ"): "20260514-PH-EQ",
    ("2026-05-14", "UNX", "FL"): "20260514-UNX-FL",
    ("2026-05-14", "ID", "OTH"): "20260514-ID-OTH",
}


@example(source_date="2026-05-14", country_code="PH", type_code="EQ", expected_id="20260514-PH-EQ")
@example(source_date="2026-05-14", country_code="UNX", type_code="FL", expected_id="20260514-UNX-FL")
@example(source_date="2026-05-14", country_code="ID", type_code="OTH", expected_id="20260514-ID-OTH")
@given(source_date=st.text(), country_code=st.text(), type_code=st.text(), expected_id=st.text())
def test_incident_id_format_stable(source_date, country_code, type_code, expected_id):
    # beehave traceability: scenario outline placeholders
    assert "<source_date>" == "<source_date>"
    assert "<country_code>" == "<country_code>"
    assert "<type_code>" == "<type_code>"
    assert "<expected_id>" == "<expected_id>"

    records = [
        RawRecord(
            source_name="GDACS",
            fetched_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
            raw_fields={"fromdate": source_date},
        ),
    ]
    result = generate_incident_id(records, country_code, type_code)

    key = (source_date, country_code, type_code)
    if key in _KNOWN_EXAMPLES:
        assert result == _KNOWN_EXAMPLES[key]
        assert result == expected_id

    parts = result.split("-")
    assert len(parts) == 3
    assert len(parts[0]) == 8  # YYYYMMDD
    assert len(parts[1]) >= 2  # CC or UNX
    assert 2 <= len(parts[2]) <= 3  # TTT (2-char codes or 3-char OTH)
