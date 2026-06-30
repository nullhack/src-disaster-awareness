from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_MODELS = (
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
)
_DEFAULT_SOURCES = ("gdacs", "usgs", "who", "healthmap")


@dataclass
class Config:
    database_url: str = "sqlite:///./disaster.db"
    ai_provider: str = "openrouter"
    ai_base_url: str = "https://openrouter.ai/api/v1"
    ai_models: tuple[str, ...] = _DEFAULT_MODELS
    ai_api_key: str = ""
    ai_api_key_env: str = "OPENROUTER_API_KEY"
    sources_enabled: tuple[str, ...] = _DEFAULT_SOURCES
    news_provider: str = "ddg"
    tracking_window_days: int = 7
    develop_re_digest_threshold: int = 3

    @classmethod
    def from_toml(cls, path: str | Path) -> Config:
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
        database = data.get("database", {})
        ai = data.get("ai", {})
        sources = data.get("sources", {})
        news = data.get("news", {})
        tracking = data.get("tracking", {})
        return cls(
            database_url=database.get("url", "sqlite:///./disaster.db"),
            ai_provider=ai.get("provider", "openrouter"),
            ai_base_url=ai.get("base_url", "https://openrouter.ai/api/v1"),
            ai_models=tuple(ai.get("models", _DEFAULT_MODELS)),
            ai_api_key=ai.get("api_key", ""),
            ai_api_key_env=ai.get("api_key_env", "OPENROUTER_API_KEY"),
            sources_enabled=tuple(sources.get("enabled", _DEFAULT_SOURCES)),
            news_provider=news.get("provider", "ddg"),
            tracking_window_days=int(tracking.get("window_days", 7)),
            develop_re_digest_threshold=int(
                tracking.get("develop_re_digest_threshold", 3)
            ),
        )
