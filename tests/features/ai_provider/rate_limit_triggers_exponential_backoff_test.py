import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(failures=1)
@example(failures=2)
@example(failures=3)
@given(failures=st.integers())
def test_rate_limit_retry_succeeds(failures):
    ...

@pytest.mark.skip(reason="not implemented")
def test_rate_limit_retries_exhausted():
    ...

