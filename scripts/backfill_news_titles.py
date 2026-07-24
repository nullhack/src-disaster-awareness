"""Backfill generic news titles (MSN, Client Challenge) from URL slugs.

Walks every news YAML under data/incidents/.../logs/.../news/ and rewrites
the `title` field when it is a known generic value, deriving a human-readable
title from the article URL slug. Only the `title:` line is rewritten; the rest
of the file is preserved byte-for-byte.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from disaster_report.sources.ddg_news import derive_title_from_slug, is_generic_title

_TITLE_LINE_RE = re.compile(r"^(?P<key>title): (?P<value>.*)$", re.MULTILINE)
_URL_LINE_RE = re.compile(r"^url: (?P<value>.*)$", re.MULTILINE)


def _replace_title_line(text: str, new_title: str) -> str:
    return _TITLE_LINE_RE.sub(
        lambda m: f"{m.group('key')}: {new_title}", text, count=1
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill generic news titles from URL slugs"
    )
    parser.add_argument(
        "--tree-root",
        default="data",
        help="Data tree root (default: data)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without writing files",
    )
    args = parser.parse_args()

    news_files = sorted(
        Path(args.tree_root).glob("incidents/*/logs/*/news/*.yaml")
    )
    changed = 0
    skipped = 0

    for f in news_files:
        text = f.read_text(encoding="utf-8")
        title_match = _TITLE_LINE_RE.search(text)
        if not title_match:
            continue
        title = title_match.group("value")
        if not is_generic_title(title):
            skipped += 1
            continue
        url_match = _URL_LINE_RE.search(text)
        if not url_match:
            print(f"SKIP (no url): {f.name}")
            skipped += 1
            continue
        url = url_match.group("value").strip()
        new_title = derive_title_from_slug(url)
        if not new_title:
            print(f"SKIP (no slug derivable): {f.name} — {url[:80]}")
            skipped += 1
            continue
        if args.dry_run:
            print(f"  {title!r} -> {new_title!r}")
        else:
            f.write_text(_replace_title_line(text, new_title), encoding="utf-8")
        changed += 1

    print(f"\n{changed} titles updated, {skipped} skipped")


if __name__ == "__main__":
    main()
