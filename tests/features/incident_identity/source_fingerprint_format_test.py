from hypothesis import given, example, strategies as st

@example(source="GDACS", native_id=12345, fingerprint="GDACS:12345")
@example(source="WHO", native_id="abc-def-456", fingerprint="WHO:abc-def-456")
@example(source="GDELT", native_id="https://reuters.com/article/xyz", fingerprint="GDELT:https://reuters.com/article/xyz")
@example(source="DDG-NEWS", native_id="https://news.example.com/article/abc", fingerprint="DDG-NEWS:https://news.example.com/article/abc")
@given(source=st.text(), native_id=st.text(), fingerprint=st.text())
def test_source_fingerprint_is_formatted_correctly(source, native_id, fingerprint):
    ...

