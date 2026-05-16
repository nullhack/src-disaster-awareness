import httpx
from hypothesis import given, example, strategies as st

from disaster_surveillance_reporter.adapters.eonet import EONETAdapter


@example(error_type="connection refused")
@example(error_type="DNS failure")
@example(error_type="network unreachable")
@given(error_type=st.text())
def test_eonet_connection_failure_yields_empty_list(error_type):
    def handler(request):
        raise httpx.ConnectError(error_type, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)
    assert result == []
