
from __future__ import annotations

import functools
import logging
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from disaster_report.ai.openrouter import OpenRouterDigester
from disaster_report.config import Settings
from disaster_report.pipeline import (
    generate_logs,
    ingest_source_reports,
    run_pipeline,
    search_news,
)
from disaster_report.reporting.markdown import MarkdownRenderer
from disaster_report.reporting.report import build_report
from disaster_report.sources.ddg_news import DuckDuckGoNewsAdapter
from disaster_report.sources.gdacs import GDACSAdapter
from disaster_report.sources.usgs import USGSAdapter
from disaster_report.sources.who import WHODiseaseOutbreakAdapter
from disaster_report.store.base import Warehouse

_DEFAULT_CONFIG_PATH = "config.toml"
_DEFAULT_SECRETS_PATH = "~/.secrets/disaster_report.env"
_DEFAULT_NEWS_TIMELIMIT = "w"


def _configure_logging(verbose: bool) -> None:
    if not verbose:
        return
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(name)s: %(levelname)s: %(message)s",
        force=True,
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_settings(config_path: str, secrets_path: str) -> Settings:
    return Settings.load(
        config_path=config_path,
        secrets_path=str(Path(secrets_path).expanduser()),
    )


def _bootstrap(config_path: str, secrets_path: str) -> tuple[Settings, Warehouse]:
    settings = _load_settings(config_path, secrets_path)
    warehouse = Warehouse(settings.db_url, clock=_now)
    return settings, warehouse


def _build_adapters(source: str | None) -> list[object]:
    all_adapters: list[object] = [
        USGSAdapter(),
        GDACSAdapter(),
        WHODiseaseOutbreakAdapter(),
    ]
    if source is None:
        return all_adapters
    needle = source.upper()
    names = ["USGS", "GDACS", "WHO"]
    return [
        adapter
        for name, adapter in zip(names, all_adapters, strict=True)
        if name == needle
    ]


def _handle_errors(fn: Callable[..., None]) -> Callable[..., None]:
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        verbose: bool = kwargs.get("verbose", False)
        _configure_logging(verbose)
        try:
            fn(*args, **kwargs)
        except Exception as exc:
            if verbose:
                raise
            label = fn.__name__.lstrip("_").replace("_", "-")
            click.echo(f"{label} error: {exc}", err=True)
            sys.exit(1)

    return wrapper


@click.group()
def cli() -> None:

    pass


@cli.command("ingest")
@click.option("--config", "config_path", default=_DEFAULT_CONFIG_PATH)
@click.option("--secrets", "secrets_path", default=_DEFAULT_SECRETS_PATH)
@click.option("--source", default=None)
@click.option("-v", "--verbose", is_flag=True, default=False)
@_handle_errors
def _ingest(
    config_path: str,
    secrets_path: str,
    source: str | None,
    verbose: bool,
) -> None:

    settings, warehouse = _bootstrap(config_path, secrets_path)
    adapters = _build_adapters(source)
    ddg = DuckDuckGoNewsAdapter()
    digester = OpenRouterDigester(
        settings.openrouter_model, settings.openrouter_api_key
    )
    result = run_pipeline(
        adapters, warehouse, ddg, digester, _now,
        min_news_threshold=settings.min_log_news_threshold,
    )
    click.echo(
        f"ingested: source_reports_kept={result.source_reports_kept} "
        f"ai_calls={result.ai_calls} ddg_calls={result.ddg_calls}"
    )


@cli.command("ingest-records")
@click.option("--config", "config_path", default=_DEFAULT_CONFIG_PATH)
@click.option("--secrets", "secrets_path", default=_DEFAULT_SECRETS_PATH)
@click.option("--source", default=None)
@click.option("-v", "--verbose", is_flag=True, default=False)
@_handle_errors
def _ingest_records(
    config_path: str,
    secrets_path: str,
    source: str | None,
    verbose: bool,
) -> None:

    _, warehouse = _bootstrap(config_path, secrets_path)
    adapters = _build_adapters(source)
    kept = ingest_source_reports(adapters, warehouse)
    click.echo(f"ingested: source_reports_kept={kept}")


@cli.command("search-news")
@click.option("--config", "config_path", default=_DEFAULT_CONFIG_PATH)
@click.option("--secrets", "secrets_path", default=_DEFAULT_SECRETS_PATH)
@click.option("--source", default=None)
@click.option(
    "--source-id",
    "source_id",
    default=None,
    help="Force news search for one source_id (bypasses should_monitor).",
)
@click.option(
    "--news-timelimit",
    "news_timelimit",
    default=_DEFAULT_NEWS_TIMELIMIT,
    help="DDG news window: d=day, w=week (default), m=month.",
)
@click.option(
    "--repoll",
    "repoll",
    is_flag=True,
    default=False,
    help="Repoll active incidents for news updates (skips per-report search).",
)
@click.option("-v", "--verbose", is_flag=True, default=False)
@_handle_errors
def _search_news(
    config_path: str,
    secrets_path: str,
    source: str | None,
    source_id: str | None,
    news_timelimit: str,
    repoll: bool,
    verbose: bool,
) -> None:

    settings, warehouse = _bootstrap(config_path, secrets_path)
    adapters: list[object] = [] if repoll else _build_adapters(source)
    ddg = DuckDuckGoNewsAdapter()
    digester = OpenRouterDigester(
        settings.openrouter_model, settings.openrouter_api_key
    )
    search_news(
        warehouse,
        adapters,
        ddg,
        digester,
        _now,
        news_timelimit=news_timelimit,
        source_id=source_id,
        active_window_days=settings.active_window_days,
    )
    click.echo("search-news: done")


@cli.command("generate-logs")
@click.option("--config", "config_path", default=_DEFAULT_CONFIG_PATH)
@click.option("--secrets", "secrets_path", default=_DEFAULT_SECRETS_PATH)
@click.option("-v", "--verbose", is_flag=True, default=False)
@_handle_errors
def _generate_logs(
    config_path: str,
    secrets_path: str,
    verbose: bool,
) -> None:

    settings, warehouse = _bootstrap(config_path, secrets_path)
    digester = OpenRouterDigester(
        settings.openrouter_model, settings.openrouter_api_key
    )
    generate_logs(warehouse, digester, min_news_threshold=settings.min_log_news_threshold)
    click.echo("generate-logs: done")


@cli.command("report")
@click.option("--config", "config_path", default=_DEFAULT_CONFIG_PATH)
@click.option("--secrets", "secrets_path", default=_DEFAULT_SECRETS_PATH)
@click.option("-v", "--verbose", is_flag=True, default=False)
@_handle_errors
def _report(config_path: str, secrets_path: str, verbose: bool) -> None:

    _, warehouse = _bootstrap(config_path, secrets_path)
    document = build_report(warehouse, _now)
    output = MarkdownRenderer().render(document)
    click.echo(output)
