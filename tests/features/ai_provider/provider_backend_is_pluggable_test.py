import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(provider="ollama")
@example(provider="gemini")
@example(provider="openai")
@example(provider="none")
@given(provider=st.text())
def test_provider_initializes_from_env_var(provider):
    ...

@pytest.mark.skip(reason="not implemented")
def test_invalid_provider_raises_error():
    ...

@pytest.mark.skip(reason="not implemented")
def test_missing_api_key_raises_error():
    ...

@pytest.mark.skip(reason="not implemented")
def test_missing_opencode_password_raises_error():
    ...

