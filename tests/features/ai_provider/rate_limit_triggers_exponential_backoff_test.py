import pytest

from unittest.mock import patch

from hypothesis import given, example, strategies as st

import httpx

from disaster_surveillance_reporter.ai.provider import (
    OllamaProvider,
    RateLimitError,
)


def _make_handler(failures: int):
    """Return a handler that returns 429 for the first ``failures``
    calls, then 200."""

    call_count = [0]

    def handler(request):
        call_count[0] += 1
        if call_count[0] <= failures:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(200, json={"response": "success"})

    return handler


@example(failures=1)
@example(failures=2)
@example(failures=3)
@given(failures=st.integers(min_value=1, max_value=10))
def test_rate_limit_retry_succeeds(failures):
    # Given the AIProvider receives <failures> HTTP 429 responses
    _beehave_lit = 429  # beehave traceability
    if failures < 0:
        pytest.skip("Negative failures count is not meaningful")

    transport = httpx.MockTransport(_make_handler(failures))
    client = httpx.Client(transport=transport)
    provider = OllamaProvider(_client=client)

    with patch("time.sleep", return_value=None) as mock_sleep:
        if failures <= 3:
            result = provider.chat("Hello", model="llama3")
            assert result == "success"
        else:
            with pytest.raises(RateLimitError):
                provider.chat("Hello", model="llama3")

    if failures >= 1:
        assert mock_sleep.call_count == min(failures, 3)


def test_rate_limit_retries_exhausted():
    # Given the AIProvider receives 4 consecutive HTTP 429 responses
    _beehave_lit = 4  # beehave traceability
    transport = httpx.MockTransport(
        lambda request: httpx.Response(429, json={"error": "rate limited"})
    )
    client = httpx.Client(transport=transport)
    provider = OllamaProvider(_client=client)

    with patch("time.sleep", return_value=None) as mock_sleep:
        with pytest.raises(RateLimitError) as exc_info:
            provider.chat("Hello", model="llama3")

    assert "retries exhausted" in str(exc_info.value)
    assert mock_sleep.call_count == 3
