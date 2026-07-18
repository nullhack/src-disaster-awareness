
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

_DEFAULT_TREE_ROOT = "data"
_API_KEY_ENV_NAME = "API_KEY"
_TREE_TOML_TABLE = "tree"
_TREE_ROOT_TOML_KEY = "root"
_OR_TOML_TABLE = "openrouter"
_OR_MODEL_TOML_KEY = "model"
_INGEST_TOML_TABLE = "ingest"
_ACTIVE_WINDOW_TOML_KEY = "active_window_days"
_MIN_LOG_NEWS_THRESHOLD_KEY = "min_log_news_threshold"


@dataclass(frozen=True)
class Settings:

    tree_root: str
    openrouter_api_key: str
    openrouter_model: str
    active_window_days: int
    min_log_news_threshold: int

    def __init__(
        self,
        tree_root: str,
        openrouter_api_key: str,
        openrouter_model: str,
        active_window_days: int,
        min_log_news_threshold: int = 3,
    ) -> None:

        if not openrouter_api_key:
            raise ValueError("openrouter_api_key must not be empty")
        if not openrouter_model:
            raise ValueError("openrouter_model must not be empty")
        object.__setattr__(self, "tree_root", tree_root or _DEFAULT_TREE_ROOT)
        object.__setattr__(self, "openrouter_api_key", openrouter_api_key)
        object.__setattr__(self, "openrouter_model", openrouter_model)
        object.__setattr__(self, "active_window_days", active_window_days)
        object.__setattr__(self, "min_log_news_threshold", min_log_news_threshold)

    @classmethod
    def load(cls, *, config_path: str, secrets_path: str) -> Settings:

        with open(config_path, "rb") as fp:
            data = tomllib.load(fp)
        tree_root = data.get(_TREE_TOML_TABLE, {}).get(_TREE_ROOT_TOML_KEY, "") or ""
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
            tree_root=tree_root,
            openrouter_api_key=openrouter_api_key,
            openrouter_model=openrouter_model,
            active_window_days=int(active_window_days),
            min_log_news_threshold=int(min_log_news_threshold),
        )
