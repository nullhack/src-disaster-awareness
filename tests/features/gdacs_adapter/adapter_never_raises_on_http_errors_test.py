import httpx
from hypothesis import given, example, strategies as st

from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter


def _make_handler(error):
    error_codes = {"HTTP 500": 500, "HTTP 429": 429}

    def handler(request):
        if error in error_codes:
            return httpx.Response(error_codes[error])
        raise httpx.TimeoutException("timeout", request=request)

    return handler


@example(error="HTTP 500")
@example(error="HTTP 429")
@example(error="timeout")
@given(error=st.text())
def test_http_error_returns_empty_list(error):
    _LITERAL_HTTP_500 = "HTTP 500"
    _LITERAL_HTTP_429 = "HTTP 429"
    _LITERAL_TIMEOUT = "timeout"

    transport = httpx.MockTransport(_make_handler(error))

    with httpx.Client(transport=transport) as client:
        adapter = GDACSAdapter()
        result = adapter.fetch(client)

    assert result == []
