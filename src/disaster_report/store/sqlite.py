from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from disaster_report.countries import all_countries, canonical_name, country_info
from disaster_report.classification import classify, country_group
from disaster_report.models import (
    DimCountry,
    DimDate,
    DimDisease,
    DimIncidentType,
    DimPriority,
    DimSeverityLevel,
    DimSource,
    FactGdacsEvent,
    FactHealthmapAlert,
    FactIncident,
    FactNewsArticle,
    FactUsgsEarthquake,
    FactWhoDon,
)
from disaster_report.sources.base import RawArticle, RawIncident
from disaster_report.store._migrations import run_migrations
from disaster_report.store._source_factories import build_source_row, parse_date
from disaster_report.store.base import (
    IncidentRecord,
    IncidentView,
    NewsView,
    SourceView,
)

_PRIORITY_RANK = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
_SEVERITY_NAME = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
_SEVERITY_LEVEL = {v: k for k, v in _SEVERITY_NAME.items()}
_SEVERITY_DESC = {
    "LOW": "Minor impact",
    "MEDIUM": "Moderate impact",
    "HIGH": "Major impact",
    "CRITICAL": "Catastrophic impact",
    "UNKNOWN": "Unranked",
}

_INCIDENT_TYPES = (
    ("Earthquake", "Natural"),
    ("Flood", "Natural"),
    ("Storm", "Natural"),
    ("Tropical Cyclone", "Natural"),
    ("Cyclone", "Natural"),
    ("Typhoon", "Natural"),
    ("Hurricane", "Natural"),
    ("Volcano", "Natural"),
    ("Volcanic Eruption", "Natural"),
    ("Drought", "Natural"),
    ("Wildfire", "Natural"),
    ("Landslide", "Natural"),
    ("Tsunami", "Natural"),
    ("Disease", "Biological"),
    ("Epidemic", "Biological"),
    ("Outbreak", "Biological"),
    ("Other", "Unknown"),
)

_SOURCES = (
    ("USGS Earthquakes", "feed", "A", "near-real-time"),
    ("GDACS", "feed", "A", "daily"),
    ("WHO Disease Outbreak News", "feed", "A", "daily"),
    ("HealthMap", "feed", "B", "near-real-time"),
    ("DDG", "news", "C", "on-demand"),
)


