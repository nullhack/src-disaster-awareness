from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("disaster_report.cli", reason="cli not implemented")
pytest.importorskip("disaster_report.store", reason="store not implemented")

import httpx  # noqa: F401  (used by some assertions below)
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

    # dspy handles HTTP now; mock at the digester boundary so no network call is made.
    monkeypatch.setattr(
        "disaster_report.ai.openrouter.OpenRouterDigester.digest",
        lambda self, sources: {
            "canonical_name": "Sarangani Earthquake",
            "summary": "A magnitude 5.2 earthquake struck near Sarangani, Philippines.",
            "severity": "LOW",
            "search_keys": ["Sarangani earthquake"],
        },
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
            incident_type="Earthquake",
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
    result = runner.invoke(app, ["report", "--config", str(cfg), "--min-severity", "MEDIUM"])

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


def test_cli_reclassify_dry_run_does_not_persist(db_url, tmp_path):
    cfg = _write_config(db_url, tmp_path)
    store = SqliteIncidentStore(db_url)
    # Deliberately mislabeled: group A MEDIUM earthquake flagged as not
    # reportable. reclassify should detect a delta but NOT persist it.
    store.upsert_incident(
        IncidentRecord(
            incident_id="20260629-PH-EQ",
            canonical_name="Sarangani Earthquake",
            summary="A magnitude 5.2 earthquake struck near Sarangani, Philippines.",
            country="Philippines",
            incident_type="Earthquake",
            priority="LOW",
            severity_level=2,
            event_date="2026-06-29",
            first_reported_date="2026-06-29",
            last_updated_date="2026-06-29",
            should_report=False,
            search_keys=["Sarangani earthquake"],
        )
    )

    runner = CliRunner()
    result = runner.invoke(app, ["reclassify", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
    assert "20260629-PH-EQ" in result.output

    view = store.find_by_incident_id("20260629-PH-EQ")
    assert view is not None
    # Unchanged: dry-run.
    with store._engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT priority, should_report FROM v_incident WHERE incident_id = ?",
            ("20260629-PH-EQ",),
        ).one()
    assert row.priority == "LOW"
    assert row.should_report == 0


def test_cli_reclassify_apply_persists_changes(db_url, tmp_path):
    cfg = _write_config(db_url, tmp_path)
    store = SqliteIncidentStore(db_url)
    store.upsert_incident(
        IncidentRecord(
            incident_id="20260629-PH-EQ",
            canonical_name="Sarangani Earthquake",
            summary="A magnitude 5.2 earthquake struck near Sarangani, Philippines.",
            country="Philippines",
            incident_type="Earthquake",
            priority="LOW",
            severity_level=2,
            event_date="2026-06-29",
            first_reported_date="2026-06-29",
            last_updated_date="2026-06-29",
            should_report=False,
            search_keys=["Sarangani earthquake"],
        )
    )

    runner = CliRunner()
    result = runner.invoke(app, ["reclassify", "--config", str(cfg), "--apply"])

    assert result.exit_code == 0, result.output
    assert "applied" in result.output
    assert "20260629-PH-EQ" in result.output

    with store._engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT priority, should_report FROM v_incident WHERE incident_id = ?",
            ("20260629-PH-EQ",),
        ).one()
    assert row.priority == "MEDIUM"
    assert row.should_report == 1


def test_cli_reclassify_no_changes_reports_cleanly(db_url, tmp_path):
    cfg = _write_config(db_url, tmp_path)
    store = SqliteIncidentStore(db_url)
    _seed_one_incident(store)  # already correctly classified

    runner = CliRunner()
    result = runner.invoke(app, ["reclassify", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "no changes" in result.output


# --------------------------------------------------------------------------- #
# redigest CLI (batch AI re-digest to populate pandemic_potential / event_status)
# --------------------------------------------------------------------------- #

def _disease_digest(self, sources):
    return {
        "canonical_name": "Berlin Ebola Case",
        "summary": "A single Ebola case was reported in Berlin.",
        "severity": "LOW",
        "disease_name": "Ebola",
        "pandemic_potential": "HIGH",
        "event_status": "new_outbreak",
        "search_keys": ["Ebola Berlin outbreak cases deaths"],
    }


def _seed_disease_incident(store):
    store.upsert_incident(
        IncidentRecord(
            incident_id="20260629-DE-EP",
            canonical_name="Berlin Ebola",
            summary="initial",
            country="Germany",
            incident_type="Disease",
            priority="LOW",
            severity_level=1,
            event_date="2026-06-29",
            first_reported_date="2026-06-29",
            last_updated_date="2026-06-29",
            should_report=False,
            search_keys=["Ebola Berlin"],
            disease_name="Ebola",
        )
    )


def test_cli_redigest_dry_run_makes_no_calls(db_url, tmp_path, monkeypatch):
    cfg = _write_config(db_url, tmp_path)
    store = SqliteIncidentStore(db_url)
    _seed_disease_incident(store)

    def forbid_digest(self, sources):
        raise AssertionError("dry-run redigest must not call the AI API")

    monkeypatch.setattr(
        "disaster_report.ai.openrouter.OpenRouterDigester.digest", forbid_digest
    )

    runner = CliRunner()
    result = runner.invoke(app, ["redigest", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
    assert "1 incident(s)" in result.output
    # Unchanged.
    with store._engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT pandemic_potential FROM v_incident WHERE incident_id = ?",
            ("20260629-DE-EP",),
        ).one()
    assert row.pandemic_potential is None


def test_cli_redigest_apply_persists_disease_digest(db_url, tmp_path, monkeypatch):
    cfg = _write_config(db_url, tmp_path)
    store = SqliteIncidentStore(db_url)
    _seed_disease_incident(store)

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        "disaster_report.ai.openrouter.OpenRouterDigester.digest", _disease_digest
    )

    runner = CliRunner()
    result = runner.invoke(app, ["redigest", "--config", str(cfg), "--apply"])

    assert result.exit_code == 0, result.output
    assert "re-digested" in result.output
    assert "20260629-DE-EP" in result.output

    with store._engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT pandemic_potential, event_status, priority, should_report "
            "FROM v_incident WHERE incident_id = ?",
            ("20260629-DE-EP",),
        ).one()
    assert row.pandemic_potential == "HIGH"
    assert row.event_status == "new_outbreak"
    assert row.priority == "HIGH"
    assert row.should_report == 1
