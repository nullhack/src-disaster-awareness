"""add incident_connections table

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-07-08 12:00:00.000000

Adds the ``incident_connections`` table recording bridge edges between
existing incidents. When a new source report's news touches two or more
existing incidents, the clusterer births a bridge incident and writes
one row per touched incident. Endpoints are normalized so
``incident_a < incident_b`` lexicographically.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "incident_connections",
        sa.Column("incident_a", sa.String(), nullable=False),
        sa.Column("incident_b", sa.String(), nullable=False),
        sa.Column("bridge_report_id", sa.String(), nullable=False),
        sa.Column("connected_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("incident_a", "incident_b", "bridge_report_id"),
    )


def downgrade() -> None:
    op.drop_table("incident_connections")
