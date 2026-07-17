"""Manual incident insertion scaffold for the v5 git-backed store.

Births a new incident from a source report, with optional places, a timeline
log, and a linked news item. Idempotent: re-running with the same
``--source/--source-id`` reuses the existing report; the incident is always
minted fresh (opaque uuid4) unless ``--incident-id`` is given.

Examples::

    # Minimal: a geophysical incident from a USGS report
    uv run python scripts/new_incident.py \\
        --source USGS --source-id us7000abcd \\
        --type "Earthquake" --name "M 6.0 - Test" --date 2026-07-17

    # Disease outbreak with a place, log, and linked news
    uv run python scripts/new_incident.py \\
        --source WHO --source-id 2026_EBOLA_X \\
        --type "Ebola" --name "Ebola outbreak - Country X" --date 2026-07-17 \\
        --country XX --subdivision "Region Y" --locality "City Z" \\
        --summary "Initial report confirms cluster." \\
        --news-url https://example.com/story --news-title "Outbreak reported" \\
        --news-date 2026-07-17

The incident manifest holds ``{id, search_keys}``; genesis identity (name,
type, category, first_seen_at) is derived lazily at read time from the
earliest-dated linked report. Reports and news are co-located under the
incident subtree. To extend the linked news set or timeline, run again with
the same ``--incident-id``.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

# Allow running both as ``python scripts/new_incident.py`` and ``python -m``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from disaster_report._search_keys import derive_repoll_keys
from disaster_report.models import IncidentLog, NewsItem, ReportPlace, SourceReport
from disaster_report.store._tree import (
    incident_manifest_path,
    incident_news_path,
    incident_report_path,
)
from disaster_report.store.content import ContentStore


def _build_report(args: argparse.Namespace) -> SourceReport:
    places: list[ReportPlace] = []
    if args.country or args.subdivision or args.locality:
        places.append(
            ReportPlace(
                country_code=args.country or "",
                subdivision=args.subdivision or "",
                locality=args.locality or "",
            )
        )
    return SourceReport(
        source=args.source,
        source_id=args.source_id,
        incident_type=args.type,
        name=args.name,
        places=places,
        report_date=args.date,
        raw_fields={},
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manually insert a new incident into the v5 content tree.",
    )
    parser.add_argument("--tree-root", default="data", help="content tree root (default: data)")
    parser.add_argument("--source", required=True, help="source name (e.g. USGS, GDACS, WHO, MANUAL)")
    parser.add_argument("--source-id", required=True, help="source-native id")
    parser.add_argument("--type", required=True, help="incident_type (e.g. Earthquake, Ebola)")
    parser.add_argument("--name", required=True, help="incident name / headline")
    parser.add_argument("--date", required=True, help="report date (YYYY-MM-DD)")
    parser.add_argument("--country", default="", help="ISO-2 country code (optional)")
    parser.add_argument("--subdivision", default="", help="subdivision (optional)")
    parser.add_argument("--locality", default="", help="locality (optional)")
    parser.add_argument("--summary", default="", help="timeline log summary (optional)")
    parser.add_argument("--log-date", default="", help="timeline log date (default: --date)")
    parser.add_argument("--news-url", default="", help="linked news url (optional)")
    parser.add_argument("--news-title", default="", help="linked news title")
    parser.add_argument("--news-date", default="", help="linked news published_date")
    parser.add_argument(
        "--incident-id",
        default="",
        help="reuse an explicit incident uuid instead of minting one",
    )
    args = parser.parse_args()

    store = ContentStore(args.tree_root)

    report = _build_report(args)
    report_id = store.ingest_source_report(report)
    store.ingest_report_places(report_id, report.places)

    incident_id = args.incident_id or uuid.uuid4().hex
    store.add_report_incident(report_id, incident_id)
    store.set_search_keys(incident_id, derive_repoll_keys(report))

    news_ids: set[str] = set()
    if args.news_url:
        news = NewsItem(
            url=args.news_url,
            title=args.news_title,
            body="",
            published_date=args.news_date or args.date,
            source=args.source,
            domain="",
            image="",
        )
        nuuid = store.ingest_news_item(news)
        store.assign_news_to_incident(nuuid, incident_id)
        news_ids.add(nuuid)

    if args.summary and news_ids:
        log_date = args.log_date or args.date
        store.append_timeline_with_provenance(
            IncidentLog(incident_id=incident_id, log_date=log_date, summary=args.summary),  # type: ignore[arg-type]
            news_ids,
        )
    elif args.summary:
        log_date = args.log_date or args.date
        store.append_timeline(
            IncidentLog(incident_id=incident_id, log_date=log_date, summary=args.summary)  # type: ignore[arg-type]
        )

    print(f"incident: {incident_manifest_path(Path(args.tree_root), incident_id)}")
    print(f"  report: {incident_report_path(Path(args.tree_root), incident_id, args.source, report_id)}")
    if args.news_url:
        nuuid = next(iter(news_ids))
        print(
            "    news: "
            f"{incident_news_path(Path(args.tree_root), incident_id, nuuid)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
