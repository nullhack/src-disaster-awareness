from __future__ import annotations

from datetime import date

from sqlalchemy import ForeignKey, JSON, MetaData, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column


_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(MappedAsDataclass, DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


class DimDate(Base):
    __tablename__ = "dim_date"

    date_key: Mapped[int] = mapped_column(primary_key=True, autoincrement=False, init=True)
    full_date: Mapped[date]
    year: Mapped[int]
    quarter: Mapped[int]
    month: Mapped[int]
    day: Mapped[int]
    day_of_week: Mapped[int]
    is_weekend: Mapped[bool]


class DimCountry(Base):
    __tablename__ = "dim_country"

    country_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    iso2: Mapped[str] = mapped_column(String(2))
    country_group: Mapped[str] = mapped_column(String(1))
    region: Mapped[str] = mapped_column(String(100))


class DimSource(Base):
    __tablename__ = "dim_source"

    source_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(50))
    reliability_tier: Mapped[str] = mapped_column(String(20))
    data_freshness: Mapped[str] = mapped_column(String(20))


class DimIncidentType(Base):
    __tablename__ = "dim_incident_type"

    type_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    type_name: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(50))


class DimDisease(Base):
    __tablename__ = "dim_disease"

    disease_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    disease_name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(50))


class DimPriority(Base):
    __tablename__ = "dim_priority"

    priority_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    priority_name: Mapped[str] = mapped_column(String(10))
    rank: Mapped[int]


class DimSeverityLevel(Base):
    __tablename__ = "dim_severity_level"

    level_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    severity_name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(200))


class FactIncident(Base):
    __tablename__ = "fact_incident"

    incident_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(32), unique=True)
    canonical_name: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text)
    first_reported_date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"))
    last_updated_date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"))
    event_date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"))
    country_key: Mapped[int] = mapped_column(ForeignKey("dim_country.country_key"))
    type_key: Mapped[int] = mapped_column(ForeignKey("dim_incident_type.type_key"))
    priority_key: Mapped[int] = mapped_column(ForeignKey("dim_priority.priority_key"))
    level_key: Mapped[int] = mapped_column(ForeignKey("dim_severity_level.level_key"))
    source_count: Mapped[int]
    disease_key: Mapped[int | None] = mapped_column(
        ForeignKey("dim_disease.disease_key"), default=None
    )
    should_report: Mapped[bool] = mapped_column(default=True)
    search_keys: Mapped[list] = mapped_column(JSON, default_factory=list)
    ai_digest_date_key: Mapped[int | None] = mapped_column(
        ForeignKey("dim_date.date_key"), default=None
    )


class FactGdacsEvent(Base):
    __tablename__ = "fact_gdacs_event"

    gdacs_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    incident_key: Mapped[int] = mapped_column(ForeignKey("fact_incident.incident_key"))
    source_key: Mapped[int] = mapped_column(ForeignKey("dim_source.source_key"))
    country_key: Mapped[int] = mapped_column(ForeignKey("dim_country.country_key"))
    type_key: Mapped[int] = mapped_column(ForeignKey("dim_incident_type.type_key"))
    fromdate_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"))
    gdacs_eventid: Mapped[str] = mapped_column(String(64), unique=True)
    episodeid: Mapped[str] = mapped_column(String(64))
    alertlevel: Mapped[str] = mapped_column(String(10))
    alertscore: Mapped[int]
    severity: Mapped[str] = mapped_column(String(20))
    population: Mapped[int]


class FactWhoDon(Base):
    __tablename__ = "fact_who_don"

    who_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    incident_key: Mapped[int] = mapped_column(ForeignKey("fact_incident.incident_key"))
    source_key: Mapped[int] = mapped_column(ForeignKey("dim_source.source_key"))
    country_key: Mapped[int] = mapped_column(ForeignKey("dim_country.country_key"))
    publication_date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"))
    don_id: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    provider: Mapped[str] = mapped_column(String(100))
    disease_key: Mapped[int | None] = mapped_column(
        ForeignKey("dim_disease.disease_key"), default=None
    )


class FactHealthmapAlert(Base):
    __tablename__ = "fact_healthmap_alert"

    healthmap_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    incident_key: Mapped[int] = mapped_column(ForeignKey("fact_incident.incident_key"))
    source_key: Mapped[int] = mapped_column(ForeignKey("dim_source.source_key"))
    country_key: Mapped[int] = mapped_column(ForeignKey("dim_country.country_key"))
    alert_date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"))
    alert_id: Mapped[str] = mapped_column(String(32), unique=True)
    feed_source: Mapped[str] = mapped_column(String(100))
    disease_key: Mapped[int | None] = mapped_column(
        ForeignKey("dim_disease.disease_key"), default=None
    )


class FactUsgsEarthquake(Base):
    __tablename__ = "fact_usgs_earthquake"

    usgs_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    incident_key: Mapped[int] = mapped_column(ForeignKey("fact_incident.incident_key"))
    source_key: Mapped[int] = mapped_column(ForeignKey("dim_source.source_key"))
    country_key: Mapped[int] = mapped_column(ForeignKey("dim_country.country_key"))
    type_key: Mapped[int] = mapped_column(ForeignKey("dim_incident_type.type_key"))
    time_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"))
    usgs_id: Mapped[str] = mapped_column(String(32), unique=True)
    magnitude: Mapped[float]
    depth: Mapped[float]
    place: Mapped[str] = mapped_column(String(200))
    felt: Mapped[int]
    tsunami: Mapped[bool]
    sig: Mapped[int]


class FactNewsArticle(Base):
    __tablename__ = "fact_news_article"

    news_key: Mapped[int] = mapped_column(init=False, primary_key=True)
    source_key: Mapped[int] = mapped_column(ForeignKey("dim_source.source_key"))
    published_date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"))
    url: Mapped[str] = mapped_column(String(500), unique=True)
    headline: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    outlet: Mapped[str] = mapped_column(String(200))
    image: Mapped[str | None] = mapped_column(String(500), default=None)
    incident_key: Mapped[int | None] = mapped_column(
        ForeignKey("fact_incident.incident_key"), default=None
    )
