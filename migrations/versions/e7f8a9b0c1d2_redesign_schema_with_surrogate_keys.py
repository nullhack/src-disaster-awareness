"""redesign schema with surrogate keys

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-07-09 18:00:00.000000

Redesigns the operational store to the 6-table + view schema: surrogate
integer keys (unix ms), split membership (``report_incidents``,
``news_incidents``), separated places (``report_places``), and a derived
``incidents`` VIEW replacing the materialized table. Drops ``cluster.py``
artifacts: ``report_news_links``, ``incident_connections``.

Backfill assigns deterministic integer IDs (base + row number) to every
entity from the legacy string-keyed tables, preserving all source reports,
news items, incident membership, and timeline logs. The ``places`` JSON
column is split into ``report_places`` rows. ``incident_logs.iso_datetime``
becomes ``log_datetime``; the PK shifts to ``(incident_id, log_datetime)``.

Bridge incidents (2 rows where a news item linked to 2+ incidents under
the old 0/1/2+ rule) collapse: each news item is assigned to one incident
(``MIN(incident_id)``), matching the new schema's 1:1 news→incident rule.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_BASE = 1700000000000
_REPORT_OFFSET = 1
_NEWS_OFFSET = 1000001
_INCIDENT_OFFSET = 2000001


def upgrade() -> None:
    bind = op.get_bind()

    _rename_legacy_tables(bind)
    _drop_auto_created_tables(bind)
    _create_new_tables(bind)

    report_map = _backfill_source_reports(bind)
    _backfill_report_places(bind, report_map)
    news_map = _backfill_news_items(bind)
    incident_map = _backfill_membership(bind, report_map, news_map)
    _backfill_incident_logs(bind, incident_map)

    _create_incidents_view(bind)
    _drop_legacy_tables(bind)


def downgrade() -> None:
    pass


_LEGACY_TABLES = [
    "source_reports",
    "news_items",
    "report_news_links",
    "incident_logs",
    "incidents",
    "incident_connections",
]

_AUTO_CREATED = ["report_places", "report_incidents", "news_incidents"]


def _rename_legacy_tables(bind: sa.engine.Connection) -> None:
    for table in _LEGACY_TABLES:
        bind.execute(sa.text(f"ALTER TABLE {table} RENAME TO _legacy_{table}"))


def _drop_auto_created_tables(bind: sa.engine.Connection) -> None:
    for table in _AUTO_CREATED:
        bind.execute(sa.text(f"DROP TABLE IF EXISTS {table}"))


def _create_new_tables(bind: sa.engine.Connection) -> None:
    bind.execute(
        sa.text(
            "CREATE TABLE source_reports ("
            "report_id INTEGER PRIMARY KEY, "
            "source VARCHAR NOT NULL, "
            "source_id VARCHAR NOT NULL, "
            "incident_type VARCHAR NOT NULL, "
            "name VARCHAR NOT NULL, "
            "report_date VARCHAR NOT NULL, "
            "raw_fields JSON NOT NULL, "
            "CONSTRAINT uq_source_reports_natural UNIQUE (source, source_id))"
        )
    )
    bind.execute(
        sa.text(
            "CREATE TABLE report_places ("
            "report_id INTEGER NOT NULL, "
            "country_code VARCHAR NOT NULL, "
            "subdivision VARCHAR NOT NULL, "
            "locality VARCHAR NOT NULL, "
            "PRIMARY KEY (report_id, country_code, subdivision, locality))"
        )
    )
    bind.execute(
        sa.text(
            "CREATE TABLE news_items ("
            "news_id INTEGER PRIMARY KEY, "
            "url VARCHAR NOT NULL UNIQUE, "
            "title VARCHAR NOT NULL, "
            "body VARCHAR NOT NULL, "
            "published_date VARCHAR NOT NULL, "
            "source VARCHAR NOT NULL, "
            "domain VARCHAR NOT NULL, "
            "image VARCHAR NOT NULL)"
        )
    )
    bind.execute(
        sa.text(
            "CREATE TABLE report_incidents ("
            "report_id INTEGER NOT NULL, "
            "incident_id INTEGER NOT NULL, "
            "PRIMARY KEY (report_id, incident_id))"
        )
    )
    bind.execute(
        sa.text(
            "CREATE TABLE news_incidents ("
            "news_id INTEGER PRIMARY KEY, "
            "incident_id INTEGER NOT NULL)"
        )
    )
    bind.execute(
        sa.text(
            "CREATE TABLE incident_logs ("
            "incident_id INTEGER NOT NULL, "
            "log_datetime VARCHAR NOT NULL, "
            "summary VARCHAR NOT NULL, "
            "PRIMARY KEY (incident_id, log_datetime))"
        )
    )


def _backfill_source_reports(
    bind: sa.engine.Connection,
) -> dict[str, int]:
    rows = bind.execute(
        sa.text(
            "SELECT source, source_id, incident_type, name, "
            "report_date, raw_fields "
            "FROM _legacy_source_reports "
            "ORDER BY source, source_id"
        )
    ).fetchall()
    mapping: dict[str, int] = {}
    for i, row in enumerate(rows):
        report_id = _BASE + _REPORT_OFFSET + i
        bind.execute(
            sa.text(
                "INSERT INTO source_reports "
                "(report_id, source, source_id, incident_type, name, "
                "report_date, raw_fields) "
                "VALUES (:rid, :src, :sid, :type, :name, :date, :raw)"
            ),
            {
                "rid": report_id,
                "src": row.source,
                "sid": row.source_id,
                "type": row.incident_type,
                "name": row.name,
                "date": row.report_date,
                "raw": row.raw_fields,
            },
        )
        mapping[f"{row.source}:{row.source_id}"] = report_id
    return mapping


def _backfill_report_places(
    bind: sa.engine.Connection,
    report_map: dict[str, int],
) -> None:
    rows = bind.execute(
        sa.text("SELECT source, source_id, places FROM _legacy_source_reports")
    ).fetchall()
    for row in rows:
        key = f"{row.source}:{row.source_id}"
        report_id = report_map.get(key)
        if report_id is None:
            continue
        places_raw = row.places
        if not places_raw:
            continue
        places: list[Any] = (
            json.loads(places_raw) if isinstance(places_raw, str) else places_raw
        )
        for place in places:
            if not isinstance(place, dict):
                continue
            bind.execute(
                sa.text(
                    "INSERT OR IGNORE INTO report_places "
                    "(report_id, country_code, subdivision, locality) "
                    "VALUES (:rid, :cc, :sub, :loc)"
                ),
                {
                    "rid": report_id,
                    "cc": str(place.get("country_code", "")),
                    "sub": str(place.get("subdivision", "")),
                    "loc": str(place.get("locality", "")),
                },
            )


def _backfill_news_items(
    bind: sa.engine.Connection,
) -> dict[str, int]:
    rows = bind.execute(
        sa.text(
            "SELECT news_id, url, title, body, published_date, "
            "source, domain, image "
            "FROM _legacy_news_items ORDER BY url"
        )
    ).fetchall()
    mapping: dict[str, int] = {}
    for i, row in enumerate(rows):
        news_id = _BASE + _NEWS_OFFSET + i
        bind.execute(
            sa.text(
                "INSERT INTO news_items "
                "(news_id, url, title, body, published_date, "
                "source, domain, image) "
                "VALUES (:nid, :url, :title, :body, :pub, :src, :dom, :img)"
            ),
            {
                "nid": news_id,
                "url": row.url,
                "title": row.title,
                "body": row.body,
                "pub": row.published_date,
                "src": row.source,
                "dom": row.domain,
                "img": row.image,
            },
        )
        mapping[str(row.news_id)] = news_id
    return mapping


def _backfill_membership(
    bind: sa.engine.Connection,
    report_map: dict[str, int],
    news_map: dict[str, int],
) -> dict[str, int]:
    link_rows = bind.execute(
        sa.text(
            "SELECT DISTINCT source_report_id, news_item_id, incident_id "
            "FROM _legacy_report_news_links"
        )
    ).fetchall()

    legacy_incident_ids: set[str] = set()
    for row in link_rows:
        legacy_incident_ids.add(str(row.incident_id))
    log_rows = bind.execute(
        sa.text("SELECT DISTINCT incident_id FROM _legacy_incident_logs")
    ).fetchall()
    for row in log_rows:
        legacy_incident_ids.add(str(row.incident_id))

    incident_map: dict[str, int] = {}
    for i, old_id in enumerate(sorted(legacy_incident_ids)):
        incident_map[old_id] = _BASE + _INCIDENT_OFFSET + i

    seen_report_incidents: set[tuple[int, int]] = set()
    for row in link_rows:
        report_id = report_map.get(str(row.source_report_id))
        news_id = news_map.get(str(row.news_item_id))
        incident_id = incident_map.get(str(row.incident_id))
        if report_id is None or news_id is None or incident_id is None:
            continue
        if (report_id, incident_id) not in seen_report_incidents:
            bind.execute(
                sa.text(
                    "INSERT OR IGNORE INTO report_incidents "
                    "(report_id, incident_id) VALUES (:rid, :iid)"
                ),
                {"rid": report_id, "iid": incident_id},
            )
            seen_report_incidents.add((report_id, incident_id))

    news_to_incident: dict[int, int] = {}
    for row in link_rows:
        news_id = news_map.get(str(row.news_item_id))
        incident_id = incident_map.get(str(row.incident_id))
        if news_id is None or incident_id is None:
            continue
        if news_id not in news_to_incident:
            news_to_incident[news_id] = incident_id
        else:
            existing = news_to_incident[news_id]
            if incident_id < existing:
                news_to_incident[news_id] = incident_id

    for news_id, incident_id in news_to_incident.items():
        bind.execute(
            sa.text(
                "INSERT OR REPLACE INTO news_incidents "
                "(news_id, incident_id) VALUES (:nid, :iid)"
            ),
            {"nid": news_id, "iid": incident_id},
        )

    return incident_map


def _backfill_incident_logs(
    bind: sa.engine.Connection,
    incident_map: dict[str, int],
) -> None:
    rows = bind.execute(
        sa.text("SELECT iso_datetime, incident_id, summary FROM _legacy_incident_logs")
    ).fetchall()
    for row in rows:
        new_incident_id = incident_map.get(str(row.incident_id))
        if new_incident_id is None:
            continue
        bind.execute(
            sa.text(
                "INSERT OR IGNORE INTO incident_logs "
                "(incident_id, log_datetime, summary) "
                "VALUES (:iid, :dt, :sum)"
            ),
            {
                "iid": new_incident_id,
                "dt": str(row.iso_datetime),
                "sum": str(row.summary),
            },
        )


_INCIDENTS_VIEW_SQL = """
CREATE VIEW incidents AS
WITH ranked AS (
  SELECT ri.incident_id, sr.incident_type, sr.name, sr.source, sr.report_date, ri.report_id,
    ROW_NUMBER() OVER (PARTITION BY ri.incident_id
                       ORDER BY sr.report_date, ri.report_id) AS rn
  FROM report_incidents ri
  JOIN source_reports sr ON sr.report_id = ri.report_id
)
SELECT incident_id,
  CASE WHEN source = 'WHO' THEN 'disease' ELSE 'geophysical' END AS incident_category,
  incident_type, name, report_date AS first_seen_at, report_id AS genesis_report_id
FROM ranked WHERE rn = 1
"""


def _create_incidents_view(bind: sa.engine.Connection) -> None:
    bind.execute(sa.text(_INCIDENTS_VIEW_SQL))


def _drop_legacy_tables(bind: sa.engine.Connection) -> None:
    for table in _LEGACY_TABLES:
        bind.execute(sa.text(f"DROP TABLE IF EXISTS _legacy_{table}"))
