from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("disaster_report.store", reason="store not implemented")

from disaster_report.sources.base import RawArticle, RawIncident
from disaster_report.store import IncidentRecord, SqliteIncidentStore


def _record(incident_id: str = "20260629-PH-EQ", **overrides) -> IncidentRecord:
    base = dict(
        incident_id=incident_id,
        canonical_name="Sarangani Earthquake",
        summary="A magnitude 5.2 earthquake struck near Sarangani, Philippines.",
        country="Philippines",
        incident_type="Earthquake",
        priority="MEDIUM",
        severity_level=2,
        event_date="2026-06-29",
        first_reported_date="2026-06-29",
        last_updated_date="2026-06-29",
        should_report=True,
        search_keys=["Sarangani earthquake"],
    )
    base.update(overrides)
    return IncidentRecord(**base)


def _raw_incident(source: str = "USGS", url: str = "https://usgs.example/1") -> RawIncident:
    return RawIncident(
        source_name=source,
        incident_name="M5.2 Earthquake near Sarangani",
        country="Philippines",
        disaster_type="Earthquake",
        report_date="2026-06-29T00:00:00Z",
        source_url=url,
        raw_fields={"mag": 5.2, "depth": 10.0, "place": "near Sarangani, Philippines"},
    )


def _article(url: str = "https://n/1", published: str = "2026-06-29T08:00:00Z") -> RawArticle:
    return RawArticle(
        source_name="DDG",
        headline="Quake shakes Sarangani",
        body="body",
        url=url,
        outlet="Reuters",
        published_date=published,
    )


@pytest.fixture
def store(db_url):
    return SqliteIncidentStore(db_url)


def test_upsert_then_find_round_trips_core_fields(store):
    key = store.upsert_incident(_record())

    assert store.count_incidents() == 1
    assert store.all_incident_ids() == ["20260629-PH-EQ"]

    view = store.find_by_incident_id("20260629-PH-EQ")
    assert view is not None
    assert view.incident_key == key
    assert view.incident_id == "20260629-PH-EQ"
    assert view.canonical_name == "Sarangani Earthquake"
    assert view.last_updated == date(2026, 6, 29)
    assert view.event_date == date(2026, 6, 29)
    assert view.search_keys == ["Sarangani earthquake"]
    assert view.source_count == 0


def test_upsert_is_idempotent_by_incident_id(store):
    store.upsert_incident(_record())
    store.upsert_incident(_record(canonical_name="Other name"))

    assert store.count_incidents() == 1
    view = store.find_by_incident_id("20260629-PH-EQ")
    assert view is not None


def test_find_by_incident_id_returns_none_when_absent(store):
    assert store.find_by_incident_id("does-not-exist") is None


def test_link_news_dedups_by_url_and_reports_newness(store):
    key = store.upsert_incident(_record())

    assert store.link_news(key, _article("https://n/1")) is True
    assert store.link_news(key, _article("https://n/1")) is False
    assert store.link_news(key, _article("https://n/2")) is True

    news = store.get_incident_news(key)
    assert {n.url for n in news} == {"https://n/1", "https://n/2"}
    assert all(n.headline and n.published_date for n in news)


def test_link_source_record_dedups_and_is_retrievable(store):
    key = store.upsert_incident(_record())

    store.link_source_record(key, _raw_incident("USGS", "https://usgs.example/1"))
    store.link_source_record(key, _raw_incident("USGS", "https://usgs.example/1"))
    store.link_source_record(key, _raw_incident("GDACS", "https://gdacs.example/1"))

    sources = store.get_incident_sources(key)
    assert {s.source_name for s in sources} == {"USGS", "GDACS"}
    view = store.find_by_incident_id("20260629-PH-EQ")
    assert view is not None
    assert view.source_count == 2


def test_get_active_incidents_filters_by_last_updated_window(store):
    fresh_key = store.upsert_incident(_record("20260629-PH-EQ"))
    store.upsert_incident(
        _record(
            "20260610-ID-EQ",
            country="Indonesia",
            last_updated_date="2026-06-10",
            event_date="2026-06-10",
            first_reported_date="2026-06-10",
        )
    )

    active = store.get_active_incidents(as_of=date(2026, 6, 29), within_days=7)

    assert [a.incident_key for a in active] == [fresh_key]


