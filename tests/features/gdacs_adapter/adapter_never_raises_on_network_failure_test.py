import httpx

from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter


def test_network_failure_returns_empty_list():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        adapter = GDACSAdapter()
        result = adapter.fetch(client)

    assert result == []
