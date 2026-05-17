import httpx
from hypothesis import assume, given, example, strategies as st

from disaster_surveillance_reporter.adapters.eonet import EONETAdapter


@example(status_code=500)
@example(status_code=503)
@example(status_code=429)
@given(status_code=st.integers())
def test_eonet_server_error_yields_empty_list(status_code):
    assume(status_code >= 100)
    transport = httpx.MockTransport(
        lambda req: httpx.Response(status_code)
    )
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)
    assert result == []


def test_eonet_request_timeout_yields_empty_list():
    def handler(request):
        raise httpx.TimeoutException("timeout", request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)
    assert result == []
