"""add incidents table

Revision ID: a1b2c3d4e5f6
Revises: 149200aba244
Create Date: 2026-07-08 02:30:00.000000

Adds the ``incidents`` table that stores the derived incident identity
metadata (category, type, name, first-seen timestamp, genesis report id)
alongside the existing four operational tables. The category is derived
from the source at incident birth (WHO -> disease, USGS/GDACS ->
geophysical) and is not stored on ``source_reports``.

The upgrade also rewrites WHO ``source_reports.incident_type`` rows that
were previously stored as the literal ``"Disease"`` to the specific
disease name extracted from the title, and backfills the new
``incidents`` table from ``incident_logs`` joined to ``source_reports``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

from disaster_report._search_keys import disease_from_title

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "149200aba244"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.String(), nullable=False),
        sa.Column("incident_category", sa.String(), nullable=False),
        sa.Column("incident_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("first_seen_at", sa.String(), nullable=False),
        sa.Column("genesis_report_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("incident_id"),
    )

    bind = op.get_bind()
    _rewrite_who_incident_types(bind)
    _backfill_incidents(bind)


def downgrade() -> None:
    op.drop_table("incidents")


def _rewrite_who_incident_types(bind: sa.engine.Connection) -> None:
    rows = bind.execute(
        sa.text(
            "SELECT source, source_id, name, incident_type "
            "FROM source_reports WHERE source = 'WHO'"
        )
    ).fetchall()
    for row in rows:
        if row.incident_type != "Disease":
            continue
        new_type = disease_from_title(row.name) or "Disease"
        if new_type == row.incident_type:
            continue
        bind.execute(
            sa.text(
                "UPDATE source_reports SET incident_type = :type "
                "WHERE source = 'WHO' AND source_id = :sid"
            ),
            {"type": new_type, "sid": row.source_id},
        )


def _backfill_incidents(bind: sa.engine.Connection) -> None:
    log_rows = bind.execute(
        sa.text(
            "SELECT incident_id, MIN(iso_datetime) AS first_seen_at "
            "FROM incident_logs GROUP BY incident_id"
        )
    ).fetchall()
    for log_row in log_rows:
        incident_id = log_row.incident_id
        first_seen_at = log_row.first_seen_at
        source, _, source_id = incident_id.partition(":")
        report_row = bind.execute(
            sa.text(
                "SELECT incident_type, name FROM source_reports "
                "WHERE source = :src AND source_id = :sid"
            ),
            {"src": source, "sid": source_id},
        ).first()
        if report_row is None:
            incident_type = "Unknown"
            name = ""
        else:
            incident_type = report_row.incident_type
            name = report_row.name
        category = "disease" if source == "WHO" else "geophysical"
        bind.execute(
            sa.text(
                "INSERT OR REPLACE INTO incidents "
                "(incident_id, incident_category, incident_type, name, "
                "first_seen_at, genesis_report_id) "
                "VALUES (:id, :cat, :type, :name, :first, :genesis)"
            ),
            {
                "id": incident_id,
                "cat": category,
                "type": incident_type,
                "name": name,
                "first": first_seen_at,
                "genesis": incident_id,
            },
        )
