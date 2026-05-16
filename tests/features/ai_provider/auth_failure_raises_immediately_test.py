import pytest

import httpx

from disaster_surveillance_reporter.ai.provider import (
    OllamaProvider,
    AuthenticationError,
)


def test_auth_failure_raises_without_retry():
    """HTTP 401 raises AuthenticationError immediately with no retries."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"error": "Unauthorized"})
    )
    client = httpx.Client(transport=transport)
    provider = OllamaProvider(_client=client)

    with pytest.raises(AuthenticationError):
        provider.chat("Hello", model="llama3")
