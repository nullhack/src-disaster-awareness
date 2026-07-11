
from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    func,
    insert,
    select,
    text,
)

from disaster_report.models import (
    Incident,
    IncidentLog,
    NewsItem,
    ReportPlace,
    SourceReport,
)

_metadata = MetaData()

_source_reports_t = Table(
    "source_reports",
    _metadata,
    Column("report_id", Integer, primary_key=True),
    Column("source", String, nullable=False),
    Column("source_id", String, nullable=False),
    Column("incident_type", String, nullable=False),
    Column("name", String, nullable=False),
    Column("report_date", String, nullable=False),
    Column("raw_fields", JSON, nullable=False),
    UniqueConstraint("source", "source_id", name="uq_source_reports_natural"),
)

_report_places_t = Table(
    "report_places",
    _metadata,
    Column("report_id", Integer, nullable=False),
    Column("country_code", String, nullable=False),
    Column("subdivision", String, nullable=False),
    Column("locality", String, nullable=False),
    PrimaryKeyConstraint("report_id", "country_code", "subdivision", "locality"),
)

_news_items_t = Table(
    "news_items",
    _metadata,
    Column("news_id", Integer, primary_key=True),
    Column("url", String, nullable=False, unique=True),
    Column("title", String, nullable=False),
    Column("body", String, nullable=False),
    Column("published_date", String, nullable=False),
    Column("source", String, nullable=False),
    Column("domain", String, nullable=False),
    Column("image", String, nullable=False),
)

_report_incidents_t = Table(
    "report_incidents",
    _metadata,
    Column("report_id", Integer, nullable=False),
    Column("incident_id", Integer, nullable=False),
    PrimaryKeyConstraint("report_id", "incident_id"),
)

_news_incidents_t = Table(
    "news_incidents",
    _metadata,
    Column("news_id", Integer, primary_key=True),
    Column("incident_id", Integer, nullable=False),
)

_incident_logs_t = Table(
    "incident_logs",
    _metadata,
    Column("incident_id", Integer, nullable=False),
    Column("log_datetime", String, nullable=False),
    Column("summary", String, nullable=False),
    PrimaryKeyConstraint("incident_id", "log_datetime"),
)

_incident_log_news_t = Table(
    "incident_log_news",
    _metadata,
    Column("incident_id", Integer, nullable=False),
    Column("log_datetime", String, nullable=False),
    Column("news_id", Integer, nullable=False),
    PrimaryKeyConstraint("incident_id", "log_datetime", "news_id"),
)

_INCIDENTS_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS incidents AS
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


def _mint_id() -> int:
    return int(time.time() * 1000)


def _source_report_from_row(row: Any) -> SourceReport:
    return SourceReport(
        source=str(row["source"]),
        source_id=str(row["source_id"]),
        incident_type=str(row["incident_type"]),
        name=str(row["name"]),
        places=[],
        report_date=str(row["report_date"]),
        raw_fields=dict(row["raw_fields"]) if row["raw_fields"] is not None else {},
    )


def _news_item_from_row(row: Any) -> NewsItem:
    return NewsItem(
        url=str(row["url"]),
        title=str(row["title"]),
        body=str(row["body"]),
        published_date=str(row["published_date"]),
        source=str(row["source"]),
        domain=str(row["domain"]),
        image=str(row["image"]),
        news_id=int(row["news_id"]),
    )


def _place_from_row(row: Any) -> ReportPlace:
    return ReportPlace(
        country_code=str(row["country_code"]),
        subdivision=str(row["subdivision"]),
        locality=str(row["locality"]),
    )


def _log_from_row(row: Any) -> IncidentLog:
    return IncidentLog(
        incident_id=int(row["incident_id"]),
        log_datetime=str(row["log_datetime"]),
        summary=str(row["summary"]),
    )


def _incident_from_row(row: Any) -> Incident:
    return Incident(
        incident_id=int(row["incident_id"]),
        incident_category=str(row["incident_category"]),
        incident_type=str(row["incident_type"]),
        name=str(row["name"]),
        first_seen_at=str(row["first_seen_at"]),
        genesis_report_id=int(row["genesis_report_id"]),
    )


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _insert_log_if_absent(conn: Any, log: IncidentLog) -> None:
    existing = conn.execute(
        select(_incident_logs_t.c.log_datetime).where(
            _incident_logs_t.c.incident_id == log.incident_id,
            _incident_logs_t.c.log_datetime == log.log_datetime,
        )
    ).first()
    if existing is not None:
        return
    conn.execute(
        insert(_incident_logs_t).values(
            incident_id=log.incident_id,
            log_datetime=log.log_datetime,
            summary=log.summary,
        )
    )


