"""One-shot: merge duplicate Puerto Madero earthquake incidents.

Merges the M 6.0 initial report (us7000t1cc, runtime birth) into the
M 7.3 final report (us7000t1bu) — they're the same real-world earthquake
that USGS revised. Target (M 7.3) has more news and is the final magnitude.

Idempotent: if source is already gone, exits 0 without changes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from disaster_report.store.content import ContentStore

SOURCE_INCIDENT = "270e9b015d554056b4e6758dbbb88ad9"  # M 6.0 Puerto Madero
TARGET_INCIDENT = "03d6656ab47645eab6a22be7f2170f89"  # M 7.3 Puerto Madero


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree-root", default="data")
    parser.add_argument("--source", default=SOURCE_INCIDENT)
    parser.add_argument("--target", default=TARGET_INCIDENT)
    args = parser.parse_args()

    store = ContentStore(args.tree_root)
    incidents = {i.incident_id for i in store.read_incidents()}
    if args.source not in incidents:
        print(f"source {args.source} not present (already merged?)", file=sys.stderr)
        return 0
    if args.target not in incidents:
        print(f"target {args.target} not present — aborting", file=sys.stderr)
        return 1

    source_news_before = len(store.read_news(args.source))
    target_news_before = len(store.read_news(args.target))

    store.merge_incidents(args.source, args.target)

    incidents_after = {i.incident_id for i in store.read_incidents()}
    target_news_after = len(store.read_news(args.target))
    print(
        f"merged: source={args.source[:8]} ({source_news_before} news) "
        f"-> target={args.target[:8]} "
        f"(news: {target_news_before} -> {target_news_after})",
        file=sys.stderr,
    )
    print(
        f"source in incidents after: {args.source in incidents_after} "
        f"(should be False)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