class SqliteIncidentStore:
    def __init__(self, url: str):
        self._engine = create_engine(url, future=True)
        run_migrations(url)
        self._session = sessionmaker(self._engine, expire_on_commit=False)
        self._seed_dimensions()

    def _seed_dimensions(self) -> None:
        with self._session() as session:
            for type_name, category in _INCIDENT_TYPES:
                existing = session.execute(
                    select(DimIncidentType).where(DimIncidentType.type_name == type_name)
                ).scalar_one_or_none()
                if existing is None:
                    session.add(DimIncidentType(type_name=type_name, category=category))
            for name, rank in _PRIORITY_RANK.items():
                existing = session.execute(
                    select(DimPriority).where(DimPriority.priority_name == name)
                ).scalar_one_or_none()
                if existing is None:
                    session.add(DimPriority(priority_name=name, rank=rank))
            for name, desc in _SEVERITY_DESC.items():
                existing = session.execute(
                    select(DimSeverityLevel).where(DimSeverityLevel.severity_name == name)
                ).scalar_one_or_none()
                if existing is None:
                    session.add(DimSeverityLevel(severity_name=name, description=desc))
            for name, src_type, tier, freshness in _SOURCES:
                existing = session.execute(
                    select(DimSource).where(DimSource.name == name)
                ).scalar_one_or_none()
                if existing is None:
                    session.add(
                        DimSource(
                            name=name,
                            type=src_type,
                            reliability_tier=tier,
                            data_freshness=freshness,
                        )
                    )
            existing_iso2 = set(
                session.execute(select(DimCountry.iso2)).scalars().all()
            )
            session.add_all(
                DimCountry(
                    name=name,
                    iso2=iso2,
                    country_group=country_group(iso2),
                    region=region,
                )
                for name, iso2, region in all_countries()
                if iso2 not in existing_iso2
            )
            session.commit()

    def _date_key(self, session: Session, day: date) -> int:
        key = int(day.strftime("%Y%m%d"))
        existing = session.get(DimDate, key)
        if existing is not None:
            return key
        row = DimDate(
            date_key=key,
            full_date=day,
            year=day.year,
            quarter=(day.month - 1) // 3 + 1,
            month=day.month,
            day=day.day,
            day_of_week=day.isoweekday(),
            is_weekend=day.weekday() >= 5,
        )
        session.add(row)
        session.flush()
        return key

    def _country_key(self, session: Session, name: str) -> int:
        iso2, region = country_info(name)
        existing = session.execute(
            select(DimCountry).where(DimCountry.iso2 == iso2)
        ).scalar_one_or_none()
        if existing is not None:
            if iso2 == "XX" and existing.name != "Unknown":
                existing.name = "Unknown"
            return existing.country_key
        canonical = "Unknown" if iso2 == "XX" else (canonical_name(name) or name)
        row = DimCountry(
            name=canonical,
            iso2=iso2,
            country_group=country_group(iso2),
            region=region,
        )
        session.add(row)
        session.flush()
        return row.country_key

    def _source_key(self, session: Session, name: str) -> int:
        existing = session.execute(
            select(DimSource).where(DimSource.name == name)
        ).scalar_one_or_none()
        if existing is not None:
            return existing.source_key
        row = DimSource(
            name=name,
            type="feed",
            reliability_tier="B",
            data_freshness="daily",
        )
        session.add(row)
        session.flush()
        return row.source_key

    def _type_key(self, session: Session, type_name: str) -> int:
        existing = session.execute(
            select(DimIncidentType).where(DimIncidentType.type_name == type_name)
        ).scalar_one_or_none()
        if existing is not None:
            return existing.type_key
        fallback = session.execute(
            select(DimIncidentType).where(DimIncidentType.type_name == "Other")
        ).scalar_one_or_none()
        if fallback is not None:
            return fallback.type_key
        row = DimIncidentType(type_name="Other", category="Unknown")
        session.add(row)
        session.flush()
        return row.type_key

    def _disease_key(self, session: Session, name: str | None) -> int | None:
        if not name:
            return None
        existing = session.execute(
            select(DimDisease).where(DimDisease.disease_name == name)
        ).scalar_one_or_none()
        if existing is not None:
            return existing.disease_key
        row = DimDisease(disease_name=name, category="Biological")
        session.add(row)
        session.flush()
        return row.disease_key

    def _priority_key(self, session: Session, name: str) -> int:
        existing = session.execute(
            select(DimPriority).where(DimPriority.priority_name == name)
        ).scalar_one_or_none()
        if existing is not None:
            return existing.priority_key
        row = DimPriority(priority_name=name, rank=_PRIORITY_RANK.get(name, 9))
        session.add(row)
        session.flush()
        return row.priority_key

    def _level_key(self, session: Session, level: int) -> int:
        name = _SEVERITY_NAME.get(level, "UNKNOWN")
        existing = session.execute(
            select(DimSeverityLevel).where(DimSeverityLevel.severity_name == name)
        ).scalar_one_or_none()
        if existing is not None:
            return existing.level_key
        row = DimSeverityLevel(
            severity_name=name, description=_SEVERITY_DESC.get(name, "Unranked")
        )
        session.add(row)
        session.flush()
        return row.level_key

    def _natural_key(self, raw_incident: RawIncident) -> str:
        event_id = raw_incident.raw_fields.get("event_id")
        if event_id:
            return str(event_id)
        return raw_incident.source_url or f"{raw_incident.incident_name}|{raw_incident.report_date}"

    def _refresh_source_count(self, session: Session, incident_key: int) -> None:
        count = 0
        for fact_cls in (FactUsgsEarthquake, FactGdacsEvent, FactWhoDon, FactHealthmapAlert):
            count += session.execute(
                select(fact_cls).where(fact_cls.incident_key == incident_key)
            ).scalars().all().__len__()
        incident = session.execute(
            select(FactIncident).where(FactIncident.incident_key == incident_key)
        ).scalar_one()
        incident.source_count = count

    def count_incidents(self) -> int:
        with self._session() as session:
            return session.execute(select(FactIncident)).scalars().all().__len__()

    def all_incident_ids(self) -> list[str]:
        with self._session() as session:
            rows = session.execute(select(FactIncident)).scalars().all()
            return sorted(row.incident_id for row in rows)

    def find_by_incident_id(self, incident_id: str) -> IncidentView | None:
        with self._session() as session:
            incident = session.execute(
                select(FactIncident).where(FactIncident.incident_id == incident_id)
            ).scalar_one_or_none()
            if incident is None:
                return None
            return self._to_view(session, incident)

    def _to_view(self, session: Session, incident: FactIncident) -> IncidentView:
        last_updated = session.execute(
            select(DimDate).where(DimDate.date_key == incident.last_updated_date_key)
        ).scalar_one()
        event_date = session.execute(
            select(DimDate).where(DimDate.date_key == incident.event_date_key)
        ).scalar_one()
        country = session.execute(
            select(DimCountry).where(DimCountry.country_key == incident.country_key)
        ).scalar_one()
        itype = session.execute(
            select(DimIncidentType).where(DimIncidentType.type_key == incident.type_key)
        ).scalar_one()
        return IncidentView(
            incident_key=incident.incident_key,
            incident_id=incident.incident_id,
            canonical_name=incident.canonical_name,
            last_updated=last_updated.full_date,
            event_date=event_date.full_date,
            search_keys=list(incident.search_keys or []),
            source_count=incident.source_count,
            country_name=country.name,
            country_iso2=country.iso2,
            ai_digest_date_key=incident.ai_digest_date_key,
            summary=incident.summary,
            incident_type=itype.type_name,
        )

    def get_incident_sources(self, incident_key: int) -> list[SourceView]:
        with self._session() as session:
            out: list[SourceView] = []
            for fact_cls, date_col, key_col in (
                (FactUsgsEarthquake, "time_key", "usgs_id"),
                (FactGdacsEvent, "fromdate_key", "gdacs_eventid"),
                (FactWhoDon, "publication_date_key", "don_id"),
                (FactHealthmapAlert, "alert_date_key", "alert_id"),
            ):
                rows = session.execute(
                    select(fact_cls).where(fact_cls.incident_key == incident_key)
                ).scalars().all()
                for row in rows:
                    source = session.execute(
                        select(DimSource).where(DimSource.source_key == row.source_key)
                    ).scalar_one()
                    day = session.execute(
                        select(DimDate).where(DimDate.date_key == getattr(row, date_col))
                    ).scalar_one()
                    out.append(
                        SourceView(
                            source_name=source.name,
                            report_date=day.full_date.isoformat(),
                            source_url=getattr(row, key_col),
                        )
                    )
            return out

    def get_incident_news(self, incident_key: int) -> list[NewsView]:
        with self._session() as session:
            rows = session.execute(
                select(FactNewsArticle)
                .where(FactNewsArticle.incident_key == incident_key)
                .order_by(FactNewsArticle.published_date_key)
            ).scalars().all()
            out: list[NewsView] = []
            for row in rows:
                day = session.execute(
                    select(DimDate).where(DimDate.date_key == row.published_date_key)
                ).scalar_one()
                out.append(
                    NewsView(
                        headline=row.headline,
                        url=row.url,
                        published_date=day.full_date.isoformat(),
                    )
                )
            return out

    def get_active_incidents(self, as_of: date, within_days: int) -> list[IncidentView]:
        cutoff = as_of - timedelta(days=within_days)
        with self._session() as session:
            incidents = session.execute(
                select(FactIncident)
                .join(DimDate, FactIncident.last_updated_date_key == DimDate.date_key)
                .where(DimDate.full_date >= cutoff, DimDate.full_date <= as_of)
                .order_by(FactIncident.incident_key)
            ).scalars().all()
            return [self._to_view(session, incident) for incident in incidents]

    def get_source_records(self, incident_key: int) -> list[dict]:
        out: list[dict] = []
        with self._session() as session:
            incident = session.execute(
                select(FactIncident).where(FactIncident.incident_key == incident_key)
            ).scalar_one()
            country_name = session.execute(
                select(DimCountry).where(DimCountry.country_key == incident.country_key)
            ).scalar_one().name
            itype = session.execute(
                select(DimIncidentType).where(DimIncidentType.type_key == incident.type_key)
            ).scalar_one()
            disease_name: str | None = None
            if incident.disease_key is not None:
                d = session.get(DimDisease, incident.disease_key)
                if d is not None:
                    disease_name = d.disease_name
            common = {
                "incident_name": incident.canonical_name,
                "country": country_name,
                "disaster_type": itype.type_name,
                "source_name": "PRIOR_DIGEST",
                "source_url": "",
                "report_date": "",
                "raw_fields": {"prior_summary": incident.summary, "disease": disease_name},
            }
            out.append(common)
        return out

    def find_disease_name(self, incident_key: int) -> str | None:
        with self._session() as session:
            incident = session.get(FactIncident, incident_key)
            if incident is None or incident.disease_key is None:
                return None
            d = session.get(DimDisease, incident.disease_key)
            return d.disease_name if d is not None else None

    def upsert_incident(self, record: IncidentRecord) -> int:
        with self._session() as session:
            existing = session.execute(
                select(FactIncident).where(FactIncident.incident_id == record.incident_id)
            ).scalar_one_or_none()
            if existing is not None:
                session.commit()
                return existing.incident_key
            country_key = self._country_key(session, record.country)
            type_key = self._type_key(session, record.incident_type)
            priority_key = self._priority_key(session, record.priority)
            level_key = self._level_key(session, record.severity_level)
            disease_key = self._disease_key(session, record.disease)
            first_key = self._date_key(session, parse_date(record.first_reported_date))
            last_key = self._date_key(session, parse_date(record.last_updated_date))
            event_key = self._date_key(session, parse_date(record.event_date))
            row = FactIncident(
                incident_id=record.incident_id,
                canonical_name=record.canonical_name,
                summary=record.summary,
                first_reported_date_key=first_key,
                last_updated_date_key=last_key,
                event_date_key=event_key,
                country_key=country_key,
                type_key=type_key,
                priority_key=priority_key,
                level_key=level_key,
                source_count=0,
                disease_key=disease_key,
                should_report=record.should_report,
                search_keys=list(record.search_keys),
                ai_digest_date_key=None,
            )
            session.add(row)
            session.flush()
            key = row.incident_key
            session.commit()
            return key

    def link_source_record(self, incident_key: int, raw_incident: RawIncident) -> bool:
        natural = self._natural_key(raw_incident)
        with self._session() as session:
            inserted = build_source_row(self, session, incident_key, raw_incident, natural)
            if inserted:
                session.flush()
                self._refresh_source_count(session, incident_key)
            session.commit()
            return inserted

    def link_news(self, incident_key: int, article: RawArticle) -> bool:
        with self._session() as session:
            existing = session.execute(
                select(FactNewsArticle).where(FactNewsArticle.url == article.url)
            ).scalar_one_or_none()
            if existing is not None:
                session.commit()
                return False
            row = FactNewsArticle(
                source_key=self._source_key(session, article.source_name),
                published_date_key=self._date_key(
                    session, parse_date(article.published_date)
                ),
                url=article.url,
                headline=article.headline,
                body=article.body,
                outlet=article.outlet,
                image=article.image,
                incident_key=incident_key,
            )
            session.add(row)
            session.commit()
            return True

    def set_last_updated(self, incident_key: int, last_updated_date: str) -> None:
        with self._session() as session:
            incident = session.execute(
                select(FactIncident).where(FactIncident.incident_key == incident_key)
            ).scalar_one()
            incident.last_updated_date_key = self._date_key(
                session, parse_date(last_updated_date)
            )
            session.commit()

    def set_digest(
        self,
        incident_key: int,
        digest: dict[str, Any],
        digested_on: date,
        country: str,
    ) -> None:
        severity = str(digest.get("severity", "LOW")).upper()
        severity_level = _SEVERITY_LEVEL.get(severity, 1)
        priority_name, _ = classify(severity_level, country)
        canonical_name = digest.get("canonical_name") or ""
        summary = digest.get("summary", "")
        search_keys = list(digest.get("search_keys", []))
        with self._session() as session:
            incident = session.execute(
                select(FactIncident).where(FactIncident.incident_key == incident_key)
            ).scalar_one()
            if canonical_name:
                incident.canonical_name = canonical_name
            incident.summary = summary
            incident.level_key = self._level_key(session, severity_level)
            incident.priority_key = self._priority_key(session, priority_name)
            incident.search_keys = search_keys
            incident.ai_digest_date_key = self._date_key(session, digested_on)
            session.commit()
