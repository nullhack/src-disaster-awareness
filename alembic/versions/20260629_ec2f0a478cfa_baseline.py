from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "ec2f0a478cfa"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_V_INCIDENT = """
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

_V_USGS = """
    CREATE VIEW v_usgs_earthquake AS
    SELECT
        u.usgs_key, u.incident_key, fi.incident_id,
        dc.name AS country_name, dc.iso2 AS country_iso2,
        it.type_name AS incident_type,
        so.name AS source_name,
        d.full_date AS time_date,
        u.usgs_id, u.magnitude, u.depth, u.place, u.felt, u.tsunami, u.sig
    FROM fact_usgs_earthquake u
    JOIN fact_incident fi ON u.incident_key = fi.incident_key
    JOIN dim_country dc ON u.country_key = dc.country_key
    JOIN dim_incident_type it ON u.type_key = it.type_key
    JOIN dim_source so ON u.source_key = so.source_key
    JOIN dim_date d ON u.time_key = d.date_key
"""

_V_GDACS = """
    CREATE VIEW v_gdacs_event AS
    SELECT
        g.gdacs_key, g.incident_key, fi.incident_id,
        dc.name AS country_name, dc.iso2 AS country_iso2,
        it.type_name AS incident_type,
        so.name AS source_name,
        d.full_date AS from_date,
        g.gdacs_eventid, g.episodeid, g.alertlevel, g.alertscore,
        g.severity, g.population
    FROM fact_gdacs_event g
    JOIN fact_incident fi ON g.incident_key = fi.incident_key
    JOIN dim_country dc ON g.country_key = dc.country_key
    JOIN dim_incident_type it ON g.type_key = it.type_key
    JOIN dim_source so ON g.source_key = so.source_key
    JOIN dim_date d ON g.fromdate_key = d.date_key
"""

_V_WHO = """
    CREATE VIEW v_who_don AS
    SELECT
        w.who_key, w.incident_key, fi.incident_id,
        dc.name AS country_name, dc.iso2 AS country_iso2,
        so.name AS source_name,
        d.full_date AS publication_date,
        w.don_id, w.title, w.provider,
        w.epidemiology, w.advice, w.assessment, w.overview,
        dz.disease_name
    FROM fact_who_don w
    JOIN fact_incident fi ON w.incident_key = fi.incident_key
    JOIN dim_country dc ON w.country_key = dc.country_key
    JOIN dim_source so ON w.source_key = so.source_key
    JOIN dim_date d ON w.publication_date_key = d.date_key
    LEFT JOIN dim_disease dz ON w.disease_key = dz.disease_key
"""

_V_HEALTHMAP = """
    CREATE VIEW v_healthmap_alert AS
    SELECT
        h.healthmap_key, h.incident_key, fi.incident_id,
        dc.name AS country_name, dc.iso2 AS country_iso2,
        so.name AS source_name,
        d.full_date AS alert_date,
        h.alert_id, h.species, h.cases, h.deaths,
        h.significance, h.feed_source,
        dz.disease_name
    FROM fact_healthmap_alert h
    JOIN fact_incident fi ON h.incident_key = fi.incident_key
    JOIN dim_country dc ON h.country_key = dc.country_key
    JOIN dim_source so ON h.source_key = so.source_key
    JOIN dim_date d ON h.alert_date_key = d.date_key
    LEFT JOIN dim_disease dz ON h.disease_key = dz.disease_key
