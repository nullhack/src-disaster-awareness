from hypothesis import given, example, strategies as st

@example(status_code=500)
@example(status_code=503)
@example(status_code=429)
@given(status_code=st.integers())
def test_server_error_produces_empty_list(status_code):
    ...

def test_request_timeout_yields_empty_list():
    ...

