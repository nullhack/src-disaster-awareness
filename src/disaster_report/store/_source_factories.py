from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from disaster_report.models import (
    FactGdacsEvent,
    FactHealthmapAlert,
    FactUsgsEarthquake,
    FactWhoDon,
)
from disaster_report.sources._dates import parse_date as _parse_date
from disaster_report.sources.base import RawIncident

if TYPE_CHECKING:
    from disaster_report.store.sqlite import SqliteIncidentStore


def parse_date(value: str) -> date:
    return _parse_date(value) or date.today()


def _has_row(session: Session, model: type, natural_kw: dict[str, object]) -> bool:
    stmt = select(model)
    for col, value in natural_kw.items():
        stmt = stmt.where(getattr(model, col) == value)
    return session.execute(stmt).scalar_one_or_none() is not None


def build_usgs(
    store: SqliteIncidentStore,
    session: Session,
    incident_key: int,
    raw: RawIncident,
    natural: str,
) -> bool:
    if _has_row(session, FactUsgsEarthquake, {"usgs_id": natural}):
        return False
    session.add(
        FactUsgsEarthquake(
            incident_key=incident_key,
            source_key=store._source_key(session, raw.source_name),
            country_key=store._country_key(session, raw.country),
            incident_type_key=store._type_key(session, raw.incident_type),
            time_key=store._date_key(session, parse_date(raw.report_date)),
            usgs_id=natural,
            magnitude=float(raw.raw_fields.get("mag", 0) or 0),
            depth=float(raw.raw_fields.get("depth", 0) or 0),
            place=raw.raw_fields.get("place", "") or "",
            felt=int(raw.raw_fields.get("felt", 0) or 0),
            tsunami=bool(raw.raw_fields.get("tsunami", False)),
            sig=int(raw.raw_fields.get("sig", 0) or 0),
        )
    )
    return True


def build_gdacs(
    store: SqliteIncidentStore,
    session: Session,
    incident_key: int,
    raw: RawIncident,
    natural: str,
) -> bool:
    if _has_row(session, FactGdacsEvent, {"gdacs_eventid": natural}):
        return False
    session.add(
        FactGdacsEvent(
            incident_key=incident_key,
            source_key=store._source_key(session, raw.source_name),
            country_key=store._country_key(session, raw.country),
            incident_type_key=store._type_key(session, raw.incident_type),
            fromdate_key=store._date_key(session, parse_date(raw.report_date)),
            gdacs_eventid=natural,
            episodeid=str(raw.raw_fields.get("episodeid", "")),
            alertlevel=str(raw.raw_fields.get("alertlevel", "")),
            alertscore=int(raw.raw_fields.get("alertscore", 0) or 0),
            severity=str(raw.raw_fields.get("severity", "")),
            population=int(raw.raw_fields.get("population", 0) or 0),
        )
    )
    return True


def build_who(
    store: SqliteIncidentStore,
    session: Session,
    incident_key: int,
    raw: RawIncident,
    natural: str,
) -> bool:
    if _has_row(session, FactWhoDon, {"don_id": natural}):
        return False
    session.add(
        FactWhoDon(
            incident_key=incident_key,
            source_key=store._source_key(session, raw.source_name),
            country_key=store._country_key(session, raw.country),
            source_date_key=store._date_key(session, parse_date(raw.report_date)),
            don_id=natural,
            title=raw.incident_name,
            provider=raw.source_name,
            disease_key=store._disease_key(session, raw.raw_fields.get("disease")),
        )
    )
    return True


def build_healthmap(
    store: SqliteIncidentStore,
    session: Session,
    incident_key: int,
    raw: RawIncident,
    natural: str,
) -> bool:
    if _has_row(session, FactHealthmapAlert, {"alert_id": natural}):
        return False
    session.add(
        FactHealthmapAlert(
            incident_key=incident_key,
            source_key=store._source_key(session, raw.source_name),
            country_key=store._country_key(session, raw.country),
            source_date_key=store._date_key(session, parse_date(raw.report_date)),
            alert_id=natural,
            feed_source=raw.source_name,
            disease_key=store._disease_key(session, raw.raw_fields.get("disease")),
        )
    )
    return True


SOURCE_FACTORIES: dict[str, Callable[..., bool]] = {
    "usgs": build_usgs,
    "gdacs": build_gdacs,
    "who": build_who,
    "healthmap": build_healthmap,
}


def build_source_row(
    store: SqliteIncidentStore,
    session: Session,
    incident_key: int,
    raw: RawIncident,
    natural: str,
) -> bool:
    name_lower = raw.source_name.lower()
    for token, factory in SOURCE_FACTORIES.items():
        if token in name_lower:
            return factory(store, session, incident_key, raw, natural)
    return False
