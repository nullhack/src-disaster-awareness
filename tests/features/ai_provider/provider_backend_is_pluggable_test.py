from hypothesis import given, example, strategies as st

@example(provider="ollama")
@example(provider="gemini")
@example(provider="openai")
@example(provider="none")
@given(provider=st.text())
def test_provider_initializes_from_env_var(provider):
    ...

def test_invalid_provider_raises_error():
    ...

def test_missing_api_key_raises_error():
    ...

