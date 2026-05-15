from hypothesis import given, example, strategies as st

@example(failures=1)
@example(failures=2)
@example(failures=3)
@given(failures=st.integers())
def test_rate_limit_retry_succeeds(failures):
    ...

def test_rate_limit_retries_exhausted():
    ...