def test_get_active_incidents_includes_recently_bumped_old_event(store):
    key = store.upsert_incident(
        _record(
            "20260601-ID-EQ",
            country="Indonesia",
            event_date="2026-06-01",
            first_reported_date="2026-06-01",
            last_updated_date="2026-06-25",
        )
    )

    active = store.get_active_incidents(as_of=date(2026, 6, 29), within_days=7)

    assert {a.incident_key for a in active} == {key}


def test_store_seeds_core_dimensions_on_init(db_url):
    import sqlalchemy as sa

    from disaster_report.models import (
        DimCountry,
        DimIncidentType,
        DimPriority,
        DimSeverityLevel,
        DimSource,
    )

    store = SqliteIncidentStore(db_url)

    with store._engine.connect() as conn:
        countries = conn.execute(sa.select(DimCountry)).all()
        types = conn.execute(sa.select(DimIncidentType)).all()
        priorities = conn.execute(sa.select(DimPriority)).all()
        levels = conn.execute(sa.select(DimSeverityLevel)).all()
        sources = conn.execute(sa.select(DimSource)).all()

    assert len(countries) >= 100
    assert len(types) >= 10
    assert len(priorities) == 3
    assert len(levels) == 5
    assert len(sources) == 5


def test_dim_status_table_not_present_after_init(db_url):
    import sqlalchemy as sa

    store = SqliteIncidentStore(db_url)
    with store._engine.connect() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dim_status'"
        ).all()
    assert rows == [], "dim_status must not exist"


def test_fact_incident_has_no_status_key_column(db_url):
    store = SqliteIncidentStore(db_url)
    with store._engine.connect() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info(fact_incident)").all()
    names = {c[1] for c in cols}
    assert "status_key" not in names


def test_link_source_record_uses_event_id_when_present_for_dedup(store):
    key = store.upsert_incident(_record())
    raw_a = _raw_incident("USGS", "https://usgs.example/long-url-1")
    raw_a.raw_fields["event_id"] = "us7000abcd"
    raw_b = _raw_incident("USGS", "https://usgs.example/different-url-2")
    raw_b.raw_fields["event_id"] = "us7000abcd"

    assert store.link_source_record(key, raw_a) is True
    assert store.link_source_record(key, raw_b) is False

    sources = store.get_incident_sources(key)
    assert len(sources) == 1


def test_dim_date_key_is_yyyymmdd_integer_not_surrogate(store):
    import sqlalchemy as sa

    from disaster_report.models import DimDate

    store.upsert_incident(_record("20260629-PH-EQ"))

    with store._engine.connect() as conn:
        rows = conn.execute(sa.select(DimDate.date_key)).all()

    assert rows, "dim_date should have at least one row after upsert"
    for (key,) in rows:
        assert 19000101 <= key <= 99991231, f"date_key {key} is not a YYYYMMDD integer"
    assert 20260629 in {k for (k,) in rows}


def test_type_key_does_not_lazy_create_unknown_types(store):
    import sqlalchemy as sa

    from disaster_report.models import DimIncidentType

    key = store.upsert_incident(_record("20260629-XX-OT", incident_type="Totally Novel Type"))
    with store._engine.connect() as conn:
        rows = conn.execute(sa.select(DimIncidentType.type_name)).all()
    names = {r[0] for r in rows}
    assert "Totally Novel Type" not in names, "unknown type must NOT be lazy-created"
    assert "Other" in names


def test_disease_key_lazy_creates_named_disease_from_record(store):
    import sqlalchemy as sa

    from disaster_report.models import DimDisease

    store.upsert_incident(
        _record(
            "20260629-XX-EP",
            incident_type="Disease",
            disease="Marburg virus disease",
        )
    )
    with store._engine.connect() as conn:
        rows = conn.execute(sa.select(DimDisease.disease_name)).all()
    names = {r[0] for r in rows}
    assert "Marburg virus disease" in names, "named disease must lazy-create dim_disease row"


