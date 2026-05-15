from hypothesis import given, example, strategies as st

@example(source_date="2026-05-14", country_code="PH", type_code="EQ", expected_id="20260514-PH-EQ")
@example(source_date="2026-05-14", country_code="UNX", type_code="FL", expected_id="20260514-UNX-FL")
@example(source_date="2026-05-14", country_code="ID", type_code="OTH", expected_id="20260514-ID-OTH")
@given(source_date=st.text(), country_code=st.text(), type_code=st.text(), expected_id=st.text())
def test_incident_id_format_stable(source_date, country_code, type_code, expected_id):
    ...

