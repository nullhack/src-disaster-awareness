"""drop relevance_score from report_news_links

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
Create Date: 2026-07-08 18:00:00.000000

Drops the ``relevance_score`` column from ``report_news_links``.
The field was always 1.0 in production (only kept news is stored) and
no read path used it for any decision.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c5d6e7f8a9b0"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("report_news_links") as batch_op:
        batch_op.drop_column("relevance_score")


def downgrade() -> None:
    with op.batch_alter_table("report_news_links") as batch_op:
        batch_op.add_column(
            sa.Column(
                "relevance_score", sa.Float(), nullable=False, server_default="1.0"
            )
        )
