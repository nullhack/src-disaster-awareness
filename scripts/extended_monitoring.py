"""Toggle extended-monitoring flag on v5 incidents.

Extended-monitoring incidents are always repolled by the search-news pipeline
regardless of news recency, ensuring long-tail events stay tracked even when
dormant.

Examples::

    # Toggle (enable if disabled, disable if enabled)
    uv run python scripts/extended_monitoring.py <incident_uuid>

    # Explicit enable / disable
    uv run python scripts/extended_monitoring.py <incident_uuid> --enable
    uv run python scripts/extended_monitoring.py <incident_uuid> --disable

    # List all extended-monitoring incidents
    uv run python scripts/extended_monitoring.py --list

The flag is stored as ``extended_monitoring: bool`` in
``incidents/<iuuid>/incident.yaml``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, cast

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from disaster_report.store.content import ContentStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "incident_id",
        nargs="?",
        help="incident uuid (omit with --list)",
    )
    parser.add_argument("--tree-root", default="data")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--enable", action="store_true", help="set flag to true")
    mode.add_argument("--disable", action="store_true", help="set flag to false")
    mode.add_argument(
        "--list",
        action="store_true",
        help="list all extended-monitoring incidents",
    )
    args = parser.parse_args()

    store = ContentStore(args.tree_root)

    if args.list:
        incs = store.extended_monitoring_incidents()
        if not incs:
            print("no extended-monitoring incidents")
            return 0
        for inc in incs:
            print(f"{inc.incident_id}  {inc.first_seen_at}  {inc.name}")
        return 0

    if not args.incident_id:
        parser.error("incident_id is required unless --list is given")

    if args.enable:
        target = True
    elif args.disable:
        target = False
    else:
        current = cast(Any, store)._incidents.get(args.incident_id, {}).get(
            "extended_monitoring", False
        )
        target = not current

    store.set_extended_monitoring(args.incident_id, target)
    state = "ENABLED" if target else "DISABLED"
    print(f"extended_monitoring {state} for {args.incident_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
