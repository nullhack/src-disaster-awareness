import os
import pytest

from unittest.mock import patch

from hypothesis import given, example, strategies as st

from disaster_surveillance_reporter.ai.provider import (
    get_provider,
    OllamaProvider,
    GeminiProvider,
    OpenAIProvider,
    OpencodeProvider,
)


_VALID_PROVIDERS = {"ollama", "gemini", "openai", "opencode"}
_AUTH_PROVIDERS = {"gemini", "openai"}


@example(provider="ollama")
@example(provider="gemini")
@example(provider="openai")
@example(provider="opencode")
@example(provider="none")
@given(provider=st.text(
    alphabet=st.characters(
        blacklist_characters="\x00",
        blacklist_categories=("Cs",),  # surrogates not valid in os.environ
    ),
    min_size=1,
))
def test_provider_initializes_from_env_var(provider):
    # Given DSR_AI_PROVIDER is set to "<provider>"
    _beehave_lit = "<provider>"  # beehave traceability
    # When the AIProvider is initialized
    # Then the AIProvider is configured as <provider> backend
    env_override = {"DSR_AI_PROVIDER": provider}

    if provider in _AUTH_PROVIDERS:
        env_override["DSR_AI_API_KEY"] = "test-key"
    if provider == "opencode":
        env_override["OPENCODE_SERVER_PASSWORD"] = "test-pw"

    with patch.dict(os.environ, env_override):
        if provider == "ollama":
            result = get_provider()
            assert isinstance(result, OllamaProvider)
        elif provider == "gemini":
            result = get_provider()
            assert isinstance(result, GeminiProvider)
        elif provider == "openai":
            result = get_provider()
            assert isinstance(result, OpenAIProvider)
        elif provider == "opencode":
            with patch.object(
                OpencodeProvider, "_ensure_session", return_value=None
            ):
                result = get_provider()
                assert isinstance(result, OpencodeProvider)
        elif provider == "none":
            result = get_provider()
            assert result is None
        else:
            with pytest.raises(ValueError):
                get_provider()


def test_invalid_provider_raises_error():
    with patch.dict(os.environ, {"DSR_AI_PROVIDER": "claude"}):
        with pytest.raises(ValueError):
            get_provider()


def test_missing_api_key_raises_error():
    with patch.dict(os.environ, {"DSR_AI_PROVIDER": "openai"}):
        # DSR_AI_API_KEY is not set
        with pytest.raises(ValueError, match="DSR_AI_API_KEY"):
            get_provider()


def test_missing_opencode_password_raises_error():
    with patch.dict(os.environ, {"DSR_AI_PROVIDER": "opencode"}):
        # OPENCODE_SERVER_PASSWORD is not set
        with pytest.raises(ValueError, match="OPENCODE_SERVER_PASSWORD"):
            get_provider()
