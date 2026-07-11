"""Backfill incident_logs with weekly granularity from existing news data.

For each incident with news, chunks news by ISO week and summarizes each
weekly batch through the LLM digester. Only writes a log row when the digester
reports has_relevant_updates=True. News in skipped batches stays un-marked
and will be re-evaluated on the next run.

ADDITIVE only — does NOT delete existing logs. Skips incidents/weeks that
already have a log row (idempotent, safe to re-run).

No re-ingest of source reports or news — operates purely on existing data.

Usage:
    python scripts/backfill_weekly_logs.py [--config CONFIG] [--secrets SECRETS]
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_CONFIG_PATH = "config.toml"
_DEFAULT_SECRETS_PATH = "~/.secrets/disaster_report.env"


def _iso_week_key(dt: datetime) -> tuple[int, int]:
    iso_year, iso_week, _ = dt.isocalendar()
    return (iso_year, iso_week)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill weekly incident_logs from existing news data.",
    )
    parser.add_argument("--config", default=_DEFAULT_CONFIG_PATH)
    parser.add_argument("--secrets", default=_DEFAULT_SECRETS_PATH)
    args = parser.parse_args(argv[1:])

    from disaster_report.ai.openrouter import OpenRouterDigester
    from disaster_report.config import Settings
    from disaster_report.models import IncidentLog
    from disaster_report.pipeline import _places_payload
    from disaster_report.store.base import Warehouse

    settings = Settings.load(
        config_path=args.config,
        secrets_path=str(Path(args.secrets).expanduser()),
    )
    wh = Warehouse(settings.db_url, clock=lambda: datetime.now(timezone.utc))
    digester = OpenRouterDigester(settings.openrouter_model, settings.openrouter_api_key)

    incidents = wh.read_incidents()
    print(f"Backfilling logs for {len(incidents)} incidents...", file=sys.stderr)

    total_logs = 0
    total_calls = 0
    total_skipped = 0

    for incident in incidents:
        already_linked = wh.read_summarized_news_ids(incident.incident_id)
        all_news = wh.read_news(incident.incident_id)
        unsummarized = [n for n in all_news if n.news_id not in already_linked]
        if not unsummarized:
            continue

        weeks: dict[tuple[int, int], list] = defaultdict(list)
        for n in unsummarized:
            dt = datetime.fromisoformat(n.published_date)
            weeks[_iso_week_key(dt)].append(n)

        sorted_weeks = sorted(weeks.keys())
        genesis = wh.read_source_report_by_id(incident.genesis_report_id)
        places = _places_payload(genesis) if genesis is not None else []

        for week_key in sorted_weeks:
            batch = weeks[week_key]
            if len(batch) < 3:
                continue
            batch.sort(key=lambda n: n.published_date)
            prior = wh.read_timeline(incident.incident_id)
            result = digester.summarize(
                batch,
                prior,
                incident_type=incident.incident_type,
                incident_name=incident.name,
                incident_places=places,
                incident_date=incident.first_seen_at,
            )
            total_calls += 1
            if not result.has_relevant_updates:
                total_skipped += 1
                wk_label = f"{week_key[0]}-W{week_key[1]:02d}"
                print(
                    f"  incident {incident.incident_id} week {wk_label}: "
                    f"{len(batch)} news -> SKIPPED (no relevant updates)",
                    file=sys.stderr,
                )
                continue
            log_datetime = max(n.published_date for n in batch)
            if any(log.log_datetime == log_datetime for log in prior):
                log_datetime = wh._clock().isoformat()
            wh.append_timeline_with_provenance(
                IncidentLog(
                    incident_id=incident.incident_id,
                    log_datetime=log_datetime,
                    summary=result.summary,
                ),
                {n.news_id for n in batch},
            )
            total_logs += 1
            wk_label = f"{week_key[0]}-W{week_key[1]:02d}"
            print(
                f"  incident {incident.incident_id} week {wk_label}: "
                f"{len(batch)} news -> log@{log_datetime}",
                file=sys.stderr,
            )

    print(
        f"Done. {total_logs} logs written, {total_skipped} skipped "
        f"({total_calls} LLM calls).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
