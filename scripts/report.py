"""Generate a Markdown disaster report from the incident DB.

Thin argparse wrapper around :func:`disaster_report.report.generate`. The same
report is available via the CLI: ``uv run python -m disaster_report.cli report``.

Usage:
    uv run python scripts/report.py --config config.toml
    uv run python scripts/report.py --config config.toml --out report.md
    uv run python scripts/report.py --db disaster.db --min-severity HIGH --news 5
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from datetime import date
from pathlib import Path

from disaster_report.report import (
    NEWS_CAP_DEFAULT,
    SEVERITY_CHOICES,
    db_path_from_url,
    generate,
)


def _load_config(config_path: Path) -> tuple[str, int]:
    with config_path.open("rb") as fh:
        cfg = tomllib.load(fh)
    url = cfg.get("database", {}).get("url", "sqlite:///./disaster.db")
    window = int(cfg.get("tracking", {}).get("window_days", 7))
    return db_path_from_url(url), window


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate a Markdown disaster report.")
    ap.add_argument("--config", type=Path, default=Path("config.toml"),
                    help="Path to config.toml (for DB url + tracking window).")
    ap.add_argument("--db", help="Override DB path (bypasses config parsing).")
    ap.add_argument("--window", type=int, help="Override tracking_window_days.")
    ap.add_argument("--min-severity", choices=list(SEVERITY_CHOICES), default="HIGH",
                    help="Lowest severity to show (default HIGH = HIGH+CRITICAL).")
    ap.add_argument("--news", type=int, default=NEWS_CAP_DEFAULT,
                    help="Max news articles to list per incident (default 5).")
    ap.add_argument("--out", type=Path, help="Write to file instead of stdout.")
    ap.add_argument("--as-of", help="Override 'today' (YYYY-MM-DD).")
    args = ap.parse_args(argv)

    db_path = args.db
    window = args.window
    if db_path is None or window is None:
        cfg_db, cfg_window = _load_config(args.config)
        db_path = db_path or cfg_db
        window = window if window is not None else cfg_window

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    text = generate(db_path, as_of=as_of, window=window,
                    min_severity=args.min_severity, news_cap=args.news)

    if args.out:
        args.out.write_text(text + "\n")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
