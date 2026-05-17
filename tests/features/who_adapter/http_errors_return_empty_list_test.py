import httpx
from hypothesis import given, example, strategies as st

from disaster_surveillance_reporter.adapters.who import WHOAdapter


@example(status_code=500)
@example(status_code=503)
@example(status_code=429)
@given(status_code=st.integers())
def test_server_error_produces_empty_list(status_code):
    def handler(request):
        return httpx.Response(status_code)

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = WHOAdapter()
        result = adapter.fetch(client)

    assert result == []


def test_request_timeout_yields_empty_list():
    def handler(request):
        raise httpx.TimeoutException("timeout", request=request)

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = WHOAdapter()
        result = adapter.fetch(client)

    assert result == []
