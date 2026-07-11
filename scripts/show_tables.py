"""Print a sample of each SQLite table as an ASCII box table.

Inspector utility for the disaster report database: discovers tables from
sqlite_master, then renders a configurable number of sample rows per table
using only the standard library (no tabulate/rich dependency).

Usage:
    python scripts/show_tables.py [DATABASE] [-n N]

DATABASE defaults to ./disaster_report.db (matches config._DEFAULT_DB_URL).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any

_MAX_CELL_WIDTH = 50
_TRUNCATE_MARKER = "..."
_TABLES_QUERY = (
    "SELECT name FROM sqlite_master "
    "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
    "ORDER BY name"
)


def _truncate(value: Any, width: int = _MAX_CELL_WIDTH) -> str:
    if value is None:
        return "NULL"
    text = str(value).replace("\n", " ").replace("\t", " ")
    if len(text) <= width:
        return text
    return text[: width - len(_TRUNCATE_MARKER)] + _TRUNCATE_MARKER


def _render_box(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if len(cell) > widths[i]:
                widths[i] = len(cell)

    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def render_row(values: list[str]) -> str:
        return (
            "| " + " | ".join(v.ljust(widths[i]) for i, v in enumerate(values)) + " |"
        )

    lines = [border, render_row(headers), border]
    lines.extend(render_row(row) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def _sample_table(conn: sqlite3.Connection, name: str, sample_size: int) -> None:
    quoted = '"' + name.replace('"', '""') + '"'
    total = conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]  # noqa: S608
    plural = "s" if total != 1 else ""
    print(f"\n=== {name}  ({total} row{plural}) ===")
    if total == 0:
        print("  (table is empty)")
        return
    cursor = conn.execute(
        f"SELECT * FROM {quoted} ORDER BY rowid LIMIT ?",  # noqa: S608
        (sample_size,),
    )
    headers = [d[0] for d in cursor.description]
    sample = [[_truncate(v) for v in row] for row in cursor.fetchall()]
    print(_render_box(headers, sample))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Show a sample of each SQLite table as an ASCII box table.",
    )
    parser.add_argument(
        "database",
        nargs="?",
        default="disaster_report.db",
        help="SQLite database path (default: ./disaster_report.db)",
    )
    parser.add_argument(
        "-n",
        "--sample-size",
        type=int,
        default=1,
        help="rows per table to display (default: 1)",
    )
    args = parser.parse_args(argv[1:])

    path = Path(args.database)
    if not path.is_file():
        print(f"error: database not found: {path}", file=sys.stderr)
        return 2
    if args.sample_size < 1:
        print("error: --sample-size must be >= 1", file=sys.stderr)
        return 2

    from disaster_report.store.base import Warehouse

    Warehouse(f"sqlite:///{path}")
    conn = sqlite3.connect(path)
    try:
        tables = [r[0] for r in conn.execute(_TABLES_QUERY).fetchall()]
        if not tables:
            print(f"no tables in {path}", file=sys.stderr)
            return 1
        plural = "s" if len(tables) != 1 else ""
        print(f"database: {path}  ({len(tables)} table{plural})")
        for name in tables:
            _sample_table(conn, name, args.sample_size)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
