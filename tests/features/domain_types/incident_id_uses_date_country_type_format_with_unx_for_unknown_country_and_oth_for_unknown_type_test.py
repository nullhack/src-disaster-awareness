from hypothesis import given, example, strategies as st

@example(country="Philippines", disaster_type="Earthquake", expected_id="20260514-PH-EQ")
@example(country="unknown", disaster_type="Flood", expected_id="20260514-UNX-FL")
@example(country="Indonesia", disaster_type="unknown", expected_id="20260514-ID-OTH")
@given(country=st.text(), disaster_type=st.text(), expected_id=st.text())
def test_incident_id_format_varies_by_country_and_type(country, disaster_type, expected_id):
    ...

