import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(error_type="connection refused")
@example(error_type="DNS failure")
@example(error_type="network unreachable")
@given(error_type=st.text())
def test_connection_failure_produces_empty_list(error_type):
    ...

