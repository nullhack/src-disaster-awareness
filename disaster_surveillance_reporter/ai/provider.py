from __future__ import annotations

import os
import time
import logging
from typing import Protocol

import httpx


# ── Exceptions ─────────────────────────────────────────────────────────

class AIProviderError(Exception):
    """Base exception for AI provider errors."""


class AuthenticationError(AIProviderError):
    """Raised on HTTP 401 — authentication failure. No retry."""


class RateLimitError(AIProviderError):
    """Raised when rate limit retries (HTTP 429) are exhausted."""


class NetworkError(AIProviderError):
    """Raised on connection-level failures — no retry."""


# ── Backoff constants ──────────────────────────────────────────────────

_INITIAL_DELAY = 15
_BACKOFF_MULTIPLIER = 2
_MAX_RETRIES = 3

_NON_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
    httpx.NetworkError,
)


# ── Protocol ────────────────────────────────────────────────────────────

class AIProvider(Protocol):
    """Abstract AI chat interface.

    ``chat(prompt, *, model) -> str``
    Raises on unrecoverable failure; auto-retries on HTTP 429.
    """

    def chat(self, prompt: str, *, model: str) -> str:
        raise NotImplementedError


# ── Backoff helper ──────────────────────────────────────────────────────

def _chat_with_backoff(make_request, parse_response) -> str:
    """Wrap a request with exponential backoff on HTTP 429.

    15 s initial, 2x multiplier, max 3 retries.
    401 → AuthenticationError immediately.
    Network errors → NetworkError immediately.
    """
    delay = _INITIAL_DELAY

    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = make_request()
        except _NON_RETRYABLE_EXCEPTIONS as exc:
            raise NetworkError(str(exc)) from exc

        if response.status_code == 200:
            return parse_response(response)

        if response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed (HTTP 401). Check your API key."
            )

        if response.status_code == 429:
            if attempt < _MAX_RETRIES:
                time.sleep(delay)
                delay *= _BACKOFF_MULTIPLIER
                continue
            raise RateLimitError(
                f"Rate limit retries exhausted after {_MAX_RETRIES} attempts"
            )

        # Other HTTP errors — no retry
        response.raise_for_status()

    raise RateLimitError("Rate limit retries exhausted")


# ── OllamaProvider (local, free) ────────────────────────────────────────

class OllamaProvider:
    """Calls a local Ollama server. No API key required.

    Default models: ``llama3.2``, ``mistral``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        _client: httpx.Client | None = None,
    ) -> None:
        _ = api_key or os.environ.get("DSR_AI_API_KEY")  # optional
        self._base_url = base_url or os.environ.get(
            "DSR_AI_BASE_URL", "http://localhost:11434"
        )
        self._client = _client

    def chat(self, prompt: str, *, model: str) -> str:
        client = self._client or httpx.Client(timeout=30)
        try:

            def make_request():
                return client.post(
                    f"{self._base_url}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                )

            def parse_response(response):
                return response.json()["response"]

            return _chat_with_backoff(make_request, parse_response)
        finally:
            if self._client is None:
                client.close()


# ── GeminiProvider (Google, free tier) ──────────────────────────────────

class GeminiProvider:
    """Calls Google Gemini API. Requires a free API key.

    Default model: ``gemini-2.0-flash``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        _client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("DSR_AI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "DSR_AI_API_KEY environment variable is required for GeminiProvider"
            )
        self._client = _client

    def chat(self, prompt: str, *, model: str) -> str:
        client = self._client or httpx.Client(timeout=30)
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={self._api_key}"
            )

            def make_request():
                return client.post(
                    url,
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                )

            def parse_response(response):
                return response.json()["candidates"][0]["content"]["parts"][0][
                    "text"
                ]

            return _chat_with_backoff(make_request, parse_response)
        finally:
            if self._client is None:
                client.close()


# ── OpenAIProvider (paid) ───────────────────────────────────────────────

