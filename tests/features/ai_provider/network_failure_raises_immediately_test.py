from hypothesis import given, example, strategies as st

@example(network_error="connection refused")
@example(network_error="DNS failure")
@example(network_error="connection timeout")
@given(network_error=st.text())
def test_network_failure_raises_without_retry(network_error):
    ...

