from hypothesis import given, example, strategies as st

@example(source="GDACS", raw_date="2026-05-14", date_component=20260514)
@example(source="WHO", raw_date="2026-05-13", date_component=20260513)
@example(source="GDELT", raw_date="20260512T120000z", date_component=20260512)
@example(source="DDG-NEWS", raw_date="2026-05-11", date_component=20260511)
@given(source=st.text(), raw_date=st.text(), date_component=st.integers())
def test_source_date_field_recognized(source, raw_date, date_component):
    ...

def test_earliest_source_date_wins():
    ...

def test_no_source_date_falls_back():
    ...

