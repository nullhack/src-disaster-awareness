"""One-shot trafilatura enrichment for news linked to active incidents.

Walks ``active_incidents(window)``, reads each incident's news, and for every
news item missing ``author`` or ``sitename`` fetches the source URL via
``fetch_article`` and writes the enriched metadata (title, body description,
published_date, author, sitename) back to the YAML file in place. Sleeps
``--spacing`` seconds between HTTP calls to be polite to publishers.

After enrichment (if any items were updated), commits on the local ``data``
worktree. Does NOT push to remote — push manually when ready::

    git -C data push origin HEAD:data

Re-run-safe: items already carrying author + sitename are skipped. Intended to
run in a separate tab while the orchestrator pipeline runs elsewhere. Requires
``data/`` to be attached as a worktree on ``origin/data``::

    git worktree add data origin/data

Examples::

    uv run python scripts/enrich_active_news.py
    uv run python scripts/enrich_active_news.py --window 30 --spacing 10
    uv run python scripts/enrich_active_news.py --dry-run
    uv run python scripts/enrich_active_news.py --no-commit
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from disaster_report.fetchers import fetch_article
from disaster_report.store._tree import dump_yaml, load_yaml
from disaster_report.store.content import ContentStore


def _is_enriched(news: Any) -> bool:
    return bool(getattr(news, "author", "")) and bool(getattr(news, "sitename", ""))


def _collect_targets(store: ContentStore, window: int) -> list[tuple[str, Any, Any]]:
    targets: list[tuple[str, Any, Any]] = []
    for inc in store.active_incidents(window):
        for news in store.read_news(inc.incident_id):
            if _is_enriched(news):
                continue
            targets.append((inc.incident_id, news.news_id, news))
    return targets


def _enrich_one(store: ContentStore, news: Any) -> bool:
    nuuid: str = news.news_id
    url: str = news.url
    if not nuuid or not url:
        return False
    path = store._news_path.get(nuuid)  # type: ignore[attr-defined]
    if path is None or not path.exists():
        print(f"    no path on disk for news={nuuid[:8]}")
        return False
    fetched = fetch_article(url)
    if fetched is None:
        return False
    data = load_yaml(path)
    if not isinstance(data, dict):
        return False
    if fetched.title:
        data["title"] = fetched.title
    if fetched.description:
        data["body"] = fetched.description
    if fetched.published_date:
        data["published_date"] = fetched.published_date
    data["author"] = fetched.author or data.get("author", "")
    data["sitename"] = fetched.sitename or data.get("sitename", "")
    dump_yaml(path, data)
    return True


def _commit(tree_root: Path, count: int) -> None:
    msg = f"chore(data): enrich active news — {count} items via trafilatura"
    print(f"\ngit commit on data branch: {msg}")
    subprocess.run(["git", "-C", str(tree_root), "add", "-A"], check=True)  # noqa: S603, S607
    subprocess.run(["git", "-C", str(tree_root), "commit", "-m", msg], check=True)  # noqa: S603, S607
    print("committed locally. push when ready: git -C data push origin HEAD:data")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enrich active-incident news with trafilatura, commit on local data branch."
    )
    parser.add_argument("--tree-root", default="data", help="content tree root (default: data)")
    parser.add_argument(
        "--window", type=int, default=7, help="active_incidents window in days (default: 7)"
    )
    parser.add_argument(
        "--spacing", type=float, default=10.0, help="seconds between HTTP fetches (default: 10)"
    )
    parser.add_argument("--dry-run", action="store_true", help="list targets without fetching")
    parser.add_argument("--no-commit", action="store_true", help="skip the git commit at the end")
    args = parser.parse_args()

    tree_root = Path(args.tree_root)
    store = ContentStore(str(tree_root))
    active = store.active_incidents(args.window)
    print(f"active window={args.window}d -> {len(active)} incidents")
    targets = _collect_targets(store, args.window)
    print(f"news needing enrichment: {len(targets)}")

    if args.dry_run:
        for inc_id, nuuid, news in targets:
            print(f"  incident={inc_id[:8]} news={nuuid[:8]} url={news.url}")
        return 0

    enriched = 0
    failed = 0
    for i, (inc_id, nuuid, news) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] incident={inc_id[:8]} news={nuuid[:8]} {news.url}")
        ok = _enrich_one(store, news)
        if ok:
            enriched += 1
            print("    enriched")
        else:
            failed += 1
            print("    skipped/failed")
        if i < len(targets):
            time.sleep(args.spacing)

    print(f"\nsummary: enriched={enriched} skipped/failed={failed} total={len(targets)}")

    if args.no_commit or enriched == 0:
        return 0
    _commit(tree_root, enriched)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
