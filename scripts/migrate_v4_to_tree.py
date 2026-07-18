"""One-shot migration: v4 SQLite (origin/db branch) -> v5 partitioned YAML tree.

The v4 ``disaster_report.db`` lives on the ``origin/db`` branch (gitignored on
every working branch). This script extracts it via ``git show`` into a tmpfile
(no workspace pollution), iterates the 7 tables, and writes the v5 tree under
``data/`` through :class:`ContentStore` so the on-disk format is identical to
what runtime ingest produces.

ID mapping (deterministic — re-runs produce byte-identical files):
* report_uuid  = uuid5("report:<source>:<source_id>")  -- natural-key derived
* news_uuid    = uuid5("news:<url>")                    -- natural-key derived
* incident_uuid = uuid5("incident:<v4_int_id>")          -- preserves v4 identity

Re-running is a no-op for already-migrated rows (ContentStore ingest is
idempotent on natural keys).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from disaster_report._search_keys import derive_repoll_keys
from disaster_report.models import IncidentLog, NewsItem, ReportPlace, SourceReport
from disaster_report.store import _tree
from disaster_report.store.content import ContentStore

DB_BRANCH = "origin/db"
DB_PATH_IN_BRANCH = "disaster_report.db"


def _extract_db(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "show", f"{DB_BRANCH}:{DB_PATH_IN_BRANCH}"]  # noqa: S607
    blob = subprocess.run(cmd, capture_output=True, check=True).stdout  # noqa: S603
    dest.write_bytes(blob)


def _incident_uuid(v4_id: int) -> str:
    return uuid.uuid5(_tree.NAMESPACE, f"incident:{v4_id}").hex


def _load_raw(raw_text: str) -> tuple[dict, str]:
    try:
        raw = json.loads(raw_text) if raw_text else {}
    except (ValueError, TypeError):
        return ({}, "")
    if not isinstance(raw, dict):
        return ({}, "")
    searched = ""
    if isinstance(raw.get("_news_searched_at"), str):
        searched = raw.pop("_news_searched_at")
    return (raw, searched)


def _materialize_search_keys(store: ContentStore) -> int:
    """Derive ``search_keys`` from each incident's genesis report and persist."""
    key_total = 0
    for inc in store.read_incidents():
        genesis = store.read_source_report_by_id(str(inc.genesis_report_id))
        if genesis is None:
            continue
        keys = derive_repoll_keys(genesis)
        if keys:
            store.set_search_keys(str(inc.incident_id), keys)
            key_total += len(keys)
    return key_total


def migrate(db_file: Path, tree_root: Path) -> None:
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    store = ContentStore(tree_root)

    v4_report_to_uuid: dict[int, str] = {}
    v4_news_to_uuid: dict[int, str] = {}

    # ---- reports + places ----
    for row in conn.execute("SELECT * FROM source_reports"):
        raw, searched = _load_raw(row["raw_fields"])
        places = [
            ReportPlace(
                country_code=p["country_code"],
                subdivision=p["subdivision"],
                locality=p["locality"],
            )
            for p in conn.execute(
                "SELECT * FROM report_places WHERE report_id = ?",
                (row["report_id"],),
            )
        ]
        report = SourceReport(
            source=row["source"],
            source_id=row["source_id"],
            incident_type=row["incident_type"],
            name=row["name"],
            places=places,
            report_date=row["report_date"],
            raw_fields=raw,
            news_searched_at=searched,
        )
        ruuid = store.ingest_source_report(report)
        store.ingest_report_places(ruuid, places)
        v4_report_to_uuid[row["report_id"]] = ruuid
    print(f"reports: {len(v4_report_to_uuid)}", file=sys.stderr)

    # ---- news ----
    for row in conn.execute("SELECT * FROM news_items"):
        item = NewsItem(
            url=row["url"],
            title=row["title"],
            body=row["body"],
            published_date=row["published_date"],
            source=row["source"],
            domain=row["domain"],
            image=row["image"],
        )
        nuuid = store.ingest_news_item(item)
        v4_news_to_uuid[row["news_id"]] = nuuid
    print(f"news: {len(v4_news_to_uuid)}", file=sys.stderr)

    # ---- incidents + report-links ----
    incidents_seen: set[int] = set()
    for row in conn.execute("SELECT * FROM report_incidents"):
        ruuid = v4_report_to_uuid.get(row["report_id"])
        if ruuid is None:
            continue
        iuuid = _incident_uuid(row["incident_id"])
        store.add_report_incident(ruuid, iuuid)
        incidents_seen.add(row["incident_id"])
    # ensure stubs for incidents that have news but no report link yet
    for row in conn.execute("SELECT DISTINCT incident_id FROM news_incidents"):
        _incident_uuid(row["incident_id"])
        incidents_seen.add(row["incident_id"])
    print(f"incidents (distinct): {len(incidents_seen)}", file=sys.stderr)

    # ---- news -> incident (1:1) ----
    linked = 0
    for row in conn.execute("SELECT * FROM news_incidents"):
        nuuid = v4_news_to_uuid.get(row["news_id"])
        if nuuid is None:
            continue
        iuuid = _incident_uuid(row["incident_id"])
        store.assign_news_to_incident(nuuid, iuuid)
        linked += 1
    print(f"news-incidents links: {linked}", file=sys.stderr)

    # ---- logs + provenance ----
    log_count = 0
    provenance = 0
    for row in conn.execute("SELECT * FROM incident_logs"):
        iuuid = _incident_uuid(row["incident_id"])
        news_uuids = {
            v4_news_to_uuid[n["news_id"]]
            for n in conn.execute(
                "SELECT news_id FROM incident_log_news WHERE incident_id = ? AND log_date = ?",
                (row["incident_id"], row["log_date"]),
            )
            if n["news_id"] in v4_news_to_uuid
        }
        store.append_timeline_with_provenance(
            IncidentLog(
                incident_id=iuuid,
                log_date=row["log_date"],
                summary=row["summary"],
            ),
            news_uuids,
        )
        log_count += 1
        provenance += len(news_uuids)
    print(f"logs: {log_count} (provenance links: {provenance})", file=sys.stderr)

    conn.close()

    key_total = _materialize_search_keys(store)
    incidents = store.read_incidents()
    print(
        f"search_keys: {key_total} keys across {len(incidents)} incidents",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree-root", default="data", help="output tree root")
    parser.add_argument(
        "--db",
        default=None,
        help="local path to v4 sqlite db (default: extract from origin/db)",
    )
    args = parser.parse_args()

    tree_root = Path(args.tree_root)
    if args.db:
        migrate(Path(args.db), tree_root)
        return
    with tempfile.TemporaryDirectory(prefix="v4-migrate-") as td:
        db_file = Path(td) / "disaster_report.db"
        print(f"extracting {DB_BRANCH}:{DB_PATH_IN_BRANCH} -> {db_file}", file=sys.stderr)
        _extract_db(db_file)
        migrate(db_file, tree_root)


if __name__ == "__main__":
    main()
