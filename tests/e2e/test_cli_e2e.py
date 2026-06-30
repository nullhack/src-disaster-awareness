from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("disaster_report.cli", reason="cli not implemented")
pytest.importorskip("disaster_report.store", reason="store not implemented")

import httpx
from click.testing import CliRunner

from disaster_report.cli import app
from disaster_report.sources.base import RawArticle
from disaster_report.store import IncidentRecord, SqliteIncidentStore

CONFIG_TOML = """\
[database]
url = "sqlite:///{db}"

[ai]
provider = "openrouter"
base_url = "https://openrouter.ai/api/v1"
models = ["nvidia/nemotron-3-super-120b-a12b:free"]
api_key_env = "OPENROUTER_API_KEY"

[sources]
enabled = ["usgs"]

[news]
provider = "ddg"

[tracking]
window_days = 7
"""


def _write_config(db_url: str, tmp_path: Path) -> Path:
    cfg = tmp_path / "config.toml"
    cfg.write_text(CONFIG_TOML.format(db=db_url.replace("sqlite:///", "")))
    return cfg


def _ai_response(url: str) -> httpx.Response:
    content = json.dumps(
        {
            "canonical_name": "Sarangani Earthquake",
            "summary": "A magnitude 5.2 earthquake struck near Sarangani, Philippines.",
            "severity": "LOW",
            "search_keys": ["Sarangani earthquake"],
        }
    )
    body = {"choices": [{"index": 0, "message": {"role": "assistant", "content": content}}]}
    return httpx.Response(200, json=body, request=httpx.Request("POST", url))


def _mock_ingest_boundaries(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    monkeypatch.setattr(
        "disaster_report.sources.usgs.UsgsAdapter.fetch", lambda self: _stub_usgs_fetch()
    )

    class FakeDDGS:
        def __init__(self, *args, **kwargs):
            pass

        def news(self, **kwargs):
            return []

    monkeypatch.setattr("disaster_report.sources.ddg_news.DDGS", FakeDDGS)

    monkeypatch.setattr(
        "disaster_report.ai.openrouter.httpx.post",
        lambda url, *a, **k: _ai_response(url),
    )

    def forbid_get(url, *a, **k):
        raise AssertionError("ingest must not hit the network via httpx.get")

    monkeypatch.setattr("disaster_report.sources.usgs.httpx.get", forbid_get)


def _stub_usgs_fetch():
    from disaster_report.sources.base import RawIncident

    return [
        RawIncident(
            source_name="USGS",
            incident_name="M5.2 Earthquake near Sarangani",
            country="Philippines",
            disaster_type="Earthquake",
            report_date="2026-06-29T00:00:00Z",
            source_url="https://earthquake.usgs.gov/ev/1",
            raw_fields={"magnitude": 5.2},
        )
    ]


def test_cli_ingest_drives_full_chain_and_writes_incidents(db_url, tmp_path, monkeypatch):
    cfg = _write_config(db_url, tmp_path)
    _mock_ingest_boundaries(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(app, ["ingest", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    store = SqliteIncidentStore(db_url)
    assert store.count_incidents() >= 1


def test_cli_report_lists_incidents_with_their_news(db_url, tmp_path):
    cfg = _write_config(db_url, tmp_path)
    store = SqliteIncidentStore(db_url)
    _seed_one_incident(store)

    runner = CliRunner()
    result = runner.invoke(app, ["report", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "Sarangani" in out
    assert "https://n/1" in out


def _seed_one_incident(store):
    incident_key = store.upsert_incident(_incident_record())
    store.link_news(
        incident_key,
        RawArticle(
            "DDG", "Quake shakes Sarangani", "body", "https://n/1", "Reuters", "2026-06-29T08:00:00Z"
        ),
    )


def _incident_record() -> IncidentRecord:
    return IncidentRecord(
        incident_id="20260629-PH-EQ",
        canonical_name="Sarangani Earthquake",
        summary="A magnitude 5.2 earthquake struck near Sarangani, Philippines.",
        country="Philippines",
        incident_type="Earthquake",
        priority="MEDIUM",
        severity_level=2,
        event_date="2026-06-29",
        first_reported_date="2026-06-29",
        last_updated_date="2026-06-29",
        should_report=True,
        search_keys=["Sarangani earthquake"],
    )


def test_cli_honors_toml_config_database_path(db_url, tmp_path, monkeypatch):
    cfg = _write_config(db_url, tmp_path)
    _mock_ingest_boundaries(monkeypatch)

    runner = CliRunner()
    result = runner.invoke(app, ["ingest", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert Path(db_url.replace("sqlite:///", "")).exists()


def test_cli_verbose_flag_emits_pipeline_logs(db_url, tmp_path, monkeypatch):
    import logging

    cfg = _write_config(db_url, tmp_path)
    _mock_ingest_boundaries(monkeypatch)

    records: list[tuple] = []

    class _CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append((record.levelname, record.getMessage()))

    logging.basicConfig(level=logging.DEBUG, force=True)
    logging.getLogger("disaster_report.pipeline").addHandler(_CaptureHandler())

    try:
        runner = CliRunner()
        result = runner.invoke(app, ["-v", "ingest", "--config", str(cfg)])
        assert result.exit_code == 0, result.output
    finally:
        logging.getLogger("disaster_report.pipeline").removeHandler(_CaptureHandler())

    assert any("pipeline run for" in msg for _, msg in records), (
        "-v must configure logging so pipeline emits progress records"
    )
