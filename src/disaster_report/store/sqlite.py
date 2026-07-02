from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from disaster_report.countries import UNKNOWN_ISO2, all_countries, country_info, normalize_country_name
from disaster_report.classification import (
    PANDEMIC_LEVEL_TO_NAME,
    PANDEMIC_NAME_TO_LEVEL,
    PRIORITY_RANK,
    SEVERITY_LEVELS,
    SEVERITY_NAMES,
    ClassifyContext,
    classify,
    country_group,
    de_escalate_pandemic_potential,
    escalate_priority,
)
from disaster_report.deriver import DeriveInput, derive_canonical_name, derive_search_keys
from disaster_report.models import (
    DimCountry,
    DimDate,
    DimDisease,
    DimIncidentType,
    DimPandemicPotential,
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
from disaster_report.sources.base import PRIOR_DIGEST_SOURCE, RawArticle, RawIncident
from disaster_report.sources.registry import SOURCE_REGISTRY
from disaster_report.store._migrations import run_migrations
from disaster_report.store._source_factories import build_source_row, parse_date
from disaster_report.store.base import (
    IncidentRecord,
    IncidentView,
    NewsView,
    SourceView,
)

# Display-only severity descriptions (store-specific; the canonical int<->name
# maps live in ``classification`` and are imported above).
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

# DimSource seed derived from the single SOURCE_REGISTRY (token -> spec).
# Adding a source anywhere in the pipeline therefore also seeds it here.
_SOURCES = tuple(
    (s.display_name, s.source_type, s.reliability_tier, s.data_freshness)
    for s in SOURCE_REGISTRY.values()
)


def _date_from_key(key: int) -> date | None:
    """Inverse of _date_key: parse a YYYYMMDD int back to a date.

    Returns None if the key is not a valid YYYYMMDD. Used to compute real
    day-gaps between incidents (raw int subtraction would mis-count across
    month boundaries, e.g. 20260701 - 20260625 == 76 ints but 6 days).
    """
    if key <= 0:
        return None
    year, rest = divmod(key, 10_000)
    month, day = divmod(rest, 100)
    try:
        return date(year, month, day)
    except ValueError:
        return None


class SqliteIncidentStore:
    def __init__(self, url: str):
        self._engine = create_engine(url, future=True)
        run_migrations(url)
        self._session = sessionmaker(self._engine, expire_on_commit=False)
        self._seed_dimensions()

    def _seed_if_missing(
        self,
        session: Session,
        model_cls: type,
        natural_col: str,
        natural_val: object,
        **fields: object,
    ) -> None:
        """Insert a dimension row iff no row matches ``natural_val`` yet."""
        filter_col = getattr(model_cls, natural_col)
        existing = session.execute(
            select(model_cls).where(filter_col == natural_val)
        ).scalar_one_or_none()
        if existing is None:
            session.add(model_cls(**fields))

    def _seed_dimensions(self) -> None:
        with self._session() as session:
            for type_name, category in _INCIDENT_TYPES:
                self._seed_if_missing(
                    session, DimIncidentType, "incident_type", type_name,
                    incident_type=type_name, category=category,
                )
            for name, rank in PRIORITY_RANK.items():
                self._seed_if_missing(
                    session, DimPriority, "priority", name,
                    priority=name, rank=rank,
                )
            for name, desc in _SEVERITY_DESC.items():
                self._seed_if_missing(
                    session, DimSeverityLevel, "severity", name,
                    severity=name, description=desc,
                )
            for level, name in PANDEMIC_LEVEL_TO_NAME.items():
                self._seed_if_missing(
                    session, DimPandemicPotential, "pandemic_potential_key", level,
                    pandemic_potential_key=level,
                    pandemic_potential=name,
                    description=f"Pandemic potential: {name}",
                )
            for name, src_type, tier, freshness in _SOURCES:
                self._seed_if_missing(
                    session, DimSource, "source_name", name,
                    source_name=name, type=src_type,
                    reliability_tier=tier, data_freshness=freshness,
                )
            existing_iso2 = set(
                session.execute(select(DimCountry.iso2)).scalars().all()
            )
            session.add_all(
                DimCountry(
                    country_name=name,
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
            if iso2 == UNKNOWN_ISO2 and existing.country_name != "Unknown":
                existing.country_name = "Unknown"
            return existing.country_key
        canonical = "Unknown" if iso2 == UNKNOWN_ISO2 else (normalize_country_name(name) or name)
        row = DimCountry(
            country_name=canonical,
            iso2=iso2,
            country_group=country_group(iso2),
            region=region,
        )
        session.add(row)
        session.flush()
        return row.country_key

    def _source_key(self, session: Session, name: str) -> int:
        existing = session.execute(
            select(DimSource).where(DimSource.source_name == name)
        ).scalar_one_or_none()
        if existing is not None:
            return existing.source_key
        row = DimSource(
            source_name=name,
            type="feed",
            reliability_tier="B",
            data_freshness="daily",
        )
        session.add(row)
        session.flush()
        return row.source_key

    def _type_key(self, session: Session, type_name: str) -> int:
        existing = session.execute(
            select(DimIncidentType).where(DimIncidentType.incident_type == type_name)
        ).scalar_one_or_none()
        if existing is not None:
            return existing.incident_type_key
        fallback = session.execute(
            select(DimIncidentType).where(DimIncidentType.incident_type == "Other")
        ).scalar_one_or_none()
        if fallback is not None:
            return fallback.incident_type_key
        row = DimIncidentType(incident_type="Other", category="Unknown")
        session.add(row)
        session.flush()
        return row.incident_type_key

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
            select(DimPriority).where(DimPriority.priority == name)
        ).scalar_one_or_none()
        if existing is not None:
            return existing.priority_key
        row = DimPriority(priority=name, rank=PRIORITY_RANK.get(name, 9))
        session.add(row)
        session.flush()
        return row.priority_key

    def _level_key(self, session: Session, level: int) -> int:
        name = SEVERITY_NAMES.get(level, "UNKNOWN")
        existing = session.execute(
            select(DimSeverityLevel).where(DimSeverityLevel.severity == name)
        ).scalar_one_or_none()
        if existing is not None:
            return existing.severity_key
        row = DimSeverityLevel(
            severity=name, description=_SEVERITY_DESC.get(name, "Unranked")
        )
        session.add(row)
        session.flush()
        return row.severity_key

    def _pandemic_potential_key(self, session: Session, level: int) -> int:
        existing = session.get(DimPandemicPotential, level)
        if existing is not None:
            return existing.pandemic_potential_key
        name = PANDEMIC_LEVEL_TO_NAME.get(level, "NONE")
        row = DimPandemicPotential(
            pandemic_potential_key=level, pandemic_potential=name, description=f"Pandemic potential: {name}"
        )
        session.add(row)
        session.flush()
        return row.pandemic_potential_key

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

    def undigested_incident_ids(self) -> list[str]:
        """Incident_ids with no AI digest yet (ai_digest_date_key IS NULL)."""
        with self._session() as session:
            rows = session.execute(
                select(FactIncident).where(FactIncident.ai_digest_date_key.is_(None))
            ).scalars().all()
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
            select(DimIncidentType).where(DimIncidentType.incident_type_key == incident.incident_type_key)
        ).scalar_one()
        severity = session.execute(
            select(DimSeverityLevel).where(DimSeverityLevel.severity_key == incident.severity_key)
        ).scalar_one()
        priority = session.execute(
            select(DimPriority).where(DimPriority.priority_key == incident.priority_key)
        ).scalar_one()
        pandemic_potential = ""
        if incident.pandemic_potential_key is not None:
            pp = session.get(DimPandemicPotential, incident.pandemic_potential_key)
            if pp is not None:
                pandemic_potential = pp.pandemic_potential or ""
        disease_name: str | None = None
        if incident.disease_key is not None:
            dz = session.get(DimDisease, incident.disease_key)
            if dz is not None:
                disease_name = dz.disease_name
        return IncidentView(
            incident_key=incident.incident_key,
            incident_id=incident.incident_id,
            canonical_name=incident.canonical_name,
            last_updated=last_updated.full_date,
            event_date=event_date.full_date,
            search_keys=list(incident.search_keys or []),
            source_count=incident.source_count,
            country_name=country.country_name,
            country_iso2=country.iso2,
            ai_digest_date_key=incident.ai_digest_date_key,
            summary=incident.summary,
            incident_type=itype.incident_type,
            should_report=bool(incident.should_report),
            severity=severity.severity,
            priority=priority.priority,
            priority_rank=priority.rank,
            pandemic_potential=pandemic_potential,
            event_status=incident.event_status or "",
            disease_name=disease_name,
            days_since_event=(last_updated.full_date - event_date.full_date).days,
        )

    def get_incident_sources(self, incident_key: int) -> list[SourceView]:
        with self._session() as session:
            out: list[SourceView] = []
            for fact_cls, date_col, key_col in (
                (FactUsgsEarthquake, "time_key", "usgs_id"),
                (FactGdacsEvent, "fromdate_key", "gdacs_eventid"),
                (FactWhoDon, "source_date_key", "don_id"),
                (FactHealthmapAlert, "source_date_key", "alert_id"),
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
                            source_name=source.source_name,
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
                .order_by(FactNewsArticle.source_date_key)
            ).scalars().all()
            out: list[NewsView] = []
            for row in rows:
                day = session.execute(
                    select(DimDate).where(DimDate.date_key == row.source_date_key)
                ).scalar_one()
                out.append(
                    NewsView(
                        headline=row.headline,
                        url=row.url,
                        published_date=day.full_date.isoformat(),
                        outlet=row.outlet or "",
                    )
                )
            return out

    def get_incident_news_full(self, incident_key: int) -> list[dict]:
        with self._session() as session:
            rows = session.execute(
                select(FactNewsArticle)
                .where(FactNewsArticle.incident_key == incident_key)
                .order_by(FactNewsArticle.source_date_key)
            ).scalars().all()
            out: list[dict] = []
            for row in rows:
                day = session.execute(
                    select(DimDate).where(DimDate.date_key == row.source_date_key)
                ).scalar_one()
                out.append(
                    {
                        "headline": row.headline,
                        "url": row.url,
                        "body": row.body,
                        "outlet": row.outlet,
                        "published_date": day.full_date.isoformat(),
                    }
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

    # --- report read-port ------------------------------------------------------
    def incident_source_counts(
        self, incident_key: int
    ) -> tuple[int, int, int, int, int]:
        """``(who_don, usgs, gdacs, healthmap, news)`` fact counts."""
        with self._session() as session:
            who = session.execute(
                select(func.count()).select_from(FactWhoDon).where(
                    FactWhoDon.incident_key == incident_key
                )
            ).scalar_one()
            usgs = session.execute(
                select(func.count()).select_from(FactUsgsEarthquake).where(
                    FactUsgsEarthquake.incident_key == incident_key
                )
            ).scalar_one()
            gdacs = session.execute(
                select(func.count()).select_from(FactGdacsEvent).where(
                    FactGdacsEvent.incident_key == incident_key
                )
            ).scalar_one()
            hm = session.execute(
                select(func.count()).select_from(FactHealthmapAlert).where(
                    FactHealthmapAlert.incident_key == incident_key
                )
            ).scalar_one()
            news = session.execute(
                select(func.count()).select_from(FactNewsArticle).where(
                    FactNewsArticle.incident_key == incident_key
                )
            ).scalar_one()
        return (who, usgs, gdacs, hm, news)

    def incident_news_capped(self, incident_key: int, cap: int) -> list[NewsView]:
        """News for one incident, newest-first, limited to ``cap``."""
        with self._session() as session:
            rows = session.execute(
                select(FactNewsArticle)
                .where(FactNewsArticle.incident_key == incident_key)
                .order_by(FactNewsArticle.source_date_key.desc())
                .limit(cap)
            ).scalars().all()
            out: list[NewsView] = []
            for row in rows:
                day = session.execute(
                    select(DimDate).where(DimDate.date_key == row.source_date_key)
                ).scalar_one()
                out.append(
                    NewsView(
                        headline=row.headline,
                        url=row.url,
                        published_date=day.full_date.isoformat(),
                        outlet=row.outlet or "",
                    )
                )
            return out

    def usgs_max_magnitude(self, incident_key: int) -> float | None:
        """Max USGS magnitude across the incident's linked earthquakes."""
        with self._session() as session:
            return session.execute(
                select(func.max(FactUsgsEarthquake.magnitude)).where(
                    FactUsgsEarthquake.incident_key == incident_key
                )
            ).scalar_one_or_none()

    def gdacs_alert(self, incident_key: int) -> tuple[str | None, int] | None:
        """``(alertlevel, max_population)`` for the incident's GDACS events.

        ``alertlevel`` joins the distinct levels (``","``-separated), mirroring
        ``GROUP_CONCAT(DISTINCT alertlevel)``; ``None`` overall when the
        incident has no GDACS rows.
        """
        with self._session() as session:
            rows = session.execute(
                select(FactGdacsEvent.alertlevel, FactGdacsEvent.population).where(
                    FactGdacsEvent.incident_key == incident_key
                )
            ).all()
        if not rows:
            return None
        distinct: list[str] = []
        seen: set[str] = set()
        for lvl, _pop in rows:
            if lvl is not None and lvl not in seen:
                seen.add(lvl)
                distinct.append(lvl)
        alertlevel = ",".join(distinct) if distinct else None
        max_pop = max((int(p or 0) for _l, p in rows), default=0)
        return (alertlevel, max_pop)

    def who_don_range(self) -> tuple[str, str, int]:
        """``(min_date_iso, max_date_iso, count)`` over all WHO DON rows."""
        with self._session() as session:
            row = session.execute(
                select(func.min(DimDate.full_date), func.max(DimDate.full_date), func.count())
                .select_from(FactWhoDon)
                .join(DimDate, DimDate.date_key == FactWhoDon.source_date_key)
            ).one()
        min_d, max_d, n = row
        if not n:
            return ("", "", 0)
        return (min_d.isoformat(), max_d.isoformat(), n)

    def get_source_records(self, incident_key: int) -> list[dict]:
        out: list[dict] = []
        with self._session() as session:
            incident = session.execute(
                select(FactIncident).where(FactIncident.incident_key == incident_key)
            ).scalar_one()
            country_name = session.execute(
                select(DimCountry).where(DimCountry.country_key == incident.country_key)
            ).scalar_one().country_name
            itype = session.execute(
                select(DimIncidentType).where(DimIncidentType.incident_type_key == incident.incident_type_key)
            ).scalar_one()
            disease_name: str | None = None
            if incident.disease_key is not None:
                d = session.get(DimDisease, incident.disease_key)
                if d is not None:
                    disease_name = d.disease_name
            common = {
                "incident_name": incident.canonical_name,
                "country": country_name,
                "incident_type": itype.incident_type,
                "source_name": PRIOR_DIGEST_SOURCE,
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
            disease_key = self._disease_key(session, record.disease_name)
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
                incident_type_key=type_key,
                priority_key=priority_key,
                severity_key=level_key,
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
                source_date_key=self._date_key(
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

    def _current_level(self, session: Session, incident: FactIncident) -> int:
        row = session.get(DimSeverityLevel, incident.severity_key)
        if row is None:
            return 1
        return SEVERITY_LEVELS.get(row.severity, 1)

    def _current_pandemic_potential(self, session: Session, incident: FactIncident) -> int | None:
        """Return the AI pandemic-potential level, or ``None`` when the column
        is NULL (not applicable / not yet digested)."""
        if incident.pandemic_potential_key is None:
            return None
        row = session.get(DimPandemicPotential, incident.pandemic_potential_key)
        if row is None:
            return None
        return PANDEMIC_NAME_TO_LEVEL.get(row.pandemic_potential, 0)

    def _build_classify_context(
        self, session: Session, incident: FactIncident, level: int
    ) -> ClassifyContext:
        country = session.execute(
            select(DimCountry).where(DimCountry.country_key == incident.country_key)
        ).scalar_one_or_none()
        country_group = (country.country_group if country else None) or "C"
        region = (country.region if country else "") or ""
        itype = session.execute(
            select(DimIncidentType).where(DimIncidentType.incident_type_key == incident.incident_type_key)
        ).scalar_one_or_none()
        incident_type = itype.incident_type if itype else ""
        disease_name: str | None = None
        if incident.disease_key is not None:
            disease = session.get(DimDisease, incident.disease_key)
            if disease is not None:
                disease_name = disease.disease_name
        pops = session.execute(
            select(FactGdacsEvent.population).where(
                FactGdacsEvent.incident_key == incident.incident_key
            )
        ).scalars().all()
        population = max((int(p or 0) for p in pops), default=0)
        source_keys: set[int] = set()
        for fact_cls in (
            FactUsgsEarthquake, FactGdacsEvent, FactWhoDon, FactHealthmapAlert,
        ):
            source_keys.update(
                session.execute(
                    select(fact_cls.source_key).where(
                        fact_cls.incident_key == incident.incident_key
                    )
                ).scalars().all()
            )
        tiers: tuple[str, ...] = ()
        if source_keys:
            tiers = tuple(
                session.execute(
                    select(DimSource.reliability_tier).where(
                        DimSource.source_key.in_(sorted(source_keys))
                    )
                ).scalars().all()
            )
        return ClassifyContext(
            level=level,
            country_group=country_group,
            region=region,
            disease_name=disease_name,
            incident_type=incident_type,
            population=population,
            source_tiers=tiers,
            pandemic_potential=self._current_pandemic_potential(session, incident),
            event_status=incident.event_status or "",
        )

    def _ratchet_priority(
        self,
        session: Session,
        incident: FactIncident,
        recomputed_priority: str,
        recomputed_should: bool,
    ) -> tuple[str, str, bool]:
        """Monotonic priority ratchet (shared by set_digest + reclassify_all).

        Returns ``(current_priority_name, desired_priority_name, desired_should)``
        for an incident given a freshly recomputed verdict: priority can only
        escalate (never demote) and ``should_report`` can only latch on (never
        off). Computes the target; the caller decides whether to persist.
        """
        cur_priority = session.execute(
            select(DimPriority).where(
                DimPriority.priority_key == incident.priority_key
            )
        ).scalar_one_or_none()
        cur_priority_name = cur_priority.priority if cur_priority else "LOW"
        desired_priority_name = escalate_priority(cur_priority_name, recomputed_priority)
        desired_should = bool(incident.should_report) or bool(recomputed_should)
        return cur_priority_name, desired_priority_name, desired_should

    def _derive_identity(
        self, session: Session, incident: FactIncident
    ) -> tuple[str, list[str]]:
        """Derive canonical_name + search_keys deterministically from the
        incident's structured facts. Single source of truth - the AI no longer
        authors these (it supplies only classification + summary), so every
        caller of set_digest gets consistent, date-anchored keys.
        """
        country = session.execute(
            select(DimCountry).where(DimCountry.country_key == incident.country_key)
        ).scalar_one_or_none()
        country_name = country.country_name if country else ""
        itype = session.execute(
            select(DimIncidentType).where(
                DimIncidentType.incident_type_key == incident.incident_type_key
            )
        ).scalar_one_or_none()
        incident_type = itype.incident_type if itype else ""
        disease_name = ""
        if incident.disease_key is not None:
            d = session.get(DimDisease, incident.disease_key)
            if d is not None:
                disease_name = d.disease_name or ""
        event_date = (
            _date_from_key(incident.event_date_key)
            if incident.event_date_key
            else None
        )
        place_row = session.execute(
            select(FactUsgsEarthquake.place).where(
                FactUsgsEarthquake.incident_key == incident.incident_key
            )
        ).scalars().first()
        ctx = DeriveInput(
            incident_type=incident_type,
            country=country_name,
            event_date=event_date,
            disease_name=disease_name,
            place=place_row or "",
        )
        return derive_canonical_name(ctx), derive_search_keys(ctx)

    def set_digest(
        self,
        incident_key: int,
        digest: dict[str, Any],
        digested_on: date,
        country: str,
    ) -> None:
        """Apply an AI digest with a monotonic ratchet.

        Severity, priority never demote; ``should_report`` never clears.
        ``pandemic_potential`` ratchets up like severity. ``event_status`` and
        the content fields (canonical name, summary, search keys) refresh every
        digest. Classification fields are written only when they escalate.
        """
        severity = str(digest.get("severity", "LOW")).upper()
        ai_level = SEVERITY_LEVELS.get(severity, 1)
        summary = digest.get("summary", "")
        pandemic_potential_raw = str(digest.get("pandemic_potential", "")).strip().upper()
        event_status = str(digest.get("event_status", "")).strip().lower()
        ai_pandemic_potential = PANDEMIC_NAME_TO_LEVEL.get(pandemic_potential_raw) if pandemic_potential_raw else None
        with self._session() as session:
            incident = session.execute(
                select(FactIncident).where(FactIncident.incident_key == incident_key)
            ).scalar_one()
            # canonical_name + search_keys are DERIVED here (not AI-authored).
            canonical_name, search_keys = self._derive_identity(session, incident)
            current_level = self._current_level(session, incident)
            new_level = max(current_level, ai_level)
            current_pandemic_potential = self._current_pandemic_potential(session, incident)
            ctx = self._build_classify_context(session, incident, new_level)
            if current_pandemic_potential is None and ai_pandemic_potential is None:
                new_pandemic_potential: int | None = None
            else:
                new_pandemic_potential = max(x for x in (current_pandemic_potential, ai_pandemic_potential) if x is not None)
            # De-escalate endemic pathogens (COVID/flu/fever): clamp stored pp to LOW
            # so the AI over-rating (e.g. seasonal flu -> CRITICAL) doesn't persist.
            new_pandemic_potential = de_escalate_pandemic_potential(ctx.disease_name, new_pandemic_potential)
            ctx = replace(ctx, pandemic_potential=new_pandemic_potential, event_status=event_status)
            recomputed_priority, recomputed_should = classify(ctx)
            cur_priority_name, desired_priority_name, desired_should = (
                self._ratchet_priority(
                    session, incident, recomputed_priority, recomputed_should
                )
            )
            digest_key = self._date_key(session, digested_on)

            changed = False
            if canonical_name and canonical_name != incident.canonical_name:
                incident.canonical_name = canonical_name
                changed = True
            if summary != incident.summary:
                incident.summary = summary
                changed = True
            if search_keys != list(incident.search_keys or []):
                incident.search_keys = search_keys
                changed = True
            if new_level > current_level:
                incident.severity_key = self._level_key(session, new_level)
                changed = True
            if desired_priority_name != cur_priority_name:
                incident.priority_key = self._priority_key(session, desired_priority_name)
                changed = True
            if desired_should != bool(incident.should_report):
                incident.should_report = desired_should
                changed = True
            if new_pandemic_potential is not None and new_pandemic_potential != current_pandemic_potential:
                incident.pandemic_potential_key = self._pandemic_potential_key(
                    session, new_pandemic_potential
                )
                changed = True
            if event_status and event_status != (incident.event_status or ""):
                incident.event_status = event_status
                changed = True
            if digest_key != incident.ai_digest_date_key:
                incident.ai_digest_date_key = digest_key
                changed = True
            if changed:
                session.commit()

    def country_context(self, country_name: str) -> tuple[str, str]:
        iso2, region = country_info(country_name)
        with self._session() as session:
            row = session.execute(
                select(DimCountry.country_group, DimCountry.region).where(
                    DimCountry.iso2 == iso2
                )
            ).first()
        if row is not None:
            return (row[0] or "C", row[1] or region or "")
        # Not yet seeded (only possible for a brand-new iso2=XX entry that has
        # not been upserted yet); fall back to the same rule used for seeding.
        return (country_group(iso2), region or "")

    def _source_token_tiers(self) -> dict[str, str]:
        tokens = tuple(SOURCE_REGISTRY)
        with self._session() as session:
            rows = session.execute(
                select(DimSource.source_name, DimSource.reliability_tier)
            ).all()
        token_tier: dict[str, str] = {}
        for name, tier in rows:
            low = (name or "").lower()
            for token in tokens:
                if token in low:
                    token_tier[token] = tier
        return token_tier

    @staticmethod
    def _match_source_tier(raw_name: str, token_tier: dict[str, str]) -> str:
        low = (raw_name or "").lower()
        for token, tier in token_tier.items():
            if token in low:
                return tier
        return "B"

    def source_tiers(self, source_names: list[str]) -> tuple[str, ...]:
        if not source_names:
            return ()
        token_tier = self._source_token_tiers()
        return tuple(
            self._match_source_tier(name, token_tier) for name in source_names
        )

    def reclassify_all(self, dry_run: bool = True) -> list[dict]:
        """Recompute ``priority`` + ``should_report`` from current severity.

        Non-destructive: does NOT re-derive ``level_key`` from source events
        (AI-assessed severity is preserved). Monotonic and idempotent — a
        second run produces no deltas. Returns one delta dict per incident
        whose classification actually changes.
        """
        deltas: list[dict] = []
        with self._session() as session:
            incidents = session.execute(select(FactIncident)).scalars().all()
            for incident in incidents:
                current_level = self._current_level(session, incident)
                ctx = self._build_classify_context(session, incident, current_level)
                recomputed_priority, recomputed_should = classify(ctx)
                cur_priority_name, desired_priority_name, desired_should = (
                    self._ratchet_priority(
                        session, incident, recomputed_priority, recomputed_should
                    )
                )
                if (
                    desired_priority_name == cur_priority_name
                    and desired_should == bool(incident.should_report)
                ):
                    continue
                deltas.append(
                    {
                        "incident_id": incident.incident_id,
                        "severity": SEVERITY_NAMES.get(current_level, "UNKNOWN"),
                        "priority": {"from": cur_priority_name, "to": desired_priority_name},
                        "should_report": {
                            "from": bool(incident.should_report),
                            "to": desired_should,
                        },
                    }
                )
                if not dry_run:
                    if desired_priority_name != cur_priority_name:
                        incident.priority_key = self._priority_key(
                            session, desired_priority_name
                        )
                    if desired_should != bool(incident.should_report):
                        incident.should_report = desired_should
            if not dry_run:
                session.commit()
        return deltas

    def find_recent_disease_incident(
        self,
        disease_name: str,
        country: str,
        as_of: date,
        within_days: int,
    ) -> int | None:
        """Find the most-recently-updated disease incident matching (disease,
        country) whose ``last_updated_date_key`` falls within ``within_days`` of
        ``as_of``. Returns its incident_key, or None.

        Used by the pipeline to merge recurring re-reports of the same outbreak
        into one incident instead of creating a new row each day. Only matches
        incidents that carry a non-null ``disease_key``.
        """
        if not disease_name or within_days <= 0:
            return None
        iso2, _ = country_info(country)
        cutoff = as_of - timedelta(days=within_days)
        cutoff_key = int(cutoff.strftime("%Y%m%d"))
        with self._session() as session:
            row = session.execute(
                select(FactIncident.incident_key)
                .join(DimCountry, DimCountry.country_key == FactIncident.country_key)
                .join(DimDisease, DimDisease.disease_key == FactIncident.disease_key)
                .where(
                    DimCountry.iso2 == iso2,
                    DimDisease.disease_name == disease_name,
                    FactIncident.last_updated_date_key >= cutoff_key,
                )
                .order_by(FactIncident.last_updated_date_key.desc())
                .limit(1)
            ).first()
        return int(row[0]) if row else None

    def merge_duplicate_disease_incidents(
        self,
        dry_run: bool = True,
        window_days: int = 30,
    ) -> list[dict]:
        """Collapse existing (disease, country) duplicates into one survivor.

        For each (disease, country) group, incidents whose first_reported_date
        chains within ``window_days`` of the previous one are treated as the
        same recurring outbreak and merged into the earliest survivor: their
        source fact rows + news articles are re-pointed to the survivor, the
        loser ``fact_incident`` rows are deleted, and the survivor's
        source_count + last_updated are refreshed. Idempotent.

        NOT a CLI command — one-time cleanup invoked from a throwaway script.
        """
        deltas: list[dict] = []
        with self._session() as session:
            incidents = (
                session.execute(
                    select(FactIncident)
                    .where(FactIncident.disease_key.is_not(None))
                )
                .scalars()
                .all()
            )
            groups: dict[tuple[int | None, int | None], list[FactIncident]] = {}
            for incident in incidents:
                groups.setdefault(
                    (incident.disease_key, incident.country_key), []
                ).append(incident)

            for (disease_key, country_key), members in groups.items():
                if len(members) < 2:
                    continue
                members.sort(
                    key=lambda record: (record.event_date_key, record.incident_key)
                )
                survivor = members[0]
                chain_end = _date_from_key(survivor.event_date_key)
                for candidate in members[1:]:
                    candidate_date = _date_from_key(candidate.event_date_key)
                    gap = (
                        (candidate_date - chain_end).days
                        if chain_end is not None and candidate_date is not None
                        else window_days + 1
                    )
                    if gap > window_days:
                        # New outbreak cluster; candidate starts a new survivor.
                        survivor = candidate
                        chain_end = candidate_date
                        continue
                    # Duplicate within the chain -> merge into survivor.
                    self._repoint_children(
                        session, candidate.incident_key, survivor.incident_key
                    )
                    deltas.append(
                        {
                            "loser": candidate.incident_id,
                            "survivor": survivor.incident_id,
                            "disease_key": disease_key,
                            "country_key": country_key,
                        }
                    )
                    chain_end = candidate_date
                    if not dry_run:
                        session.flush()
                        self._refresh_source_count(session, survivor.incident_key)
                        if (
                            candidate.last_updated_date_key
                            > survivor.last_updated_date_key
                        ):
                            survivor.last_updated_date_key = (
                                candidate.last_updated_date_key
                            )
                        session.delete(candidate)
            if not dry_run:
                session.commit()
        return deltas

    def _repoint_children(
        self, session: Session, loser_key: int, survivor_key: int
    ) -> None:
        """Re-point every child fact row from the loser incident to the survivor."""
        for model in (
            FactUsgsEarthquake,
            FactGdacsEvent,
            FactWhoDon,
            FactHealthmapAlert,
            FactNewsArticle,
        ):
            rows = session.execute(
                select(model).where(model.incident_key == loser_key)
            ).scalars().all()
            for row in rows:
                row.incident_key = survivor_key
