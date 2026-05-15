from __future__ import annotations

import os
from typing import Protocol


class AIProvider(Protocol):
    def chat(self, prompt: str, *, model: str) -> str:
        raise NotImplementedError


class OllamaProvider:
    def __init__(self) -> None:
        _ = os.environ.get("DSR_AI_API_KEY")

    def chat(self, prompt: str, *, model: str) -> str:
        raise NotImplementedError


class GeminiProvider:
    def __init__(self) -> None:
        _ = os.environ.get("DSR_AI_API_KEY")

    def chat(self, prompt: str, *, model: str) -> str:
        raise NotImplementedError


class OpenAIProvider:
    def __init__(self) -> None:
        _ = os.environ.get("DSR_AI_API_KEY")

    def chat(self, prompt: str, *, model: str) -> str:
        raise NotImplementedError


_PROVIDER_REGISTRY: dict[str, type] = {
    "ollama": OllamaProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
}


def get_provider() -> AIProvider | None:
    provider_name = os.environ.get("DSR_AI_PROVIDER")
    if not provider_name:
        raise ValueError("DSR_AI_PROVIDER environment variable is not set")
    if provider_name == "none":
        return None
    if provider_name not in _PROVIDER_REGISTRY:
        raise ValueError(f"Unknown AI provider: {provider_name!r}")
    return _PROVIDER_REGISTRY[provider_name]()
