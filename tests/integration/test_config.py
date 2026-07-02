from __future__ import annotations

import pytest

pytest.importorskip("disaster_report.config", reason="config not implemented")

from disaster_report.config import Config


CONFIG_TOML = """\
[database]
url = "sqlite:///./disaster.db"

[ai]
provider = "openrouter"
base_url = "https://openrouter.ai/api/v1"
models = ["nvidia/nemotron-3-super-120b-a12b:free", "google/gemma-4-31b-it:free"]
api_key_env = "OPENROUTER_API_KEY"

[sources]
enabled = ["gdacs", "usgs", "who", "healthmap"]

[news]
provider = "ddg"

[tracking]
window_days = 7
"""


def _write_config(tmp_path) -> str:
    path = tmp_path / "config.toml"
    path.write_text(CONFIG_TOML)
    return str(path)


def test_from_toml_loads_every_section(tmp_path):
    config = Config.from_toml(_write_config(tmp_path))

    assert config.database_url == "sqlite:///./disaster.db"
    assert config.ai_provider == "openrouter"
    assert config.ai_base_url == "https://openrouter.ai/api/v1"
    assert config.ai_models == (
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-31b-it:free",
    )
    assert config.ai_api_key_env == "OPENROUTER_API_KEY"
    assert config.ai_api_key == ""
    assert list(config.sources_enabled) == ["gdacs", "usgs", "who", "healthmap"]
    assert config.news_provider == "ddg"
    assert config.tracking_window_days == 7


def test_config_has_sensible_defaults_so_pipeline_can_construct_directly():
    config = Config(tracking_window_days=5)

    assert config.tracking_window_days == 5


def test_config_default_tracking_window_is_seven_days():
    assert Config().tracking_window_days == 7


def test_from_toml_reads_inline_api_key_when_provided(tmp_path):
    toml = CONFIG_TOML.replace(
        'api_key_env = "OPENROUTER_API_KEY"',
        'api_key_env = "OPENROUTER_API_KEY"\napi_key = "sk-or-v1-test"',
    )
    path = tmp_path / "config.toml"
    path.write_text(toml)

    config = Config.from_toml(path)

    assert config.ai_api_key == "sk-or-v1-test"
