from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

import click

from disaster_report.ai.openrouter import OpenRouterDigester
from disaster_report.config import Config
from disaster_report.pipeline import Pipeline
from disaster_report.resolver import IncidentResolver
from disaster_report.sources.ddg_news import DdgNewsAdapter
from disaster_report.sources.gdacs import GDACSAdapter
from disaster_report.sources.healthmap import HealthMapAdapter
from disaster_report.sources.usgs import UsgsAdapter
from disaster_report.sources.who import WHODiseaseOutbreakAdapter
from disaster_report.store import SqliteIncidentStore

_OPENROUTER_AUTH_FALLBACK = Path.home() / ".local/share/opencode/auth.json"

_SOURCE_REGISTRY = {
    "usgs": UsgsAdapter,
    "gdacs": GDACSAdapter,
    "who": WHODiseaseOutbreakAdapter,
    "healthmap": HealthMapAdapter,
}

_NEWS_REGISTRY = {
    "ddg": DdgNewsAdapter,
}


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
        force=True,
    )
    logging.getLogger("disaster_report").setLevel(level)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Emit progress logs to stderr.")
def app(verbose: bool) -> None:
    _configure_logging(verbose)


def _load(config_path: str) -> Config:
    return Config.from_toml(config_path)


def _build_sources(config: Config) -> list:
    sources = []
    for name in config.sources_enabled:
        factory = _SOURCE_REGISTRY.get(name.lower())
        if factory is not None:
            sources.append(factory())
    return sources


def _build_news(config: Config):
    factory = _NEWS_REGISTRY.get(config.news_provider.lower())
    if factory is None:
        raise click.ClickException(f"unknown news provider: {config.news_provider}")
    return factory()


def _resolve_api_key(config: Config) -> str:
    if config.ai_api_key:
        return config.ai_api_key
    env_value = os.environ.get(config.ai_api_key_env, "")
    if env_value:
        return env_value
    try:
        data = json.loads(_OPENROUTER_AUTH_FALLBACK.read_text())
        return data.get("openrouter", {}).get("key", "")
    except (OSError, ValueError, KeyError):
        return ""


def _build_digester(config: Config):
    return OpenRouterDigester(
        api_key=_resolve_api_key(config),
        base_url=config.ai_base_url,
        models=config.ai_models,
    )


@app.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def ingest(config_path: str) -> None:
    config = _load(config_path)
    store = SqliteIncidentStore(config.database_url)
    pipeline = Pipeline(
        sources=_build_sources(config),
        news=_build_news(config),
        resolver=IncidentResolver(),
        digester=_build_digester(config),
        store=store,
        config=config,
        clock=date.today,
    )
    pipeline.run()
    click.echo(f"ingested: {store.count_incidents()} incident(s) tracked")


@app.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def report(config_path: str) -> None:
    config = _load(config_path)
    store = SqliteIncidentStore(config.database_url)
    incidents = store.get_active_incidents(as_of=date.today(), within_days=config.tracking_window_days)
    if not incidents:
        click.echo("no active incidents")
        return
    for incident in incidents:
        click.echo(f"- {incident.canonical_name} [{incident.incident_id}]")
        for news in store.get_incident_news(incident.incident_key):
            click.echo(f"    * {news.url}")


if __name__ == "__main__":
    app()
