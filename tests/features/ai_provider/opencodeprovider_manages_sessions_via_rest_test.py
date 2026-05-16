import os
import pytest

from unittest.mock import patch

import httpx

from disaster_surveillance_reporter.ai.provider import (
    OpencodeProvider,
)


def test_opencodeprovider_creates_session_and_sends_message():
    """Happy path: create session via POST /session, then send message."""
    session_id = "session-abc123"
    responses_seen = []

    def handler(request):
        responses_seen.append((request.method, request.url.path))
        if request.url.path == "/session":
            # Verify basic auth header is present
            auth_header = request.headers.get("authorization", "")
            assert "Basic " in auth_header
            return httpx.Response(200, json={"id": session_id})
        if request.url.path == f"/session/{session_id}/message":
            return httpx.Response(
                200,
                json={"parts": [{"type": "text", "text": "Hello from opencode"}]},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    with patch.dict(
        os.environ,
        {
            "OPENCODE_SERVER_PASSWORD": "test-pw",
            "OPENCODE_BASE_URL": "http://localhost:4096",
        },
    ):
        provider = OpencodeProvider(_client=client)
        result = provider.chat("Hello", model="opencode")

    assert result == "Hello from opencode"
    # Verify both endpoints were called
    assert ("POST", "/session") in responses_seen
    assert ("POST", f"/session/{session_id}/message") in responses_seen


def test_opencodeprovider_auto_recreates_session_on_401():
    """When message endpoint returns 401, session is recreated and message retried."""
    old_session_id = "session-old"
    new_session_id = "session-new"
    session_call_count = [0]
    responses_seen = []

    def handler(request):
        responses_seen.append((request.method, request.url.path))
        if request.url.path == "/session":
            session_call_count[0] += 1
            if session_call_count[0] == 1:
                return httpx.Response(200, json={"id": old_session_id})
            else:
                return httpx.Response(200, json={"id": new_session_id})
        if request.url.path == f"/session/{old_session_id}/message":
            return httpx.Response(401)
        if request.url.path == f"/session/{new_session_id}/message":
            return httpx.Response(
                200,
                json={"parts": [{"type": "text", "text": "response after retry"}]},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    with patch.dict(
        os.environ,
        {
            "OPENCODE_SERVER_PASSWORD": "test-pw",
            "OPENCODE_BASE_URL": "http://localhost:4096",
        },
    ):
        provider = OpencodeProvider(_client=client)
        result = provider.chat("Hello", model="opencode")

    assert result == "response after retry"
    # Session created twice: init + auto-recreate
    assert session_call_count[0] == 2
    assert ("POST", "/session") in responses_seen
    assert ("POST", f"/session/{old_session_id}/message") in responses_seen
    assert ("POST", f"/session/{new_session_id}/message") in responses_seen
