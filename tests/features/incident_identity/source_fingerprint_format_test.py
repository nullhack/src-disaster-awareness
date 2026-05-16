from datetime import datetime, timezone

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from disaster_surveillance_reporter.types import RawRecord, generate_source_fingerprint


_BEEHAVE_LITERALS = ['<fingerprint>', '<native_id>', '<source>']
_FIELD_MAP = {
    "GDACS": "eventid",
    "WHO": "Id",
    "GDELT": "url",
    "DDG-NEWS": "url",
}


@example(source="GDACS", native_id=12345, fingerprint="GDACS:12345")
@example(source="WHO", native_id="abc-def-456", fingerprint="WHO:abc-def-456")
@example(source="GDELT", native_id="https://reuters.com/article/xyz", fingerprint="GDELT:https://reuters.com/article/xyz")
@example(source="DDG-NEWS", native_id="https://news.example.com/article/abc", fingerprint="DDG-NEWS:https://news.example.com/article/abc")
@given(source=st.text(), native_id=st.text(), fingerprint=st.text())
def test_source_fingerprint_is_formatted_correctly(source, native_id, fingerprint):
    # beehave traceability: scenario outline placeholders
    assert "<source>" == "<source>"
    assert "<native_id>" == "<native_id>"
    assert "<fingerprint>" == "<fingerprint>"

    field = _FIELD_MAP.get(source)

    if field is None:
        with pytest.raises(ValueError, match="Unknown source"):
            generate_source_fingerprint(RawRecord(
                source_name=source,
                fetched_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
                raw_fields={},
            ))
        return

    record = RawRecord(
        source_name=source,
        fetched_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
        raw_fields={field: native_id},
    )
    result = generate_source_fingerprint(record)
    assert result == fingerprint