"""

_V_NEWS = """
    CREATE VIEW v_news_article AS
    SELECT
        n.news_key, n.incident_key, fi.incident_id,
        so.name AS source_name,
        d.full_date AS published_date,
        n.url, n.headline, n.body, n.outlet, n.image,
        dc.name AS country_name
    FROM fact_news_article n
    LEFT JOIN fact_incident fi ON n.incident_key = fi.incident_key
    JOIN dim_source so ON n.source_key = so.source_key
    JOIN dim_date d ON n.published_date_key = d.date_key
    LEFT JOIN dim_country dc ON n.country_key = dc.country_key
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
    op.create_table(
        "dim_country",
        sa.Column("country_key", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("iso2", sa.String(length=2), nullable=False),
        sa.Column("country_group", sa.String(length=1), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("country_key", name=op.f("pk_dim_country")),
    )
    op.create_table(
        "dim_date",
        sa.Column("date_key", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("full_date", sa.Date(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("is_weekend", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("date_key", name=op.f("pk_dim_date")),
    )
    op.create_table(
        "dim_disease",
        sa.Column("disease_key", sa.Integer(), nullable=False),
        sa.Column("disease_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("disease_key", name=op.f("pk_dim_disease")),
    )
    op.create_table(
        "dim_incident_type",
        sa.Column("type_key", sa.Integer(), nullable=False),
        sa.Column("type_name", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("type_key", name=op.f("pk_dim_incident_type")),
    )
    op.create_table(
        "dim_priority",
        sa.Column("priority_key", sa.Integer(), nullable=False),
        sa.Column("priority_name", sa.String(length=10), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("priority_key", name=op.f("pk_dim_priority")),
    )
    op.create_table(
        "dim_severity_level",
        sa.Column("level_key", sa.Integer(), nullable=False),
        sa.Column("severity_name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("level_key", name=op.f("pk_dim_severity_level")),
    )
    op.create_table(
        "dim_source",
        sa.Column("source_key", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("reliability_tier", sa.String(length=20), nullable=False),
        sa.Column("data_freshness", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("source_key", name=op.f("pk_dim_source")),
    )
    op.create_table(
        "fact_incident",
        sa.Column("incident_key", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.String(length=32), nullable=False),
        sa.Column("canonical_name", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("first_reported_date_key", sa.Integer(), nullable=False),
        sa.Column("last_updated_date_key", sa.Integer(), nullable=False),
        sa.Column("event_date_key", sa.Integer(), nullable=False),
        sa.Column("country_key", sa.Integer(), nullable=False),
        sa.Column("type_key", sa.Integer(), nullable=False),
        sa.Column("priority_key", sa.Integer(), nullable=False),
        sa.Column("level_key", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("disease_key", sa.Integer(), nullable=True),
        sa.Column("should_report", sa.Boolean(), nullable=False),
        sa.Column("search_keys", sa.JSON(), nullable=False),
        sa.Column("ai_digest_date_key", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ai_digest_date_key"], ["dim_date.date_key"],
            name=op.f("fk_fact_incident_ai_digest_date_key_dim_date"),
        ),
        sa.ForeignKeyConstraint(
            ["country_key"], ["dim_country.country_key"],
            name=op.f("fk_fact_incident_country_key_dim_country"),
        ),
        sa.ForeignKeyConstraint(
            ["disease_key"], ["dim_disease.disease_key"],
            name=op.f("fk_fact_incident_disease_key_dim_disease"),
        ),
        sa.ForeignKeyConstraint(
            ["event_date_key"], ["dim_date.date_key"],
            name=op.f("fk_fact_incident_event_date_key_dim_date"),
        ),
        sa.ForeignKeyConstraint(
            ["first_reported_date_key"], ["dim_date.date_key"],
            name=op.f("fk_fact_incident_first_reported_date_key_dim_date"),
        ),
        sa.ForeignKeyConstraint(
            ["last_updated_date_key"], ["dim_date.date_key"],
            name=op.f("fk_fact_incident_last_updated_date_key_dim_date"),
        ),
        sa.ForeignKeyConstraint(
            ["level_key"], ["dim_severity_level.level_key"],
            name=op.f("fk_fact_incident_level_key_dim_severity_level"),
        ),
        sa.ForeignKeyConstraint(
            ["priority_key"], ["dim_priority.priority_key"],
            name=op.f("fk_fact_incident_priority_key_dim_priority"),
        ),
        sa.ForeignKeyConstraint(
            ["type_key"], ["dim_incident_type.type_key"],
            name=op.f("fk_fact_incident_type_key_dim_incident_type"),
        ),
        sa.PrimaryKeyConstraint("incident_key", name=op.f("pk_fact_incident")),
        sa.UniqueConstraint("incident_id", name=op.f("uq_fact_incident_incident_id")),
    )
    op.create_table(
        "fact_gdacs_event",
        sa.Column("gdacs_key", sa.Integer(), nullable=False),
        sa.Column("incident_key", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.Integer(), nullable=False),
        sa.Column("country_key", sa.Integer(), nullable=False),
        sa.Column("type_key", sa.Integer(), nullable=False),
        sa.Column("fromdate_key", sa.Integer(), nullable=False),
        sa.Column("gdacs_eventid", sa.String(length=64), nullable=False),
        sa.Column("episodeid", sa.String(length=64), nullable=False),
        sa.Column("alertlevel", sa.String(length=10), nullable=False),
        sa.Column("alertscore", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("population", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["country_key"], ["dim_country.country_key"],
            name=op.f("fk_fact_gdacs_event_country_key_dim_country"),
        ),
        sa.ForeignKeyConstraint(
            ["fromdate_key"], ["dim_date.date_key"],
            name=op.f("fk_fact_gdacs_event_fromdate_key_dim_date"),
        ),
        sa.ForeignKeyConstraint(
            ["incident_key"], ["fact_incident.incident_key"],
            name=op.f("fk_fact_gdacs_event_incident_key_fact_incident"),
        ),
        sa.ForeignKeyConstraint(
            ["source_key"], ["dim_source.source_key"],
            name=op.f("fk_fact_gdacs_event_source_key_dim_source"),
        ),
        sa.ForeignKeyConstraint(
            ["type_key"], ["dim_incident_type.type_key"],
            name=op.f("fk_fact_gdacs_event_type_key_dim_incident_type"),
        ),
        sa.PrimaryKeyConstraint("gdacs_key", name=op.f("pk_fact_gdacs_event")),
        sa.UniqueConstraint("gdacs_eventid", name=op.f("uq_fact_gdacs_event_gdacs_eventid")),
    )
    op.create_table(
        "fact_healthmap_alert",
        sa.Column("healthmap_key", sa.Integer(), nullable=False),
        sa.Column("incident_key", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.Integer(), nullable=False),
        sa.Column("country_key", sa.Integer(), nullable=False),
        sa.Column("alert_date_key", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.String(length=32), nullable=False),
        sa.Column("species", sa.String(length=100), nullable=False),
        sa.Column("cases", sa.Integer(), nullable=False),
        sa.Column("deaths", sa.Integer(), nullable=False),
        sa.Column("significance", sa.String(length=20), nullable=False),
        sa.Column("feed_source", sa.String(length=100), nullable=False),
        sa.Column("disease_key", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["alert_date_key"], ["dim_date.date_key"],
            name=op.f("fk_fact_healthmap_alert_alert_date_key_dim_date"),
        ),
        sa.ForeignKeyConstraint(
            ["country_key"], ["dim_country.country_key"],
            name=op.f("fk_fact_healthmap_alert_country_key_dim_country"),
        ),
        sa.ForeignKeyConstraint(
            ["disease_key"], ["dim_disease.disease_key"],
            name=op.f("fk_fact_healthmap_alert_disease_key_dim_disease"),
        ),
        sa.ForeignKeyConstraint(
            ["incident_key"], ["fact_incident.incident_key"],
            name=op.f("fk_fact_healthmap_alert_incident_key_fact_incident"),
        ),
        sa.ForeignKeyConstraint(
            ["source_key"], ["dim_source.source_key"],
            name=op.f("fk_fact_healthmap_alert_source_key_dim_source"),
        ),
        sa.PrimaryKeyConstraint("healthmap_key", name=op.f("pk_fact_healthmap_alert")),
        sa.UniqueConstraint("alert_id", name=op.f("uq_fact_healthmap_alert_alert_id")),
    )
    op.create_table(
        "fact_news_article",
        sa.Column("news_key", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.Integer(), nullable=False),
        sa.Column("published_date_key", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("headline", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("outlet", sa.String(length=200), nullable=False),
        sa.Column("image", sa.String(length=500), nullable=True),
        sa.Column("incident_key", sa.Integer(), nullable=True),
        sa.Column("country_key", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["country_key"], ["dim_country.country_key"],
            name=op.f("fk_fact_news_article_country_key_dim_country"),
        ),
        sa.ForeignKeyConstraint(
            ["incident_key"], ["fact_incident.incident_key"],
            name=op.f("fk_fact_news_article_incident_key_fact_incident"),
        ),
        sa.ForeignKeyConstraint(
            ["published_date_key"], ["dim_date.date_key"],
            name=op.f("fk_fact_news_article_published_date_key_dim_date"),
        ),
        sa.ForeignKeyConstraint(
            ["source_key"], ["dim_source.source_key"],
            name=op.f("fk_fact_news_article_source_key_dim_source"),
        ),
        sa.PrimaryKeyConstraint("news_key", name=op.f("pk_fact_news_article")),
        sa.UniqueConstraint("url", name=op.f("uq_fact_news_article_url")),
    )
    op.create_table(
        "fact_usgs_earthquake",
        sa.Column("usgs_key", sa.Integer(), nullable=False),
        sa.Column("incident_key", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.Integer(), nullable=False),
        sa.Column("country_key", sa.Integer(), nullable=False),
        sa.Column("type_key", sa.Integer(), nullable=False),
        sa.Column("time_key", sa.Integer(), nullable=False),
        sa.Column("usgs_id", sa.String(length=32), nullable=False),
        sa.Column("magnitude", sa.Float(), nullable=False),
        sa.Column("depth", sa.Float(), nullable=False),
        sa.Column("place", sa.String(length=200), nullable=False),
        sa.Column("felt", sa.Integer(), nullable=False),
        sa.Column("tsunami", sa.Boolean(), nullable=False),
        sa.Column("sig", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["country_key"], ["dim_country.country_key"],
            name=op.f("fk_fact_usgs_earthquake_country_key_dim_country"),
        ),
        sa.ForeignKeyConstraint(
            ["incident_key"], ["fact_incident.incident_key"],
            name=op.f("fk_fact_usgs_earthquake_incident_key_fact_incident"),
        ),
        sa.ForeignKeyConstraint(
            ["source_key"], ["dim_source.source_key"],
            name=op.f("fk_fact_usgs_earthquake_source_key_dim_source"),
        ),
        sa.ForeignKeyConstraint(
            ["time_key"], ["dim_date.date_key"],
            name=op.f("fk_fact_usgs_earthquake_time_key_dim_date"),
        ),
        sa.ForeignKeyConstraint(
            ["type_key"], ["dim_incident_type.type_key"],
            name=op.f("fk_fact_usgs_earthquake_type_key_dim_incident_type"),
        ),
        sa.PrimaryKeyConstraint("usgs_key", name=op.f("pk_fact_usgs_earthquake")),
        sa.UniqueConstraint("usgs_id", name=op.f("uq_fact_usgs_earthquake_usgs_id")),
    )
    op.create_table(
        "fact_who_don",
        sa.Column("who_key", sa.Integer(), nullable=False),
        sa.Column("incident_key", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.Integer(), nullable=False),
        sa.Column("country_key", sa.Integer(), nullable=False),
        sa.Column("publication_date_key", sa.Integer(), nullable=False),
        sa.Column("don_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("epidemiology", sa.Text(), nullable=False),
        sa.Column("advice", sa.Text(), nullable=False),
        sa.Column("assessment", sa.Text(), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("disease_key", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["country_key"], ["dim_country.country_key"],
            name=op.f("fk_fact_who_don_country_key_dim_country"),
        ),
        sa.ForeignKeyConstraint(
            ["disease_key"], ["dim_disease.disease_key"],
            name=op.f("fk_fact_who_don_disease_key_dim_disease"),
        ),
        sa.ForeignKeyConstraint(
            ["incident_key"], ["fact_incident.incident_key"],
            name=op.f("fk_fact_who_don_incident_key_fact_incident"),
        ),
        sa.ForeignKeyConstraint(
            ["publication_date_key"], ["dim_date.date_key"],
            name=op.f("fk_fact_who_don_publication_date_key_dim_date"),
        ),
        sa.ForeignKeyConstraint(
            ["source_key"], ["dim_source.source_key"],
            name=op.f("fk_fact_who_don_source_key_dim_source"),
        ),
        sa.PrimaryKeyConstraint("who_key", name=op.f("pk_fact_who_don")),
        sa.UniqueConstraint("don_id", name=op.f("uq_fact_who_don_don_id")),
    )
    for _name, _ddl in _VIEWS:
        op.execute(_ddl)


def downgrade() -> None:
    for _name, _ddl in _VIEWS:
        op.execute(f"DROP VIEW IF EXISTS {_name}")
    op.drop_table("fact_who_don")
    op.drop_table("fact_usgs_earthquake")
    op.drop_table("fact_news_article")
    op.drop_table("fact_healthmap_alert")
    op.drop_table("fact_gdacs_event")
    op.drop_table("fact_incident")
    op.drop_table("dim_source")
    op.drop_table("dim_severity_level")
    op.drop_table("dim_priority")
    op.drop_table("dim_incident_type")
    op.drop_table("dim_disease")
    op.drop_table("dim_date")
    op.drop_table("dim_country")
