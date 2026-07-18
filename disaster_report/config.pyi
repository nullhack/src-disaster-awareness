from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    # tree_root is the path to the v5 git-backed content tree (default "data").
    # openrouter_api_key is loaded from the secrets file via dotenv_values().
    # openrouter_model is the model id from [openrouter] model in config.toml.
    tree_root: str
    openrouter_api_key: str
    openrouter_model: str
    active_window_days: int
    min_log_news_threshold: int = 3

    @classmethod
    def load(cls, *, config_path: str, secrets_path: str) -> Settings: ...
