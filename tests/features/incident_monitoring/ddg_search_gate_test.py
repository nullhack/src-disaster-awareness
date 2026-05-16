import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(should_report=True, active=True, missing_fields=False, triggered="triggered")
@example(should_report=True, active=False, missing_fields=True, triggered="triggered")
@example(should_report=True, active=True, missing_fields=True, triggered="triggered")
@example(should_report=False, active=True, missing_fields=False, triggered="not triggered")
@example(should_report=True, active=False, missing_fields=False, triggered="not triggered")
@example(should_report=False, active=False, missing_fields=True, triggered="not triggered")
@given(should_report=st.booleans(), active=st.booleans(), missing_fields=st.booleans(), triggered=st.text())
def test_ddg_search_triggered_by_gate_condition(should_report, active, missing_fields, triggered):
    ...

