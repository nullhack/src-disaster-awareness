from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    # db_url is the canonical SQLAlchemy URL string form ("sqlite:///<path>");
    # if constructed empty, normalised to "sqlite:///./disaster_report.db".
    # openrouter_api_key is loaded from the secrets file via dotenv_values().
    # openrouter_model is the model id from [openrouter] model in config.toml.
    db_url: str
    openrouter_api_key: str
    openrouter_model: str
    active_window_days: int
    min_log_news_threshold: int

    @classmethod
    def load(cls, *, config_path: str, secrets_path: str) -> Settings: ...
