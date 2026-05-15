import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(title="Magnitude 7.2 earthquake", country="Philippines", disaster_type="Earthquake", expected_query="Magnitude 7.2 earthquake Philippines Earthquake latest news")
@example(title="Disease outbreak report", country="", disaster_type="Flood", expected_query="Disease outbreak report Flood latest news")
@example(title="Flood warning issued", country="", disaster_type="", expected_query="Flood warning issued disaster emergency latest news")
@example(title="disaster incident", country="Japan", disaster_type="Earthquake", expected_query="disaster incident Japan Earthquake latest news")
@given(title=st.text(), country=st.text(), disaster_type=st.text(), expected_query=st.text())
def test_pipeline_search_query_matches_template(title, country, disaster_type, expected_query):
    ...

