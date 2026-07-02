"""Ubiquitous-language column renames.

Renames dimension columns to the canonical terms codified in GLOSSARY.md and
unifies the per-source artifact-date foreign keys to ``source_date_key``. The
six read-side views are redefined to reference the new column names; their
output aliases are preserved (``country_name``/``incident_type``/``source_name``
/``severity``/``priority``/``pandemic_potential`` already matched the UL, and
the per-source date aliases ``publication_date``/``published_date``/
``alert_date`` are retained as source-specific display labels).

Uses SQLite's native ``ALTER TABLE ... RENAME COLUMN`` (3.25+); data preserved.

Revision ID: a1b2c3d4e5f7
Revises: c1a2b3d4e5f6
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, old_column, new_column) — order-independent under RENAME COLUMN
# because each rename is scoped to its own table.
_RENAMES: list[tuple[str, str, str]] = [
    ("dim_incident_type", "type_key", "incident_type_key"),
    ("dim_incident_type", "type_name", "incident_type"),
    ("dim_severity_level", "level_key", "severity_key"),
    ("dim_severity_level", "severity_name", "severity"),
    ("dim_pandemic_potential", "potential_key", "pandemic_potential_key"),
    ("dim_pandemic_potential", "potential_name", "pandemic_potential"),
    ("dim_priority", "priority_name", "priority"),
    ("dim_country", "name", "country_name"),
    ("dim_source", "name", "source_name"),
    ("fact_incident", "type_key", "incident_type_key"),
    ("fact_incident", "level_key", "severity_key"),
    ("fact_usgs_earthquake", "type_key", "incident_type_key"),
    ("fact_gdacs_event", "type_key", "incident_type_key"),
    ("fact_who_don", "publication_date_key", "source_date_key"),
    ("fact_news_article", "published_date_key", "source_date_key"),
    ("fact_healthmap_alert", "alert_date_key", "source_date_key"),
]

# --- Views with column refs updated to the new names -------------------------
_V_INCIDENT = """
    CREATE VIEW v_incident AS
    SELECT
        fi.incident_key, fi.incident_id, fi.canonical_name, fi.summary,
        dc.country_name AS country_name, dc.iso2 AS country_iso2,
        dc.country_group, dc.region,
        it.incident_type AS incident_type, it.category AS incident_category,
        pr.priority AS priority, pr.rank AS priority_rank,
        sv.severity AS severity, sv.description AS severity_description,
        pp.pandemic_potential AS pandemic_potential,
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
    JOIN dim_incident_type it ON fi.incident_type_key = it.incident_type_key
    JOIN dim_priority pr ON fi.priority_key = pr.priority_key
    JOIN dim_severity_level sv ON fi.severity_key = sv.severity_key
    LEFT JOIN dim_pandemic_potential pp ON fi.pandemic_potential_key = pp.pandemic_potential_key
    LEFT JOIN dim_disease dz ON fi.disease_key = dz.disease_key
    JOIN dim_date d1 ON fi.first_reported_date_key = d1.date_key
    JOIN dim_date d2 ON fi.last_updated_date_key = d2.date_key
    JOIN dim_date d3 ON fi.event_date_key = d3.date_key
    LEFT JOIN dim_date d4 ON fi.ai_digest_date_key = d4.date_key
"""

_V_USGS = """
    CREATE VIEW v_usgs_earthquake AS
    SELECT
        u.usgs_key, u.incident_key, fi.incident_id,
        dc.country_name AS country_name, dc.iso2 AS country_iso2,
        it.incident_type AS incident_type,
        so.source_name AS source_name,
        d.full_date AS time_date,
        u.usgs_id, u.magnitude, u.depth, u.place, u.felt, u.tsunami, u.sig
    FROM fact_usgs_earthquake u
    JOIN fact_incident fi ON u.incident_key = fi.incident_key
    JOIN dim_country dc ON u.country_key = dc.country_key
    JOIN dim_incident_type it ON u.incident_type_key = it.incident_type_key
    JOIN dim_source so ON u.source_key = so.source_key
    JOIN dim_date d ON u.time_key = d.date_key
