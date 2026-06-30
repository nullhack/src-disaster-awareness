from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = 'bdc77a90477b'
down_revision: Union[str, Sequence[str], None] = 'ec2f0a478cfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_V_WHO = """
    CREATE VIEW v_who_don AS
    SELECT
        w.who_key, w.incident_key, fi.incident_id,
        dc.name AS country_name, dc.iso2 AS country_iso2,
        so.name AS source_name,
        d.full_date AS publication_date,
        w.don_id, w.title, w.provider,
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
        h.alert_id, h.feed_source,
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
        n.url, n.headline, n.body, n.outlet, n.image
    FROM fact_news_article n
    LEFT JOIN fact_incident fi ON n.incident_key = fi.incident_key
    JOIN dim_source so ON n.source_key = so.source_key
    JOIN dim_date d ON n.published_date_key = d.date_key
"""

_V_WHO_OLD = """
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

_V_HEALTHMAP_OLD = """
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

_V_NEWS_OLD = """
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


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_who_don")
    op.execute("DROP VIEW IF EXISTS v_healthmap_alert")
    op.execute("DROP VIEW IF EXISTS v_news_article")

    with op.batch_alter_table('fact_healthmap_alert', schema=None) as batch_op:
        batch_op.drop_column('cases')
        batch_op.drop_column('species')
        batch_op.drop_column('significance')
        batch_op.drop_column('deaths')

    with op.batch_alter_table('fact_news_article', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_fact_news_article_country_key_dim_country'), type_='foreignkey')
        batch_op.drop_column('country_key')

    with op.batch_alter_table('fact_who_don', schema=None) as batch_op:
        batch_op.drop_column('overview')
        batch_op.drop_column('advice')
        batch_op.drop_column('epidemiology')
        batch_op.drop_column('assessment')

    op.execute(_V_WHO)
    op.execute(_V_HEALTHMAP)
    op.execute(_V_NEWS)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_who_don")
    op.execute("DROP VIEW IF EXISTS v_healthmap_alert")
    op.execute("DROP VIEW IF EXISTS v_news_article")

    with op.batch_alter_table('fact_who_don', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assessment', sa.TEXT(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('epidemiology', sa.TEXT(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('advice', sa.TEXT(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('overview', sa.TEXT(), nullable=False, server_default=''))

    with op.batch_alter_table('fact_news_article', schema=None) as batch_op:
        batch_op.add_column(sa.Column('country_key', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_fact_news_article_country_key_dim_country'), 'dim_country', ['country_key'], ['country_key'])

    with op.batch_alter_table('fact_healthmap_alert', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deaths', sa.INTEGER(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('significance', sa.VARCHAR(length=20), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('species', sa.VARCHAR(length=100), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('cases', sa.INTEGER(), nullable=False, server_default='0'))

    op.execute(_V_WHO_OLD)
    op.execute(_V_HEALTHMAP_OLD)
    op.execute(_V_NEWS_OLD)
