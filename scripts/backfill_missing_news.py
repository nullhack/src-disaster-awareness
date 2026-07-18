"""Backfill news/logs dropped by the initial v4→v5 migration.

The initial migration commit (3b2aec3) dropped ~73 of 912 v4 news URLs.
This script re-reads origin/db and restores them, resolving the v4→v5
incident mapping by where each v4 incident's reports ACTUALLY live in
the current v5 tree (handles the 2 cases where the migration commit was
polluted by a follow-up pipeline run that birthed uuid4 incidents and
displaced the deterministic uuid5 mapping).

Restores:
  1. News items whose URL is missing from the v5 tree (writes to staging,
     then assigns to the v5 incident holding the corresponding v4 report).
  2. (incident_id, log_date) log entries present in v4 but absent in v5
     (adds them with the v4 news provenance set; existing v5 logs untouched).

Idempotent: re-runs are no-ops for already-restored rows. Skips any news
already summarized in v5 to preserve v5's timeline.

Examples::

    PYTHONPATH=. uv run python scripts/backfill_missing_news.py --tree-root data
    PYTHONPATH=. uv run python scripts/backfill_missing_news.py --tree-root data --dry-run
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, cast

from disaster_report.models import IncidentLog, NewsItem
from disaster_report.store import _tree
from disaster_report.store.content import ContentStore

DB_BRANCH = "origin/db"
DB_PATH_IN_BRANCH = "disaster_report.db"


def _extract_db(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "show", f"{DB_BRANCH}:{DB_PATH_IN_BRANCH}"]  # noqa: S607
    blob = subprocess.run(cmd, capture_output=True, check=True).stdout  # noqa: S603
    dest.write_bytes(blob)


def _incident_uuid_v5(v4_inc_id: int) -> str:
    return uuid.uuid5(_tree.NAMESPACE, f"incident:{v4_inc_id}").hex


def _build_v4_to_v5_incident_map(conn: sqlite3.Connection, store: ContentStore) -> dict[int, str]:
    """For each v4 incident_id, return the v5 iuuid that currently holds its reports.

    Falls back to the deterministic uuid5 mapping when no report link exists.
    """
    mapping: dict[int, str] = {}
    rows = conn.execute(
        "SELECT incident_id, report_id FROM report_incidents"
    ).fetchall()
    for v4_inc, v4_rep in rows:
        if v4_inc in mapping:
            continue
        rep = conn.execute(
            "SELECT source, source_id FROM source_reports WHERE report_id=?",
            (v4_rep,),
        ).fetchone()
        if rep is None:
            continue
        ruuid = _tree.report_uuid(rep["source"], rep["source_id"])
        current = cast("Any", store)._report_incident.get(ruuid)
        mapping[v4_inc] = current if current else _incident_uuid_v5(v4_inc)
    # Fallback: incidents that have news but no report link
    for row in conn.execute("SELECT DISTINCT incident_id FROM news_incidents"):
        v4_inc = row["incident_id"]
        if v4_inc not in mapping:
            mapping[v4_inc] = _incident_uuid_v5(v4_inc)
    return mapping


def _phase_a_backfill_news(conn, store, v4_news_to_uuid, *, dry_run) -> set[str]:
    backfilled: set[str] = set()
    for row in conn.execute("SELECT * FROM news_items"):
        nuuid = v4_news_to_uuid[row["news_id"]]
        if nuuid in store._news:
            continue
        if not dry_run:
            item = NewsItem(
                url=row["url"],
                title=row["title"],
                body=row["body"],
                published_date=row["published_date"],
                source=row["source"],
                domain=row["domain"],
                image=row["image"],
            )
            store.ingest_news_item(item)
        backfilled.add(nuuid)
    return backfilled


def _phase_b_assign(conn, store, v4_to_v5, v4_news_to_uuid, backfilled, *, dry_run) -> int:
    assignments = 0
    for row in conn.execute("SELECT * FROM news_incidents"):
        nuuid = v4_news_to_uuid.get(row["news_id"])
        if nuuid is None or nuuid not in backfilled:
            continue
        target = v4_to_v5.get(row["incident_id"])
        if target is None:
            continue
        if not dry_run:
            store.assign_news_to_incident(nuuid, target)
        assignments += 1
    return assignments


def _phase_c_logs(conn, store, v4_to_v5, v4_news_to_uuid, *, dry_run) -> tuple[int, int]:
    new_logs = 0
    new_prov = 0
    for row in conn.execute("SELECT * FROM incident_logs"):
        v4_inc = row["incident_id"]
        iuuid = v4_to_v5.get(v4_inc) or _incident_uuid_v5(v4_inc)
        if iuuid not in store._incidents:
            continue
        if row["log_date"] in store._logs.get(iuuid, {}):
            continue
        prov_uuids = {
            v4_news_to_uuid[n["news_id"]]
            for n in conn.execute(
                "SELECT news_id FROM incident_log_news WHERE incident_id = ? AND log_date = ?",
                (v4_inc, row["log_date"]),
            )
            if n["news_id"] in v4_news_to_uuid
            and v4_news_to_uuid[n["news_id"]] in store._news
        }
        if not dry_run:
            store.append_timeline_with_provenance(
                IncidentLog(
                    incident_id=iuuid,
                    log_date=row["log_date"],
                    summary=row["summary"],
                ),
                prov_uuids,
            )
        new_logs += 1
        new_prov += len(prov_uuids)
    return new_logs, new_prov


def backfill(db_file: Path, tree_root: Path, *, dry_run: bool) -> None:
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    store = ContentStore(tree_root)

    v4_to_v5 = _build_v4_to_v5_incident_map(conn, store)
    v4_news_to_uuid: dict[int, str] = {
        row["news_id"]: _tree.news_uuid(row["url"])
        for row in conn.execute("SELECT news_id, url FROM news_items")
    }

    backfilled = _phase_a_backfill_news(conn, store, v4_news_to_uuid, dry_run=dry_run)
    print(f"missing news_items backfilled: {len(backfilled)}", file=sys.stderr)
    assignments = _phase_b_assign(conn, store, v4_to_v5, v4_news_to_uuid, backfilled, dry_run=dry_run)
    print(f"news_incidents assignments: {assignments}", file=sys.stderr)
    new_logs, new_prov = _phase_c_logs(conn, store, v4_to_v5, v4_news_to_uuid, dry_run=dry_run)
    print(f"new logs: {new_logs} (provenance links: {new_prov})", file=sys.stderr)

    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree-root", default="data", help="content tree root (default: data)")
    parser.add_argument("--db", default=None, help="local sqlite db path (default: extract origin/db)")
    parser.add_argument("--dry-run", action="store_true", help="report counts without writing")
    args = parser.parse_args()

    tree_root = Path(args.tree_root)
    if args.db:
        backfill(Path(args.db), tree_root, dry_run=args.dry_run)
        return
    with tempfile.TemporaryDirectory(prefix="v4-backfill-") as td:
        db_file = Path(td) / "disaster_report.db"
        print(f"extracting {DB_BRANCH}:{DB_PATH_IN_BRANCH} -> {db_file}", file=sys.stderr)
        _extract_db(db_file)
        backfill(db_file, tree_root, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
