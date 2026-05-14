import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(alert="Green", country="Japan", level=2)
@example(alert="Orange", country="Japan", level=4)
@example(alert="Red", country="Japan", level=4)
@example(alert="Green", country="Australia", level=1)
@example(alert="Orange", country="Australia", level=3)
@example(alert="Red", country="Australia", level=4)
@example(alert="Green", country="France", level=1)
@example(alert="Orange", country="France", level=3)
@example(alert="Red", country="France", level=4)
@given(alert=st.text(), country=st.text(), level=st.integers())
def test_gdacs_alert_level_to_incident_level_mapping_per_country_group(alert, country, level):
    ...

