from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

import click

from disaster_report.ai.openrouter import OpenRouterDigester
from disaster_report.classification import configure_disease_tiers, configure_endemics
from disaster_report.config import Config
from disaster_report.pipeline import Pipeline
from disaster_report.report import (
    NEWS_CAP_DEFAULT,
    SEVERITY_CHOICES,
    db_path_from_url,
    generate as generate_report,
)
from disaster_report.resolver import IncidentResolver
from disaster_report.sources.registry import SOURCE_REGISTRY
from disaster_report.store import SqliteIncidentStore

_OPENROUTER_AUTH_FALLBACK = Path.home() / ".local/share/opencode/auth.json"

# Adapter registries are derived from the single SOURCE_REGISTRY in
# sources.registry, filtered by source_type ("feed" -> incidents, "news" ->
# searchable article adapter).
_SOURCE_REGISTRY = {
    token: spec.adapter_cls
    for token, spec in SOURCE_REGISTRY.items()
    if spec.source_type == "feed"
}
_NEWS_REGISTRY = {
    token: spec.adapter_cls
    for token, spec in SOURCE_REGISTRY.items()
    if spec.source_type == "news"
}

# Mirrors _SOURCE_REGISTRY/_NEWS_REGISTRY so the digester is wired by config
# token too, not by a hard-coded concrete import at the call site.
_DIGESTER_REGISTRY = {
    "openrouter": OpenRouterDigester,
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
    config = Config.from_toml(config_path)
    configure_disease_tiers(
        pandemic_risk=config.pandemic_risk_diseases,
        outbreak_of_concern=config.outbreak_of_concern_diseases,
    )
    configure_endemics(config.endemic_diseases)
    return config


def _build_sources(config: Config) -> list:
    sources = []
    for name in config.sources_enabled:
        token = name.lower()
        factory = _SOURCE_REGISTRY.get(token)
        if factory is None:
            raise click.ClickException(f"unknown source: {name}")
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
    factory = _DIGESTER_REGISTRY.get((config.ai_provider or "").lower())
    if factory is None:
        raise click.ClickException(f"unknown ai provider: {config.ai_provider}")
    return factory(
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
@click.option("--window", type=int, help="Override tracking_window_days.")
@click.option(
    "--min-severity",
    type=click.Choice(SEVERITY_CHOICES, case_sensitive=False),
    default="HIGH",
    help="Lowest severity to show (default HIGH = HIGH+CRITICAL).",
)
@click.option(
    "--news",
    type=int,
    default=NEWS_CAP_DEFAULT,
    help="Max news articles to list per incident (default 5).",
)
@click.option("--out", type=click.Path(), help="Write to file instead of stdout.")
@click.option("--as-of", help="Override 'today' (YYYY-MM-DD).")
def report(config_path: str, window: int, min_severity: str, news: int,
           out: str, as_of: str) -> None:
    """Generate a Markdown disaster report.

    Two parts (geophysical & weather first, disease outbreaks second), grouped
    by severity and ordered by news volume. Only incidents with ``should_report=1``
    whose ``event_date`` falls in the tracking window are listed.
    """
    config = _load(config_path)
    db_path = db_path_from_url(config.database_url)
    win = window if window is not None else config.tracking_window_days
    as_of_date = date.fromisoformat(as_of) if as_of else date.today()
    text = generate_report(
        db_path, as_of=as_of_date, window=win,
        min_severity=min_severity, news_cap=news,
    )
    if out:
        Path(out).write_text(text + "\n")
        click.echo(f"wrote {out}", err=True)
    else:
        click.echo(text)


@app.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option(
    "--apply",
    is_flag=True,
    help="Persist changes. Without this flag the command is a dry-run.",
)
def reclassify(config_path: str, apply: bool) -> None:
    """Backfill priority + should_report from current severity (monotonic).

    Default is a dry-run. Pass --apply to persist. Idempotent: a second run
    reports no deltas. Non-destructive: never re-derives severity from events
    and never demotes an incident.
    """
    config = _load(config_path)
    store = SqliteIncidentStore(config.database_url)
    deltas = store.reclassify_all(dry_run=not apply)
    mode = "applied" if apply else "dry-run"
    if not deltas:
        click.echo(f"reclassify ({mode}): no changes")
        return
    click.echo(f"reclassify ({mode}): {len(deltas)} incident(s) changed")
    for delta in deltas:
        click.echo(
            f"- {delta['incident_id']} [{delta['severity']}] "
            f"priority {delta['priority']['from']} -> {delta['priority']['to']}, "
            f"should_report {delta['should_report']['from']} -> {delta['should_report']['to']}"
        )


@app.command()
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option(
    "--apply",
    is_flag=True,
    help="Issue AI digest requests and persist results. Without this flag the "
    "command only reports what would be re-digested (no API calls).",
)
@click.option(
    "--limit",
    type=int,
    default=0,
    help="Max incidents to re-digest (0 = all). Use for chunking under rate limits.",
)
@click.option(
    "--undigested",
    "undigested_only",
    is_flag=True,
    help="Only target incidents with no AI digest yet (ai_digest_date_key IS NULL).",
)
def redigest(config_path: str, apply: bool, limit: int, undigested_only: bool) -> None:
    """Re-run AI digestion on existing incidents to populate pandemic_potential
    and event_status for the disease track.

    Iterates all incidents (or --limit, or --undigested for only those missing a
    digest) using existing store methods, feeds each incident's stored source
    records + linked news back through the digester, and applies the digest via
    the monotonic set_digest ratchet.
    """
    config = _load(config_path)
    store = SqliteIncidentStore(config.database_url)
    if undigested_only:
        incident_ids = store.undigested_incident_ids()
        scope = "undigested"
    else:
        incident_ids = store.all_incident_ids()
        scope = "all"
    if limit > 0:
        incident_ids = incident_ids[:limit]
    if not apply:
        click.echo(
            f"redigest (dry-run, {scope}): {len(incident_ids)} incident(s) would be re-digested"
        )
        return
    digester = _build_digester(config)
    today = date.today()
    succeeded = 0
    failed = 0
    for incident_id in incident_ids:
        view = store.find_by_incident_id(incident_id)
        if view is None:
            continue
        materials = {
            "source_reports": store.get_source_records(view.incident_key),
            "news_articles": store.get_incident_news_full(view.incident_key),
        }
        try:
            digest = digester.digest(materials)
        except Exception as exc:
            failed += 1
            click.echo(f"- {incident_id}: digest failed: {exc}", err=True)
            continue
        store.set_digest(view.incident_key, digest, today, view.country_name)
        succeeded += 1
        # Re-fetch so the log shows the DERIVED canonical_name/search_keys that
        # set_digest persisted (single source of truth), plus the AI bits just
        # produced (read from the digest dict - IncidentView has no AI fields).
        fresh = store.find_by_incident_id(incident_id) or view
        ai_bits = []
        for key, label in (
            ("disease_name", "disease"),
            ("severity", "sev"),
            ("pandemic_potential", "pp"),
            ("event_status", "es"),
        ):
            value = digest.get(key)
            if value:
                ai_bits.append(f"{label}={value}")
        summary = " ".join((digest.get("summary") or "").split())
        if len(summary) > 80:
            summary = summary[:77] + "..."
        bits_str = " ".join(ai_bits)
        bits_str = f"{bits_str} | " if bits_str else ""
        click.echo(
            f"- {incident_id} | {fresh.canonical_name} | "
            f"{bits_str}{summary!r} | keys={list(fresh.search_keys or [])}"
        )
    click.echo(f"redigest (applied, {scope}): {succeeded} re-digested, {failed} failed")


if __name__ == "__main__":
    app()