class Warehouse:

    def __init__(
        self,
        db_url: str,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:

        self._engine = create_engine(db_url)
        self._clock = clock
        _metadata.create_all(self._engine)
        with self._engine.begin() as conn:
            conn.execute(text(_INCIDENTS_VIEW_SQL))

    def ingest_source_report(self, report: SourceReport) -> int:

        with self._engine.begin() as conn:
            existing = conn.execute(
                select(_source_reports_t.c.report_id).where(
                    _source_reports_t.c.source == report.source,
                    _source_reports_t.c.source_id == report.source_id,
                )
            ).first()
            if existing is not None:
                return int(existing.report_id)
            report_id = _mint_id()
            conn.execute(
                insert(_source_reports_t).values(
                    report_id=report_id,
                    source=report.source,
                    source_id=report.source_id,
                    incident_type=report.incident_type,
                    name=report.name,
                    report_date=report.report_date,
                    raw_fields=report.raw_fields,
                )
            )
            return report_id

    def ingest_report_places(self, report_id: int, places: list[ReportPlace]) -> None:

        if not places:
            return
        with self._engine.begin() as conn:
            for place in places:
                conn.execute(
                    insert(_report_places_t)
                    .prefix_with("OR IGNORE")
                    .values(
                        report_id=report_id,
                        country_code=place.country_code,
                        subdivision=place.subdivision,
                        locality=place.locality,
                    )
                )

    def read_report_places(self, report_id: int) -> list[ReportPlace]:

        with self._engine.connect() as conn:
            rows = conn.execute(
                select(_report_places_t).where(
                    _report_places_t.c.report_id == report_id
                )
            ).fetchall()
        return [_place_from_row(row._mapping) for row in rows]

    def read_searched_report_keys(self) -> set[str]:

        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    _source_reports_t.c.source,
                    _source_reports_t.c.source_id,
                    _source_reports_t.c.raw_fields,
                )
            ).fetchall()
        return {
            f"{row.source}:{row.source_id}"
            for row in rows
            if isinstance(row.raw_fields, dict)
            and "_news_searched_at" in row.raw_fields
        }

    def read_source_report_keys(self) -> set[str]:

        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    _source_reports_t.c.source,
                    _source_reports_t.c.source_id,
                )
            ).fetchall()
        return {f"{row.source}:{row.source_id}" for row in rows}

    def mark_report_searched(self, source: str, source_id: str, timestamp: str) -> None:

        from sqlalchemy import update

        with self._engine.begin() as conn:
            row = conn.execute(
                select(_source_reports_t.c.raw_fields).where(
                    _source_reports_t.c.source == source,
                    _source_reports_t.c.source_id == source_id,
                )
            ).first()
            if row is None:
                return
            fields = dict(row.raw_fields) if isinstance(row.raw_fields, dict) else {}
            fields["_news_searched_at"] = timestamp
            conn.execute(
                update(_source_reports_t)
                .where(
                    _source_reports_t.c.source == source,
                    _source_reports_t.c.source_id == source_id,
                )
                .values(raw_fields=fields)
            )

    def ingest_news_item(self, item: NewsItem) -> int:

        with self._engine.begin() as conn:
            existing = conn.execute(
                select(_news_items_t.c.news_id).where(_news_items_t.c.url == item.url)
            ).first()
            if existing is not None:
                return int(existing.news_id)
            news_id = _mint_id()
            conn.execute(
                insert(_news_items_t).values(
                    news_id=news_id,
                    url=item.url,
                    title=item.title,
                    body=item.body,
                    published_date=item.published_date,
                    source=item.source,
                    domain=item.domain,
                    image=item.image,
                )
            )
            return news_id

    def read_news_item(self, news_id: int) -> NewsItem:

        with self._engine.connect() as conn:
            row = conn.execute(
                select(_news_items_t).where(_news_items_t.c.news_id == news_id)
            ).first()
        if row is None:
            raise KeyError(news_id)
        return _news_item_from_row(row._mapping)

    def assign_news_to_incident(self, news_id: int, incident_id: int) -> None:

        with self._engine.begin() as conn:
            conn.execute(
                insert(_news_incidents_t)
                .prefix_with("OR REPLACE")
                .values(news_id=news_id, incident_id=incident_id)
            )

    def read_incident_for_news(self, news_id: int) -> int | None:

        with self._engine.connect() as conn:
            row = conn.execute(
                select(_news_incidents_t.c.incident_id).where(
                    _news_incidents_t.c.news_id == news_id
                )
            ).first()
        return int(row.incident_id) if row is not None else None

    def read_incidents_for_news(self, news_ids: set[int]) -> dict[int, set[int]]:

        if not news_ids:
            return {}
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    _news_incidents_t.c.news_id,
                    _news_incidents_t.c.incident_id,
                ).where(_news_incidents_t.c.news_id.in_(news_ids))
            ).fetchall()
        mapping: dict[int, set[int]] = {}
        for row in rows:
            mapping.setdefault(int(row.news_id), set()).add(int(row.incident_id))
        return mapping

    def add_report_incident(self, report_id: int, incident_id: int) -> None:

        with self._engine.begin() as conn:
            conn.execute(
                insert(_report_incidents_t)
                .prefix_with("OR IGNORE")
                .values(report_id=report_id, incident_id=incident_id)
            )

    def read_report_ids_for_incident(self, incident_id: int) -> list[int]:

        with self._engine.connect() as conn:
            rows = conn.execute(
                select(_report_incidents_t.c.report_id).where(
                    _report_incidents_t.c.incident_id == incident_id
                )
            ).fetchall()
        return [int(row.report_id) for row in rows]

    def read_incident_ids_for_report(self, report_id: int) -> list[int]:

        with self._engine.connect() as conn:
            rows = conn.execute(
                select(_report_incidents_t.c.incident_id).where(
                    _report_incidents_t.c.report_id == report_id
                )
            ).fetchall()
        return [int(row.incident_id) for row in rows]

    def read_incident_ids_for_source_id(self, source_id: str) -> list[int]:

        with self._engine.connect() as conn:
            rows = conn.execute(
                select(_report_incidents_t.c.incident_id)
                .join(
                    _source_reports_t,
                    _source_reports_t.c.report_id == _report_incidents_t.c.report_id,
                )
                .where(_source_reports_t.c.source_id == source_id)
            ).fetchall()
        return [int(row.incident_id) for row in rows]

    def append_timeline(self, row: IncidentLog) -> None:

        with self._engine.begin() as conn:
            _insert_log_if_absent(conn, row)

    def append_timeline_with_provenance(
        self, log: IncidentLog, news_ids: set[int]
    ) -> None:

        with self._engine.begin() as conn:
            _insert_log_if_absent(conn, log)
            if news_ids:
                rows = [
                    {
                        "incident_id": log.incident_id,
                        "log_datetime": log.log_datetime,
                        "news_id": nid,
                    }
                    for nid in news_ids
                ]
                conn.execute(
                    insert(_incident_log_news_t).prefix_with("OR IGNORE").values(rows)
                )

    def read_summarized_news_ids(self, incident_id: int) -> set[int]:

        with self._engine.connect() as conn:
            rows = conn.execute(
                select(_incident_log_news_t.c.news_id).where(
                    _incident_log_news_t.c.incident_id == incident_id
                )
            ).fetchall()
        return {int(row.news_id) for row in rows}

    def read_source_reports(self) -> list[SourceReport]:

        with self._engine.connect() as conn:
            rows = conn.execute(select(_source_reports_t)).fetchall()
        return [_source_report_from_row(row._mapping) for row in rows]

    def read_source_report_by_id(self, report_id: int) -> SourceReport | None:

        import dataclasses

        with self._engine.connect() as conn:
            row = conn.execute(
                select(_source_reports_t).where(
                    _source_reports_t.c.report_id == report_id
                )
            ).first()
        if row is None:
            return None
        report = _source_report_from_row(row._mapping)
        places = self.read_report_places(report_id)
        return dataclasses.replace(report, places=places)

    def read_timeline(self, incident_id: int) -> list[IncidentLog]:

        with self._engine.connect() as conn:
            rows = conn.execute(
                select(_incident_logs_t)
                .where(_incident_logs_t.c.incident_id == incident_id)
                .order_by(_incident_logs_t.c.log_datetime)
            ).fetchall()
        return [_log_from_row(row._mapping) for row in rows]

    def read_incidents(self) -> list[Incident]:

        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM incidents ORDER BY first_seen_at")
            ).fetchall()
        return [
            Incident(
                incident_id=int(row.incident_id),
                incident_category=str(row.incident_category),
                incident_type=str(row.incident_type),
                name=str(row.name),
                first_seen_at=str(row.first_seen_at),
                genesis_report_id=int(row.genesis_report_id),
            )
            for row in rows
        ]

    def read_news(self, incident_id: int) -> list[NewsItem]:

        with self._engine.connect() as conn:
            rows = conn.execute(
                select(_news_items_t)
                .join(
                    _news_incidents_t,
                    _news_incidents_t.c.news_id == _news_items_t.c.news_id,
                )
                .where(_news_incidents_t.c.incident_id == incident_id)
            ).fetchall()
        return [_news_item_from_row(row._mapping) for row in rows]

    def active_incidents(self, window_days: int) -> list[Incident]:

        raw_now = self._clock() if self._clock is not None else None
        now = _as_utc(raw_now) if raw_now is not None else datetime.now(timezone.utc)
        cutoff = now - timedelta(days=window_days)
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(
                    _news_incidents_t.c.incident_id,
                    func.max(_news_items_t.c.published_date),
                )
                .join(
                    _news_items_t,
                    _news_items_t.c.news_id == _news_incidents_t.c.news_id,
                )
                .group_by(_news_incidents_t.c.incident_id)
            ).fetchall()
        active_ids: set[int] = set()
        for row in rows:
            try:
                row_dt = _as_utc(datetime.fromisoformat(str(row[1])))
            except (ValueError, TypeError):
                continue
            if cutoff <= row_dt <= now:
                active_ids.add(int(row.incident_id))
        if not active_ids:
            return []
        all_incidents = {i.incident_id: i for i in self.read_incidents()}
        return [
            all_incidents[iid] for iid in sorted(active_ids) if iid in all_incidents
        ]
