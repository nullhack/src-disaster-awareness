import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(country="Japan")
@example(country="Australia")
@example(country="France")
@given(country=st.text())
def test_level_4_incident_is_always_reportable_across_all_groups(country):
    ...

