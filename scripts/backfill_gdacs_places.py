"""Backfill GDACS report places after adapter parsing fix.

Re-fetches GDACS RSS, re-parses each item, and overwrites places on any
existing report (idempotent on natural key). Reports no longer in the
7-day RSS window are skipped (their places cannot be recomputed).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from disaster_report.sources.gdacs import GDACSAdapter
from disaster_report.store.content import ContentStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree-root", default="data")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    store = ContentStore(args.tree_root)
    existing = store.read_source_report_keys()
    reports = GDACSAdapter().fetch()
    print(f"gdacs: {len(reports)} items in feed; {sum(1 for k in existing if k.startswith('GDACS:'))} in tree", file=sys.stderr)

    repaired = 0
    skipped = 0
    for report in reports:
        natural = f"{report.source}:{report.source_id}"
        if natural not in existing:
            skipped += 1
            continue
        if args.dry_run:
            print(f"  would repair {report.source_id} → {[(p.country_code, p.subdivision) for p in report.places]}", file=sys.stderr)
            repaired += 1
            continue
        rid = store.ingest_source_report(report)
        store.ingest_report_places(rid, report.places)
        repaired += 1

    print(f"backfill: repaired={repaired} skipped(not-in-tree)={skipped} dry-run={args.dry_run}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
