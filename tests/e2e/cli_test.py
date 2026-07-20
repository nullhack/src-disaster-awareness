from __future__ import annotations

from unittest.mock import MagicMock


def _patch_bootstrap(monkeypatch) -> None:
    monkeypatch.setattr(
        "disaster_report.cli._bootstrap",
        lambda *a, **kw: (MagicMock(), object()),
    )


class TestCliE2E:
    def test_ingest_command_calls_run_pipeline(self, monkeypatch) -> None:
        from click.testing import CliRunner

        from disaster_report.cli import cli

        captured: dict[str, object] = {}

        def fake_run_pipeline(*args: object, **kwargs: object) -> object:
            captured["called"] = True
            from disaster_report.pipeline import IngestReport

            return IngestReport(source_reports_kept=0, ai_calls=0, ddg_calls=0)

        monkeypatch.setattr("disaster_report.cli.run_pipeline", fake_run_pipeline)
        monkeypatch.setattr("disaster_report.cli._build_adapters", lambda source: [])
        monkeypatch.setattr(
            "disaster_report.cli.OpenRouterDigester", lambda *a, **kw: object()
        )
        monkeypatch.setattr(
            "disaster_report.cli.DuckDuckGoNewsAdapter", lambda *a, **kw: object()
        )
        _patch_bootstrap(monkeypatch)
        result = CliRunner().invoke(cli, ["ingest", "--source", "USGS", "-v"])
        assert captured.get("called") is True
        assert result.exit_code == 0

    def test_ingest_records_command_calls_ingest_source_reports(
        self, monkeypatch
    ) -> None:
        from click.testing import CliRunner

        from disaster_report.cli import cli

        captured: dict[str, object] = {}

        def fake_ingest(*args: object, **kwargs: object) -> int:
            captured["called"] = True
            return 0

        monkeypatch.setattr("disaster_report.cli.ingest_source_reports", fake_ingest)
        monkeypatch.setattr("disaster_report.cli._build_adapters", lambda source: [])
        _patch_bootstrap(monkeypatch)
        result = CliRunner().invoke(cli, ["ingest-records", "--source", "USGS"])
        assert captured.get("called") is True
        assert result.exit_code == 0

    def test_search_news_command_calls_search_news(self, monkeypatch) -> None:
        from click.testing import CliRunner

        from disaster_report.cli import cli

        captured: dict[str, object] = {}

        def fake_search(*args: object, **kwargs: object) -> int:
            captured["called"] = True
            return 0

        monkeypatch.setattr("disaster_report.cli.search_news", fake_search)
        monkeypatch.setattr("disaster_report.cli._build_adapters", lambda source: [])
        monkeypatch.setattr(
            "disaster_report.cli.DuckDuckGoNewsAdapter", lambda *a, **kw: object()
        )
        monkeypatch.setattr(
            "disaster_report.cli.OpenRouterDigester", lambda *a, **kw: object()
        )
        _patch_bootstrap(monkeypatch)
        result = CliRunner().invoke(cli, ["search-news", "--source", "USGS"])
        assert captured.get("called") is True
        assert result.exit_code == 0

    def test_generate_logs_command_calls_generate_logs(self, monkeypatch) -> None:
        from click.testing import CliRunner

        from disaster_report.cli import cli

        captured: dict[str, object] = {}

        def fake_generate(*args: object, **kwargs: object) -> int:
            captured["called"] = True
            return 0

        monkeypatch.setattr("disaster_report.cli.generate_logs", fake_generate)
        monkeypatch.setattr(
            "disaster_report.cli.OpenRouterDigester", lambda *a, **kw: object()
        )
        _patch_bootstrap(monkeypatch)
        result = CliRunner().invoke(cli, ["generate-logs"])
        assert captured.get("called") is True
        assert result.exit_code == 0

    def test_report_command_emits_markdown_brief(self, monkeypatch) -> None:
        from click.testing import CliRunner

        from disaster_report.cli import cli
        from disaster_report.reporting.report import ReportDocument

        _patch_bootstrap(monkeypatch)
        monkeypatch.setattr(
            "disaster_report.cli.build_report",
            lambda *a, **kw: ReportDocument(
                generated_at="2026-07-17T00:00:00+00:00",
                incidents=[],
                timeline=[],
                news=[],
            ),
        )
        result = CliRunner().invoke(cli, ["report"])
        assert result.exit_code == 0

    def test_no_reclassify_command_exists(self) -> None:
        from disaster_report.cli import cli

        commands = set(cli.commands)
        assert "reclassify" not in commands

    def test_no_redigest_command_exists(self) -> None:
        from disaster_report.cli import cli

        commands = set(cli.commands)
        assert "redigest" not in commands
