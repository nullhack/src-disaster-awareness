import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(disaster_type="WF")
@example(disaster_type="DR")
@example(disaster_type="FL")
@given(disaster_type=st.text())
def test_o4_triggers_for_environmental_disaster_type_in_group_a_country(disaster_type):
    ...

@pytest.mark.skip(reason="not implemented")
def test_o4_does_not_trigger_for_environmental_disaster_in_group_b_country():
    ...