"""

_V_GDACS = """
    CREATE VIEW v_gdacs_event AS
    SELECT
        g.gdacs_key, g.incident_key, fi.incident_id,
        dc.country_name AS country_name, dc.iso2 AS country_iso2,
        it.incident_type AS incident_type,
        so.source_name AS source_name,
        d.full_date AS from_date,
        g.gdacs_eventid, g.episodeid, g.alertlevel, g.alertscore,
        g.severity, g.population
    FROM fact_gdacs_event g
    JOIN fact_incident fi ON g.incident_key = fi.incident_key
    JOIN dim_country dc ON g.country_key = dc.country_key
    JOIN dim_incident_type it ON g.incident_type_key = it.incident_type_key
    JOIN dim_source so ON g.source_key = so.source_key
    JOIN dim_date d ON g.fromdate_key = d.date_key
"""

_V_WHO = """
    CREATE VIEW v_who_don AS
    SELECT
        w.who_key, w.incident_key, fi.incident_id,
        dc.country_name AS country_name, dc.iso2 AS country_iso2,
        so.source_name AS source_name,
        d.full_date AS publication_date,
        w.don_id, w.title, w.provider,
        dz.disease_name
    FROM fact_who_don w
    JOIN fact_incident fi ON w.incident_key = fi.incident_key
    JOIN dim_country dc ON w.country_key = dc.country_key
    JOIN dim_source so ON w.source_key = so.source_key
    JOIN dim_date d ON w.source_date_key = d.date_key
    LEFT JOIN dim_disease dz ON w.disease_key = dz.disease_key
"""

_V_HEALTHMAP = """
    CREATE VIEW v_healthmap_alert AS
    SELECT
        h.healthmap_key, h.incident_key, fi.incident_id,
        dc.country_name AS country_name, dc.iso2 AS country_iso2,
        so.source_name AS source_name,
        d.full_date AS alert_date,
        h.alert_id, h.feed_source,
        dz.disease_name
    FROM fact_healthmap_alert h
    JOIN fact_incident fi ON h.incident_key = fi.incident_key
    JOIN dim_country dc ON h.country_key = dc.country_key
    JOIN dim_source so ON h.source_key = so.source_key
    JOIN dim_date d ON h.source_date_key = d.date_key
    LEFT JOIN dim_disease dz ON h.disease_key = dz.disease_key
"""

_V_NEWS = """
    CREATE VIEW v_news_article AS
    SELECT
        n.news_key, n.incident_key, fi.incident_id,
        so.source_name AS source_name,
        d.full_date AS published_date,
        n.url, n.headline, n.body, n.outlet, n.image
    FROM fact_news_article n
    LEFT JOIN fact_incident fi ON n.incident_key = fi.incident_key
    JOIN dim_source so ON n.source_key = so.source_key
    JOIN dim_date d ON n.source_date_key = d.date_key
"""

_VIEWS = [
    ("v_incident", _V_INCIDENT),
    ("v_usgs_earthquake", _V_USGS),
    ("v_gdacs_event", _V_GDACS),
    ("v_who_don", _V_WHO),
    ("v_healthmap_alert", _V_HEALTHMAP),
    ("v_news_article", _V_NEWS),
]


def upgrade() -> None:
    # Rename columns first; views are dropped because they reference the old
    # column names and would otherwise become invalid after the renames.
    for name, _ in _VIEWS:
        op.execute(f"DROP VIEW IF EXISTS {name}")
    for table, old, new in _RENAMES:
        op.execute(f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}")
    for _, ddl in _VIEWS:
        op.execute(ddl)


def downgrade() -> None:
    # Reverse: restore old view DDL (old column refs), then rename back.
    op.execute("DROP VIEW IF EXISTS v_incident")
    op.execute("""CREATE VIEW v_incident AS
    SELECT
        fi.incident_key, fi.incident_id, fi.canonical_name, fi.summary,
        dc.country_name AS country_name, dc.iso2 AS country_iso2,
        dc.country_group, dc.region,
        it.incident_type AS incident_type, it.category AS incident_category,
        pr.priority_name AS priority, pr.rank AS priority_rank,
        sv.severity_name AS severity, sv.description AS severity_description,
        pp.pandemic_potential AS pandemic_potential,
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
    """)
    for table, old, new in _RENAMES:
        op.execute(f"ALTER TABLE {table} RENAME COLUMN {new} TO {old}")
