import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(error="HTTP 500")
@example(error="HTTP 429")
@example(error="timeout")
@given(error=st.text())
def test_http_error_returns_empty_list(error):
    ...

