"""collapse incident_logs to one row per incident per day (log_date)

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-07-16 12:00:00.000000

Renames ``incident_logs.log_datetime`` -> ``log_date`` and shifts the
PK to ``(incident_id, log_date)`` so there is at most one log per
incident per calendar day. Multiple generate-logs runs on the same day
now upsert into that day's row (summaries concatenated) instead of
inserting distinct timestamped rows.

``incident_log_news`` is rebuilt with the same ``log_date`` key. Existing
same-day duplicate log groups are consolidated: summaries are merged
(datetime-ascending order, joined by a blank line), news links are
re-keyed to the truncated date. ``INSERT OR IGNORE`` drops any duplicate
news link that surfaces from the merge.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CREATE_LOGS_NEW_SQL = (
    "CREATE TABLE incident_logs_new ("
    "incident_id INTEGER NOT NULL, "
    "log_date VARCHAR NOT NULL, "
    "summary VARCHAR NOT NULL, "
    "PRIMARY KEY (incident_id, log_date))"
)

_CREATE_LOG_NEWS_SQL = (
    "CREATE TABLE incident_log_news ("
    "incident_id INTEGER NOT NULL, "
    "log_date VARCHAR NOT NULL, "
    "news_id INTEGER NOT NULL, "
    "PRIMARY KEY (incident_id, log_date, news_id), "
    "FOREIGN KEY (incident_id, log_date) "
    "REFERENCES incident_logs (incident_id, log_date) ON DELETE CASCADE, "
    "FOREIGN KEY (news_id) REFERENCES news_items (news_id) ON DELETE CASCADE)"
)

_CREATE_INDEX_SQL = (
    "CREATE INDEX ix_incident_log_news_news_id ON incident_log_news (news_id)"
)


def upgrade() -> None:
    bind = op.get_bind()

    rows = bind.execute(
        sa.text(
            "SELECT incident_id, log_datetime, summary FROM incident_logs "
            "ORDER BY incident_id, log_datetime"
        )
    ).fetchall()

    grouped: dict[tuple[int, str], list[str]] = defaultdict(list)
    for incident_id, log_datetime, summary in rows:
        log_date = str(log_datetime)[:10]
        grouped[(int(incident_id), log_date)].append(str(summary))

    bind.execute(sa.text(_CREATE_LOGS_NEW_SQL))
    for (incident_id, log_date), summaries in grouped.items():
        merged = "\n\n".join(summaries)
        bind.execute(
            sa.text(
                "INSERT INTO incident_logs_new (incident_id, log_date, summary) "
                "VALUES (:iid, :ld, :s)"
            ),
            {"iid": incident_id, "ld": log_date, "s": merged},
        )

    news_rows = bind.execute(
        sa.text(
            "SELECT incident_id, log_datetime, news_id FROM incident_log_news"
        )
    ).fetchall()

    bind.execute(sa.text("DROP TABLE incident_log_news"))
    bind.execute(sa.text("DROP TABLE incident_logs"))
    bind.execute(sa.text("ALTER TABLE incident_logs_new RENAME TO incident_logs"))
    bind.execute(sa.text(_CREATE_LOG_NEWS_SQL))
    bind.execute(sa.text(_CREATE_INDEX_SQL))

    for incident_id, log_datetime, news_id in news_rows:
        log_date = str(log_datetime)[:10]
        bind.execute(
            sa.text(
                "INSERT OR IGNORE INTO incident_log_news "
                "(incident_id, log_date, news_id) VALUES (:iid, :ld, :nid)"
            ),
            {"iid": int(incident_id), "ld": log_date, "nid": int(news_id)},
        )


def downgrade() -> None:
    pass
