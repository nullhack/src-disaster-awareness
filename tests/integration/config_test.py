from __future__ import annotations

import pytest


class TestSettings:
    def test_loads_database_url_from_config(self, monkeypatch, tmp_path) -> None:
        from disaster_report.config import Settings

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[database]\ndb_url = "sqlite:///./from_config.db"\n'
            '[openrouter]\nmodel = "openrouter/deepseek/deepseek-v4"\n'
            "[ingest]\nactive_window_days = 7\n"
        )
        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text("API_KEY=sk-or-test\n")
        settings = Settings.load(
            config_path=str(config_file), secrets_path=str(secrets_file)
        )
        assert settings.db_url == "sqlite:///./from_config.db"

    def test_openrouter_key_from_secrets_file(self, monkeypatch, tmp_path) -> None:
        from disaster_report.config import Settings

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[database]\n[openrouter]\nmodel = "openrouter/deepseek/deepseek-v4"\n'
            "[ingest]\nactive_window_days = 7\n"
        )
        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text("API_KEY=sk-or-test\n")
        settings = Settings.load(
            config_path=str(config_file), secrets_path=str(secrets_file)
        )
        assert settings.openrouter_api_key == "sk-or-test"

    def test_openrouter_model_from_config(self, tmp_path) -> None:
        from disaster_report.config import Settings

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[openrouter]\nmodel = "openrouter/deepseek/deepseek-v4"\n'
            "[ingest]\nactive_window_days = 7\n"
        )
        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text("API_KEY=sk-or-test\n")
        settings = Settings.load(
            config_path=str(config_file), secrets_path=str(secrets_file)
        )
        assert settings.openrouter_model == "openrouter/deepseek/deepseek-v4"

    def test_empty_api_key_raises(self) -> None:
        from disaster_report.config import Settings

        with pytest.raises(ValueError):
            Settings(
                db_url="sqlite:///./x.db",
                openrouter_api_key="",
                openrouter_model="openrouter/deepseek/deepseek-v4",
                active_window_days=7,
            )

    def test_empty_model_raises(self) -> None:
        from disaster_report.config import Settings

        with pytest.raises(ValueError):
            Settings(
                db_url="sqlite:///./x.db",
                openrouter_api_key="sk-or-test",
                openrouter_model="",
                active_window_days=7,
            )

    def test_settings_is_frozen_after_construction(self) -> None:
        from dataclasses import FrozenInstanceError

        from disaster_report.config import Settings

        settings = Settings(
            db_url="sqlite:///./x.db",
            openrouter_api_key="sk-or-test",
            openrouter_model="openrouter/deepseek/deepseek-v4",
            active_window_days=7,
        )
        with pytest.raises(FrozenInstanceError):
            settings.db_url = "sqlite:///./y.db"  # type: ignore[misc]

    def test_db_url_defaults_to_local_sqlite(self) -> None:
        from disaster_report.config import Settings

        settings = Settings(
            db_url="",
            openrouter_api_key="sk-or-test",
            openrouter_model="openrouter/deepseek/deepseek-v4",
            active_window_days=7,
        )
        assert settings.db_url == "sqlite:///./disaster_report.db"

    def test_missing_secrets_file_raises_clear_error(
        self, monkeypatch, tmp_path
    ) -> None:
        from disaster_report.config import Settings

        config_file = tmp_path / "config.toml"
        config_file.write_text("[database]\n")
        with pytest.raises(FileNotFoundError):
            Settings.load(
                config_path=str(config_file), secrets_path=str(tmp_path / "missing.env")
            )

    def test_ai_key_is_never_logged(self, monkeypatch, tmp_path, caplog) -> None:
        import logging

        from disaster_report.config import Settings

        secrets_file = tmp_path / "secrets.env"
        secrets_file.write_text("API_KEY=sk-or-secret\n")
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[database]\n[openrouter]\nmodel = "openrouter/deepseek/deepseek-v4"\n'
            "[ingest]\nactive_window_days = 7\n"
        )
        with caplog.at_level(logging.DEBUG):
            Settings.load(config_path=str(config_file), secrets_path=str(secrets_file))
        assert "sk-or-secret" not in caplog.text
