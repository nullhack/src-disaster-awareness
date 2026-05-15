import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(field="country")
@example(field="disaster_type")
@example(field="country and type")
@given(field=st.text())
def test_pipeline_missing_field_triggers_search(field):
    ...

