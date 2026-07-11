"""add incident_log_news junction table

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-11 12:00:00.000000

Adds the ``incident_log_news`` junction table linking each
``incident_logs`` row to the ``news_items`` that fed it, giving every log
row auditable provenance and providing the anti-join source for P3 delta
summarization. Composite PK ``(incident_id, log_datetime, news_id)``
makes junction writes idempotent under ``INSERT OR IGNORE``; FKs to
``incident_logs`` and ``news_items`` cascade on delete; an index on
``news_id`` serves the reverse-provenance audit query.

A one-time backfill links every existing log row to the news assigned to
its incident whose ``published_date`` predates the log's
``log_datetime`` (the honest approximation — the exact subset the
digester saw is unknown). ``INSERT OR IGNORE`` makes the backfill
idempotent under re-run.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CREATE_TABLE_SQL = (
    "CREATE TABLE incident_log_news ("
    "incident_id INTEGER NOT NULL, "
    "log_datetime VARCHAR NOT NULL, "
    "news_id INTEGER NOT NULL, "
    "PRIMARY KEY (incident_id, log_datetime, news_id), "
    "FOREIGN KEY (incident_id, log_datetime) "
    "REFERENCES incident_logs (incident_id, log_datetime) ON DELETE CASCADE, "
    "FOREIGN KEY (news_id) REFERENCES news_items (news_id) ON DELETE CASCADE)"
)

_CREATE_INDEX_SQL = (
    "CREATE INDEX ix_incident_log_news_news_id ON incident_log_news (news_id)"
)

_BACKFILL_SQL = (
    "INSERT OR IGNORE INTO incident_log_news "
    "(incident_id, log_datetime, news_id) "
    "SELECT il.incident_id, il.log_datetime, ni.news_id "
    "FROM incident_logs il "
    "JOIN news_incidents ni ON ni.incident_id = il.incident_id "
    "JOIN news_items n ON n.news_id = ni.news_id "
    "WHERE n.published_date <= il.log_datetime"
)


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(_CREATE_TABLE_SQL))
    bind.execute(sa.text(_CREATE_INDEX_SQL))
    bind.execute(sa.text(_BACKFILL_SQL))


def downgrade() -> None:
    pass
