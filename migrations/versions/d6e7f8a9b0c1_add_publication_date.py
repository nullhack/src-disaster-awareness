"""add publication_date to report_news_links

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-09 12:00:00.000000

Adds ``publication_date`` to ``report_news_links`` — the news article's
publication date (sourced from ``news_items.published_date``).  This is
the signal ``active_incidents`` uses to determine whether an incident
is still active.  ``linked_at`` remains as the ingestion-time timestamp.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d6e7f8a9b0c1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("report_news_links") as batch_op:
        batch_op.add_column(sa.Column("publication_date", sa.String(), nullable=True))
    op.execute(
        "UPDATE report_news_links SET publication_date = "
        "(SELECT published_date FROM news_items "
        "WHERE news_items.news_id = report_news_links.news_item_id)"
    )
    with op.batch_alter_table("report_news_links") as batch_op:
        batch_op.alter_column("publication_date", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("report_news_links") as batch_op:
        batch_op.drop_column("publication_date")