def test_store_creates_read_only_views_joining_all_dimensions(store):
    expected_views = {
        "v_incident",
        "v_usgs_earthquake",
        "v_gdacs_event",
        "v_who_don",
        "v_healthmap_alert",
        "v_news_article",
    }
    with store._engine.connect() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='view'"
        ).all()
    actual = {r[0] for r in rows}
    assert expected_views <= actual, f"missing views: {expected_views - actual}"


def test_v_incident_returns_human_readable_labels_after_upsert(store):
    incident_key = store.upsert_incident(_record())
    with store._engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT incident_id, country_name, country_iso2, incident_type, "
            "priority, severity, first_reported_date, event_date, "
            "should_report, search_keys "
            "FROM v_incident WHERE incident_key = ?",
            (incident_key,),
        ).one()
    assert row.incident_id == "20260629-PH-EQ"
    assert row.country_name == "Philippines"
    assert row.country_iso2 == "PH"
    assert row.incident_type == "Earthquake"
    assert row.priority == "MEDIUM"
    assert row.severity == "MEDIUM"
    assert row.first_reported_date == "2026-06-29"
    assert row.event_date == "2026-06-29"
    assert row.should_report == 1
    assert "Sarangani earthquake" in row.search_keys


def test_v_usgs_earthquake_joins_to_incident_id_and_dims(store):
    incident_key = store.upsert_incident(_record())
    store.link_source_record(incident_key, _raw_incident(source="USGS"))
    with store._engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT incident_id, country_name, source_name, magnitude, depth, place, usgs_id "
            "FROM v_usgs_earthquake WHERE incident_key = ?",
            (incident_key,),
        ).one()
    assert row.incident_id == "20260629-PH-EQ"
    assert row.country_name == "Philippines"
    assert "USGS" in row.source_name
    assert row.magnitude == 5.2
    assert row.depth == 10.0
    assert row.place == "near Sarangani, Philippines"


def test_v_news_article_lists_articles_with_incident_id(store):
    incident_key = store.upsert_incident(_record())
    store.link_news(incident_key, _article())
    with store._engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT incident_id, headline, url, source_name FROM v_news_article"
        ).one()
    assert row.incident_id == "20260629-PH-EQ"
    assert "Sarangani" in row.headline
    assert row.url == "https://n/1"


def test_dim_country_group_uses_classification_matrix_not_region_letter(store):
    import sqlalchemy as sa

    from disaster_report.models import DimCountry

    store.upsert_incident(_record("20260629-PH-EQ", country="Philippines"))
    store.upsert_incident(_record("20260629-AU-EQ", country="Australia"))
    store.upsert_incident(_record("20260629-US-EQ", country="United States"))
    store.upsert_incident(_record("20260629-XX-EQ", country="off the coast of Central America"))

    with store._engine.connect() as conn:
        rows = conn.execute(
            sa.select(DimCountry.iso2, DimCountry.country_group)
        ).all()

    by_iso = {r[0]: r[1] for r in rows}
    assert by_iso.get("PH") == "A", "Philippines must be group A (Asia priority)"
    assert by_iso.get("AU") == "B", "Australia must be group B"
    assert by_iso.get("US") == "C", "US must be group C (default)"
    assert by_iso.get("XX") == "C", "Unknown must default to group C"


def test_unknown_country_row_is_named_unknown_not_raw_place_string(store):
    import sqlalchemy as sa

    from disaster_report.models import DimCountry

    store.upsert_incident(_record("20260629-XX-EQ", country="off the coast of Central America"))
    with store._engine.connect() as conn:
        row = conn.execute(
            sa.select(DimCountry).where(DimCountry.iso2 == "XX")
        ).one()
    assert row.name == "Unknown"


def test_country_key_normalizes_existing_xx_row_name_to_unknown(store):
    import sqlalchemy as sa

    from disaster_report.models import DimCountry

    with store._engine.begin() as conn:
        conn.execute(sa.text(
            "UPDATE dim_country SET name = 'off the coast of Central America' WHERE iso2 = 'XX'"
        ))
    store.upsert_incident(_record("20260629-XX-EQ", country="off the coast of Central America"))
    with store._engine.connect() as conn:
        row = conn.execute(
            sa.select(DimCountry).where(DimCountry.iso2 == "XX")
        ).one()
    assert row.name == "Unknown"
