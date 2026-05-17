import pytest

from unittest.mock import MagicMock

from hypothesis import given, example, strategies as st

import httpx

from disaster_surveillance_reporter.ai.provider import (
    OllamaProvider,
    NetworkError,
)


_NETWORK_ERROR_EXCEPTIONS = {
    "connection refused": httpx.ConnectError("Connection refused"),
    "DNS failure": httpx.ConnectError("DNS resolution failed"),
    "connection timeout": httpx.ConnectTimeout("Connection timed out"),
}


@example(network_error="connection refused")
@example(network_error="DNS failure")
@example(network_error="connection timeout")
@given(network_error=st.sampled_from(["connection refused", "DNS failure", "connection timeout"]))
def test_network_failure_raises_without_retry(network_error):
    exc = _NETWORK_ERROR_EXCEPTIONS.get(network_error)
    if exc is None:
        pytest.skip(f"Unknown network error: {network_error!r}")

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = exc

    provider = OllamaProvider(_client=mock_client)

    with pytest.raises(NetworkError):
        provider.chat("Hello", model="llama3")