class OpenAIProvider:
    """Calls OpenAI API. Requires a paid API key.

    Default model: ``gpt-4o-mini``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        _client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("DSR_AI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "DSR_AI_API_KEY environment variable is required for OpenAIProvider"
            )
        self._client = _client

    def chat(self, prompt: str, *, model: str) -> str:
        client = self._client or httpx.Client(timeout=30)
        try:

            def make_request():
                return client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )

            def parse_response(response):
                return response.json()["choices"][0]["message"]["content"]

            return _chat_with_backoff(make_request, parse_response)
        finally:
            if self._client is None:
                client.close()


# ── OpencodeProvider (opencode serve REST) ───────────────────────────────

class OpencodeProvider:
    """Calls opencode serve HTTP REST API.

    Session-managed: one persistent session per instance.
    Auto-recreates on 401/404 from message endpoint.

    Uses OPENCODE_SERVER_PASSWORD for ``opencode:<password>`` basic auth.
    """

    def __init__(
        self,
        _client: httpx.Client | None = None,
    ) -> None:
        self._password = os.environ.get("OPENCODE_SERVER_PASSWORD")
        if not self._password:
            raise ValueError(
                "OPENCODE_SERVER_PASSWORD environment variable is required "
                "for OpencodeProvider"
            )
        self._base_url = os.environ.get(
            "OPENCODE_BASE_URL", "http://127.0.0.1:4096"
        ).rstrip("/")
        self._timeout = float(
            os.environ.get("OPENCODE_SESSION_TIMEOUT", "120")
        )
        self._client = _client
        self._auth = httpx.BasicAuth("opencode", self._password)
        self._session_id: str | None = None
        self._last_model: str | None = None

        self._ensure_session()

    # ── session management ──────────────────────────────────────────

    def _ensure_session(self) -> None:
        """Create session via POST /session (fail-fast on auth error)."""
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.post(
                f"{self._base_url}/session", auth=self._auth
            )
            if resp.status_code == 401:
                raise AuthenticationError(
                    "OpencodeProvider authentication failed (HTTP 401). "
                    "Check OPENCODE_SERVER_PASSWORD."
                )
            resp.raise_for_status()
            self._session_id = resp.json()["id"]
        finally:
            if self._client is None:
                client.close()

    def _recreate_session(self) -> None:
        """Recreate session after 401/404 on message endpoint."""
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.post(
                f"{self._base_url}/session", auth=self._auth
            )
            resp.raise_for_status()
            self._session_id = resp.json()["id"]
        finally:
            if self._client is None:
                client.close()

    # ── chat ────────────────────────────────────────────────────────

    def chat(self, prompt: str, *, model: str) -> str:
        if self._last_model is not None and model != self._last_model:
            logging.warning(
                "OpencodeProvider ignores model parameter %r; "
                "opencode serve uses its own configured model.",
                model,
            )
        elif self._last_model is None and model != "opencode":
            logging.warning(
                "OpencodeProvider ignores model parameter %r; "
                "opencode serve uses its own configured model.",
                model,
            )
        self._last_model = model

        client = self._client or httpx.Client(timeout=self._timeout)
        try:

            def make_request():
                return client.post(
                    f"{self._base_url}/session/{self._session_id}/message",
                    json={"parts": [{"type": "text", "text": prompt}]},
                    auth=self._auth,
                )

            def parse_response(response):
                parts = response.json().get("parts", [])
                texts = [
                    p["text"]
                    for p in parts
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                return "\n".join(texts)

            def make_request_with_refresh():
                try:
                    return make_request()
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code in (401, 404):
                        self._recreate_session()
                        return make_request()
                    raise

            return _chat_with_backoff(make_request_with_refresh, parse_response)

        finally:
            if self._client is None:
                client.close()


# ── Factory ──────────────────────────────────────────────────────────────

_PROVIDER_REGISTRY: dict[str, type] = {
    "ollama": OllamaProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "opencode": OpencodeProvider,
}


def get_provider() -> AIProvider | None:
    """Return a configured AIProvider based on ``DSR_AI_PROVIDER``.

    Returns:
        An ``AIProvider`` instance for valid backends,
        ``None`` when ``DSR_AI_PROVIDER=none``.

    Raises:
        ValueError: If ``DSR_AI_PROVIDER`` is unset or invalid, or if
            a required ``DSR_AI_API_KEY`` is missing.
    """
    provider_name = os.environ.get("DSR_AI_PROVIDER")
    if not provider_name:
        raise ValueError("DSR_AI_PROVIDER environment variable is not set")
    if provider_name == "none":
        return None
    if provider_name not in _PROVIDER_REGISTRY:
        raise ValueError(f"Unknown AI provider: {provider_name!r}")
    return _PROVIDER_REGISTRY[provider_name]()
