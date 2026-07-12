
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

_DEFAULT_DB_URL = "sqlite:///./disaster_report.db"
_API_KEY_ENV_NAME = "API_KEY"
_DB_TOML_TABLE = "database"
_DB_URL_TOML_KEY = "db_url"
_OR_TOML_TABLE = "openrouter"
_OR_MODEL_TOML_KEY = "model"
_INGEST_TOML_TABLE = "ingest"
_ACTIVE_WINDOW_TOML_KEY = "active_window_days"
_MIN_LOG_NEWS_THRESHOLD_KEY = "min_log_news_threshold"


@dataclass(frozen=True)
class Settings:

    db_url: str
    openrouter_api_key: str
    openrouter_model: str
    active_window_days: int
    min_log_news_threshold: int

    def __init__(
        self,
        db_url: str,
        openrouter_api_key: str,
        openrouter_model: str,
        active_window_days: int,
        min_log_news_threshold: int = 3,
    ) -> None:

        if not openrouter_api_key:
            raise ValueError("openrouter_api_key must not be empty")
        if not openrouter_model:
            raise ValueError("openrouter_model must not be empty")
        object.__setattr__(self, "db_url", db_url or _DEFAULT_DB_URL)
        object.__setattr__(self, "openrouter_api_key", openrouter_api_key)
        object.__setattr__(self, "openrouter_model", openrouter_model)
        object.__setattr__(self, "active_window_days", active_window_days)
        object.__setattr__(self, "min_log_news_threshold", min_log_news_threshold)

    @classmethod
    def load(cls, *, config_path: str, secrets_path: str) -> Settings:

        with open(config_path, "rb") as fp:
            data = tomllib.load(fp)
        db_url = data.get(_DB_TOML_TABLE, {}).get(_DB_URL_TOML_KEY, "") or ""
        openrouter_model = (
            data.get(_OR_TOML_TABLE, {}).get(_OR_MODEL_TOML_KEY, "") or ""
        )

        if not Path(secrets_path).is_file():
            raise FileNotFoundError(secrets_path)
        values = dotenv_values(secrets_path)
        openrouter_api_key = values.get(_API_KEY_ENV_NAME) or ""
        active_window_days = int(
            data.get(_INGEST_TOML_TABLE, {}).get(_ACTIVE_WINDOW_TOML_KEY, 0)
        )
        min_log_news_threshold = int(
            data.get(_INGEST_TOML_TABLE, {}).get(_MIN_LOG_NEWS_THRESHOLD_KEY, 3)
        )

        return cls(
            db_url=db_url,
            openrouter_api_key=openrouter_api_key,
            openrouter_model=openrouter_model,
            active_window_days=int(active_window_days),
            min_log_news_threshold=int(min_log_news_threshold),
        )
