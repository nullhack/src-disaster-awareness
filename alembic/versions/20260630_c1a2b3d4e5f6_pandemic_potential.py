from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'bdc77a90477b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Recreate v_incident to also expose the AI pandemic_potential label and the
# raw event_status text column from fact_incident.
_V_INCIDENT = """
    CREATE VIEW v_incident AS
    SELECT
        fi.incident_key, fi.incident_id, fi.canonical_name, fi.summary,
        dc.name AS country_name, dc.iso2 AS country_iso2,
        dc.country_group, dc.region,
        it.type_name AS incident_type, it.category AS incident_category,
        pr.priority_name AS priority, pr.rank AS priority_rank,
        sv.severity_name AS severity, sv.description AS severity_description,
        pp.potential_name AS pandemic_potential,
        fi.event_status,
        dz.disease_name,
        d1.full_date AS first_reported_date,
        d2.full_date AS last_updated_date,
        d3.full_date AS event_date,
        d4.full_date AS ai_digest_date,
        CAST(julianday(d2.full_date) - julianday(d3.full_date) AS INTEGER) AS days_since_event,
        fi.source_count, fi.should_report, fi.search_keys
    FROM fact_incident fi
    JOIN dim_country dc ON fi.country_key = dc.country_key
    JOIN dim_incident_type it ON fi.type_key = it.type_key
    JOIN dim_priority pr ON fi.priority_key = pr.priority_key
    JOIN dim_severity_level sv ON fi.level_key = sv.level_key
    LEFT JOIN dim_pandemic_potential pp ON fi.pandemic_potential_key = pp.potential_key
    LEFT JOIN dim_disease dz ON fi.disease_key = dz.disease_key
    JOIN dim_date d1 ON fi.first_reported_date_key = d1.date_key
    JOIN dim_date d2 ON fi.last_updated_date_key = d2.date_key
    JOIN dim_date d3 ON fi.event_date_key = d3.date_key
    LEFT JOIN dim_date d4 ON fi.ai_digest_date_key = d4.date_key
"""

_V_INCIDENT_OLD = """
    CREATE VIEW v_incident AS
    SELECT
        fi.incident_key, fi.incident_id, fi.canonical_name, fi.summary,
        dc.name AS country_name, dc.iso2 AS country_iso2,
        dc.country_group, dc.region,
        it.type_name AS incident_type, it.category AS incident_category,
        pr.priority_name AS priority, pr.rank AS priority_rank,
        sv.severity_name AS severity, sv.description AS severity_description,
        dz.disease_name,
        d1.full_date AS first_reported_date,
        d2.full_date AS last_updated_date,
        d3.full_date AS event_date,
        d4.full_date AS ai_digest_date,
        CAST(julianday(d2.full_date) - julianday(d3.full_date) AS INTEGER) AS days_since_event,
        fi.source_count, fi.should_report, fi.search_keys
    FROM fact_incident fi
    JOIN dim_country dc ON fi.country_key = dc.country_key
    JOIN dim_incident_type it ON fi.type_key = it.type_key
    JOIN dim_priority pr ON fi.priority_key = pr.priority_key
    JOIN dim_severity_level sv ON fi.level_key = sv.level_key
    LEFT JOIN dim_disease dz ON fi.disease_key = dz.disease_key
    JOIN dim_date d1 ON fi.first_reported_date_key = d1.date_key
    JOIN dim_date d2 ON fi.last_updated_date_key = d2.date_key
    JOIN dim_date d3 ON fi.event_date_key = d3.date_key
    LEFT JOIN dim_date d4 ON fi.ai_digest_date_key = d4.date_key
"""


def upgrade() -> None:
    op.create_table(
        'dim_pandemic_potential',
        sa.Column('potential_key', sa.Integer(), nullable=False),
        sa.Column('potential_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint('potential_key', name=op.f('pk_dim_pandemic_potential')),
    )
    op.bulk_insert(
        sa.table(
            'dim_pandemic_potential',
            sa.column('potential_key', sa.Integer),
            sa.column('potential_name', sa.String),
            sa.column('description', sa.String),
        ),
        [
            {'potential_key': 0, 'potential_name': 'NONE', 'description': 'No pandemic potential'},
            {'potential_key': 1, 'potential_name': 'LOW', 'description': 'Limited pandemic potential'},
            {'potential_key': 2, 'potential_name': 'MEDIUM', 'description': 'Moderate pandemic potential'},
            {'potential_key': 3, 'potential_name': 'HIGH', 'description': 'High pandemic potential'},
            {'potential_key': 4, 'potential_name': 'CRITICAL', 'description': 'Severe pandemic potential'},
        ],
    )

    # op.add_column emits SQLite's native ALTER TABLE ADD COLUMN (no table
    # rebuild), so the views that reference fact_incident stay valid. The
    # foreign-key constraint is modeled in the ORM (ForeignKey); SQLite does
    # not enforce FKs in this engine.
    op.add_column(
        'fact_incident',
        sa.Column('pandemic_potential_key', sa.Integer(), nullable=True),
    )
    op.add_column(
        'fact_incident',
        sa.Column('event_status', sa.Text(), nullable=True),
    )

    op.execute("DROP VIEW IF EXISTS v_incident")
    op.execute(_V_INCIDENT)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_incident")
    op.execute(_V_INCIDENT_OLD)
    op.drop_column('fact_incident', 'event_status')
    op.drop_column('fact_incident', 'pandemic_potential_key')
    op.drop_table('dim_pandemic_potential')
