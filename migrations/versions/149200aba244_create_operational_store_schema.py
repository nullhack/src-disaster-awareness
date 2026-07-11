"""create operational store schema

Revision ID: 149200aba244
Revises:
Create Date: 2026-07-05 09:14:55.184322

The operational relational schema backing ``Warehouse``: four tables that
satisfy the 12-method ingest/read boundary. This is NOT a dimensional
(fact/dimension star) schema — the dimensional model is a traced deferral to
a separate ``data-architect`` consultation per the simulation journal.

Tables:
- ``source_reports``: ingested source reports; idempotent on
  (source, source_id).
- ``news_items``: deduplicated news items keyed by a generated ``news_id``
  with a unique ``url`` natural key.
- ``report_news_links``: edges linking a source report and a news item under
  an incident; idempotent on (source_report_id, news_item_id, incident_id)
  with a frozen relevance score.
- ``incident_logs``: timeline rows; idempotent on
  (iso_datetime, incident_id).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "149200aba244"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_reports",
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("incident_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("places", sa.JSON(), nullable=False),
        sa.Column("report_date", sa.String(), nullable=False),
        sa.Column("raw_fields", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("source", "source_id"),
    )
    op.create_table(
        "news_items",
        sa.Column("news_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("published_date", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("image", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("news_id"),
        sa.UniqueConstraint("url"),
    )
    op.create_table(
        "report_news_links",
        sa.Column("source_report_id", sa.String(), nullable=False),
        sa.Column("news_item_id", sa.String(), nullable=False),
        sa.Column("incident_id", sa.String(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("linked_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("source_report_id", "news_item_id", "incident_id"),
    )
    op.create_table(
        "incident_logs",
        sa.Column("iso_datetime", sa.String(), nullable=False),
        sa.Column("incident_id", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("iso_datetime", "incident_id"),
    )


def downgrade() -> None:
    op.drop_table("incident_logs")
    op.drop_table("report_news_links")
    op.drop_table("news_items")
    op.drop_table("source_reports")
