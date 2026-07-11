"""Fix bad-dated news items by re-fetching real publish dates from DDG.

Targets news items with sub-second crawl timestamps on 2026-07-08 (the DDG
crawl-timestamp bug pre-fix 226b826). For each, searches DDG by title,
matches results by URL, and updates published_date in the DB.

Respects DDG rate limits (3s between calls). Uses logging for visibility.

Usage:
    python scripts/fix_news_dates.py [--config CONFIG] [--secrets SECRETS] [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

_DEFAULT_DB = "disaster_report.db"
_MIN_DELAY_SECONDS = 3.0

logger = logging.getLogger("fix_news_dates")


def _is_crawl_timestamp(date_str: str) -> bool:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return abs((datetime.now(timezone.utc) - dt).total_seconds()) < 120


def _urls_match(url_a: str, url_b: str) -> bool:
    if url_a == url_b:
        return True
    path_a = urlparse(url_a).path.rstrip("/")
    path_b = urlparse(url_b).path.rstrip("/")
    return path_a == path_b and bool(path_a)


def _fetch_bad_news(db_path: str) -> list[tuple[int, str, str, str]]:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """
        SELECT news_id, url, title, published_date
        FROM news_items
        WHERE published_date LIKE '2026-07-08T%'
          AND published_date NOT LIKE '2026-07-08T00:00:00%'
        ORDER BY news_id
        """,
    )
    rows = c.fetchall()
    conn.close()
    return rows


def _update_date(db_path: str, news_id: int, new_date: str) -> None:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        "UPDATE news_items SET published_date = ? WHERE news_id = ?",
        (new_date, news_id),
    )
    conn.commit()
    conn.close()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Fix bad-dated news items via DDG re-fetch.",
    )
    parser.add_argument("--db", default=_DEFAULT_DB)
    parser.add_argument("--dry-run", action="store_true", help="Log only, no DB writes")
    parser.add_argument(
        "--delay",
        type=float,
        default=_MIN_DELAY_SECONDS,
        help="Min seconds between DDG calls (default 3.0)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv[1:])

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    from disaster_report.sources.ddg_news import DuckDuckGoNewsAdapter

    bad_news = _fetch_bad_news(args.db)
    logger.info("Found %d bad-dated news items to fix", len(bad_news))

    ddg = DuckDuckGoNewsAdapter()
    fixed = 0
    skipped = 0
    failed = 0

    for i, (news_id, url, title, old_date) in enumerate(bad_news, 1):
        query = title[:100]
        logger.info(
            "[%d/%d] news_id=%d query=%r",
            i,
            len(bad_news),
            news_id,
            query,
        )

        results = ddg.search(query=query, timelimit=None)
        matched_date = None
        for r in results:
            if _urls_match(r.url, url):
                if not _is_crawl_timestamp(r.published_date):
                    matched_date = r.published_date
                    logger.info(
                        "  MATCH url=%s -> published_date=%s",
                        r.url[:80],
                        matched_date,
                    )
                    break
                logger.debug("  match but still crawl timestamp: %s", r.published_date)

        if matched_date is None:
            logger.warning("  NO MATCH found for news_id=%d url=%s", news_id, url[:80])
            failed += 1
        else:
            logger.info(
                "  UPDATE news_id=%d: %s -> %s",
                news_id,
                old_date,
                matched_date,
            )
            if not args.dry_run:
                _update_date(args.db, news_id, matched_date)
            fixed += 1

        elapsed = time.monotonic() - ddg._last_call_time
        if elapsed < args.delay:
            time.sleep(args.delay - elapsed)

    logger.info(
        "Done: %d fixed, %d skipped, %d failed (of %d total)",
        fixed,
        skipped,
        failed,
        len(bad_news),
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
