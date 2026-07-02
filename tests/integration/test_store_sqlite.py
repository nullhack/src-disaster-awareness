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
        incident_type="Earthquake",
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


def test_get_incident_news_full_returns_body_and_outlet(store):
    key = store.upsert_incident(_record())
    store.link_news(key, _article("https://n/1"))

    full = store.get_incident_news_full(key)
    assert len(full) == 1
    row = full[0]
    assert row["url"] == "https://n/1"
    assert row["headline"] == "Quake shakes Sarangani"
    assert row["body"] == "body"
    assert row["outlet"] == "Reuters"
    assert row["published_date"]


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
        rows = conn.execute(sa.select(DimIncidentType.incident_type)).all()
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
            disease_name="Marburg virus disease",
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
    assert row.country_name == "Unknown"


def test_country_key_normalizes_existing_xx_row_name_to_unknown(store):
    import sqlalchemy as sa

    from disaster_report.models import DimCountry

    with store._engine.begin() as conn:
        conn.execute(sa.text(
            "UPDATE dim_country SET country_name = 'off the coast of Central America' WHERE iso2 = 'XX'"
        ))
    store.upsert_incident(_record("20260629-XX-EQ", country="off the coast of Central America"))
    with store._engine.connect() as conn:
        row = conn.execute(
            sa.select(DimCountry).where(DimCountry.iso2 == "XX")
        ).one()
    assert row.country_name == "Unknown"


# --------------------------------------------------------------------------- #
# set_digest ratchet + reclassify_all backfill
# --------------------------------------------------------------------------- #

def _row(store, incident_key: int) -> dict:
    with store._engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT incident_id, priority, severity, should_report, summary, "
            "canonical_name, pandemic_potential, event_status "
            "FROM v_incident WHERE incident_key = ?",
            (incident_key,),
        ).one()
    return row._mapping


def test_set_digest_escalates_severity_and_latches_should_report(store):
    # Start: LOW severity in group C (Germany) -> should_report = False.
    key = store.upsert_incident(
        _record(
            "20260629-DE-EQ",
            country="Germany",
            priority="LOW",
            severity_level=1,
            should_report=False,
            canonical_name="Initial",
            summary="initial summary",
        )
    )
    assert _row(store, key)["should_report"] == 0

    store.set_digest(
        key,
        {
            "summary": "Upgraded event.",
            "severity": "CRITICAL",
        },
        digested_on=date(2026, 6, 29),
        country="Germany",
    )

    row = _row(store, key)
    assert row["severity"] == "CRITICAL"
    assert row["priority"] == "HIGH"
    assert row["should_report"] == 1
    # canonical_name + search_keys are now DERIVED (not AI-authored) — assert refresh happened.
    assert row["canonical_name"] == "Earthquake Germany June 2026"
    assert row["summary"] == "Upgraded event."


def test_set_digest_never_demotes_severity_or_clears_should_report(store):
    key = store.upsert_incident(
        _record(
            "20260629-DE-EQ",
            country="Germany",
            priority="HIGH",
            severity_level=4,
            should_report=True,
            canonical_name="Critical Quake",
            summary="original",
        )
    )

    # A later digest with a *lower* severity must not demote.
    store.set_digest(
        key,
        {
            "canonical_name": "Critical Quake",
            "summary": "revised detail",
            "severity": "LOW",
            "search_keys": ["berlin"],
        },
        digested_on=date(2026, 6, 30),
        country="Germany",
    )

    row = _row(store, key)
    assert row["severity"] == "CRITICAL"
    assert row["priority"] == "HIGH"
    assert row["should_report"] == 1
    # Content still refreshes.
    assert row["summary"] == "revised detail"


def test_reclassify_all_dry_run_writes_nothing(store):
    # Group A MEDIUM earthquake deliberately mislabeled as not reportable:
    # classify(2, "A") -> ("MEDIUM", True), so a delta is expected.
    key = store.upsert_incident(
        _record(
            "20260629-PH-EQ",
            country="Philippines",
            priority="LOW",
            severity_level=2,
            should_report=False,
        )
    )
    before = _row(store, key)

    deltas = store.reclassify_all(dry_run=True)

    after = _row(store, key)
    assert any(d["incident_id"] == "20260629-PH-EQ" for d in deltas)
    assert after == before, "dry-run must not persist changes"


def test_reclassify_all_apply_persists_deltas_and_is_idempotent(store):
    store.upsert_incident(
        _record(
            "20260629-PH-EQ",
            country="Philippines",
            priority="LOW",
            severity_level=2,
            should_report=False,
        )
    )

    first = store.reclassify_all(dry_run=False)
    assert any(d["incident_id"] == "20260629-PH-EQ" for d in first)

    row = _row(store, store.find_by_incident_id("20260629-PH-EQ").incident_key)
    assert row["priority"] == "MEDIUM"
    assert row["should_report"] == 1

    # Second run must produce no deltas (idempotent + monotonic).
    second = store.reclassify_all(dry_run=False)
    assert second == []


def test_reclassify_all_ignores_already_correct_incidents(store):
    # Group A MEDIUM incident: matrix already reports it (MEDIUM, True).
    store.upsert_incident(
        _record(
            "20260629-PH-EQ",
            country="Philippines",
            priority="MEDIUM",
            severity_level=2,
            should_report=True,
        )
    )
    deltas = store.reclassify_all(dry_run=True)
    assert not any(d["incident_id"] == "20260629-PH-EQ" for d in deltas)


# --------------------------------------------------------------------------- #
# set_digest — pandemic_potential ratchet + event_status (disease track)
# --------------------------------------------------------------------------- #

def test_set_digest_persists_pandemic_potential_and_event_status(store):
    # Disease incident, group C, LOW -> baseline ("LOW", False). AI digest drives
    # the escalation via pandemic_potential=HIGH (the primary disease signal).
    key = store.upsert_incident(
        _record(
            "20260629-DE-EP",
            country="Germany",
            incident_type="Disease",
            priority="LOW",
            severity_level=1,
            should_report=False,
            disease_name="Ebola",
            canonical_name="Initial",
            summary="initial",
        )
    )

    store.set_digest(
        key,
        {
            "canonical_name": "Berlin Ebola Case",
            "summary": "A case was reported.",
            "severity": "LOW",
            "pandemic_potential": "HIGH",
            "event_status": "new_outbreak",
            "search_keys": ["ebola berlin"],
        },
        digested_on=date(2026, 6, 29),
        country="Germany",
    )

    row = _row(store, key)
    assert row["pandemic_potential"] == "HIGH"
    assert row["event_status"] == "new_outbreak"
    assert row["priority"] == "HIGH"
    assert row["should_report"] == 1


def test_set_digest_ratchets_pandemic_potential(store):
    key = store.upsert_incident(
        _record(
            "20260629-DE-EP",
            country="Germany",
            incident_type="Disease",
            priority="LOW",
            severity_level=1,
            should_report=False,
            disease_name="Ebola",
        )
    )

    store.set_digest(
        key,
        {"summary": "s1", "severity": "LOW", "pandemic_potential": "LOW",
         "event_status": "new_outbreak", "search_keys": []},
        digested_on=date(2026, 6, 29),
        country="Germany",
    )
    assert _row(store, key)["pandemic_potential"] == "LOW"

    # Escalate to CRITICAL.
    store.set_digest(
        key,
        {"summary": "s2", "severity": "LOW", "pandemic_potential": "CRITICAL",
         "event_status": "escalating", "search_keys": []},
        digested_on=date(2026, 6, 30),
        country="Germany",
    )
    row = _row(store, key)
    assert row["pandemic_potential"] == "CRITICAL"
    assert row["event_status"] == "escalating"

    # A later lower AI assessment must NOT demote the ratcheted value.
    store.set_digest(
        key,
        {"summary": "s3", "severity": "LOW", "pandemic_potential": "LOW",
         "event_status": "new_outbreak", "search_keys": []},
        digested_on=date(2026, 7, 1),
        country="Germany",
    )
    row = _row(store, key)
    assert row["pandemic_potential"] == "CRITICAL"
    # event_status is refreshable (not ratcheted).
    assert row["event_status"] == "new_outbreak"


def test_set_digest_non_event_status_does_not_clear_should_report(store):
    # set_digest is monotonic: even a non_event status (which classify suppresses)
    # must not clear an already-latched should_report. The one-time destructive
    # reflag is the only place suppression actually clears the flag.
    key = store.upsert_incident(
        _record(
            "20260629-DE-EP",
            country="Germany",
            incident_type="Disease",
            priority="HIGH",
            severity_level=1,
            should_report=True,
            disease_name="Ebola",
        )
    )

    store.set_digest(
        key,
        {"summary": "s", "severity": "LOW", "pandemic_potential": "HIGH",
         "event_status": "non_event", "search_keys": []},
        digested_on=date(2026, 6, 29),
        country="Germany",
    )

    row = _row(store, key)
    # event_status is recorded ...
    assert row["event_status"] == "non_event"
    # ... but should_report is preserved (monotonic set_digest).
    assert row["should_report"] == 1


def test_set_digest_skips_pandemic_potential_for_physical_incidents(store):
    # A physical incident: passing pandemic_potential in the digest must not
    # persist anything to the column (it stays NULL / not-applicable).
    key = store.upsert_incident(
        _record(
            "20260629-DE-EQ",
            country="Germany",
            incident_type="Earthquake",
            priority="LOW",
            severity_level=1,
            should_report=False,
        )
    )
    store.set_digest(
        key,
        {"summary": "s", "severity": "LOW", "pandemic_potential": "HIGH",
         "event_status": "new_outbreak", "search_keys": []},
        digested_on=date(2026, 6, 29),
        country="Germany",
    )
    # The digester won't send these keys for physical track, but if it leaks,
    # set_digest still must not escalate a physical incident on pandemic grounds.
    row = _row(store, key)
    assert row["should_report"] == 0
    assert row["priority"] == "LOW"


def _last_updated_key(store, incident_key: int) -> int:
    with store._engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT last_updated_date_key FROM fact_incident WHERE incident_key = ?",
            (incident_key,),
        ).one()
    return row[0]


def test_set_digest_clamps_endemic_pandemic_potential_to_low(store):
    # COVID-19 is endemic: the AI over-rating pp=CRITICAL must be clamped to LOW
    # on persist (de-escalation), so it never force-reports on pp alone.
    key = store.upsert_incident(
        _record(
            "20260629-DE-EP",
            country="Germany",
            incident_type="Disease",
            priority="LOW",
            severity_level=1,
            should_report=False,
            disease_name="COVID-19",
        )
    )
    store.set_digest(
        key,
        {"summary": "s", "severity": "LOW", "pandemic_potential": "CRITICAL",
         "event_status": "ongoing", "search_keys": []},
        digested_on=date(2026, 6, 29),
        country="Germany",
    )
    row = _row(store, key)
    assert row["pandemic_potential"] == "LOW"
    # Matrix (1,C) = (LOW,False); endemic pp clamped -> no report.
    assert row["should_report"] == 0
    assert row["priority"] == "LOW"


def test_set_digest_leaves_last_updated_date_unchanged(store):
    # Regression guard: set_digest must NOT bump last_updated_date_key. That
    # column reflects real new source/news reporting, not AI re-processing.
    key = store.upsert_incident(_record())
    assert _last_updated_key(store, key) == 20260629

    store.set_digest(
        key,
        {"summary": "fresh summary", "severity": "HIGH", "search_keys": ["k"]},
        digested_on=date(2026, 7, 5),
        country="Philippines",
    )
    # last_updated stays at the original ingest date, NOT the digest date.
    assert _last_updated_key(store, key) == 20260629


def test_find_recent_disease_incident_returns_match_in_window(store):
    key = store.upsert_incident(
        _record(
            "20260610-NG-EP",
            country="Nigeria",
            incident_type="Disease",
            disease_name="Cholera",
            last_updated_date="2026-06-10",
            first_reported_date="2026-06-10",
            event_date="2026-06-10",
        )
    )
    # Within 30 days of 2026-06-29 -> match.
    found = store.find_recent_disease_incident(
        "Cholera", "Nigeria", date(2026, 6, 29), within_days=30
    )
    assert found == key


def test_find_recent_disease_incident_returns_none_outside_window(store):
    store.upsert_incident(
        _record(
            "20260401-NG-EP",
            country="Nigeria",
            incident_type="Disease",
            disease_name="Cholera",
            last_updated_date="2026-04-01",
            first_reported_date="2026-04-01",
            event_date="2026-04-01",
        )
    )
    found = store.find_recent_disease_incident(
        "Cholera", "Nigeria", date(2026, 6, 29), within_days=30
    )
    assert found is None


def test_find_recent_disease_incident_ignores_different_disease(store):
    store.upsert_incident(
        _record(
            "20260610-NG-EP",
            country="Nigeria",
            incident_type="Disease",
            disease_name="Ebola",
            last_updated_date="2026-06-10",
            first_reported_date="2026-06-10",
            event_date="2026-06-10",
        )
    )
    found = store.find_recent_disease_incident(
        "Cholera", "Nigeria", date(2026, 6, 29), within_days=30
    )
    assert found is None


def test_merge_duplicate_disease_incidents_dry_run_writes_nothing(store):
    k1 = store.upsert_incident(
        _record(
            "20260601-NG-EP",
            country="Nigeria",
            incident_type="Disease",
            disease_name="Cholera",
            first_reported_date="2026-06-01",
            event_date="2026-06-01",
            last_updated_date="2026-06-01",
        )
    )
    k2 = store.upsert_incident(
        _record(
            "20260610-NG-EP",
            country="Nigeria",
            incident_type="Disease",
            disease_name="Cholera",
            first_reported_date="2026-06-10",
            event_date="2026-06-10",
            last_updated_date="2026-06-10",
        )
    )
    store.link_news(k1, _article(url="https://n/a"))
    store.link_news(k2, _article(url="https://n/b"))

    deltas = store.merge_duplicate_disease_incidents(dry_run=True)
    assert len(deltas) == 1
    # Dry-run -> nothing merged.
    assert store.count_incidents() == 2


def test_merge_duplicate_disease_incidents_apply_merges_and_is_idempotent(store):
    k1 = store.upsert_incident(
        _record(
            "20260601-NG-EP",
            country="Nigeria",
            incident_type="Disease",
            disease_name="Cholera",
            first_reported_date="2026-06-01",
            event_date="2026-06-01",
            last_updated_date="2026-06-01",
        )
    )
    k2 = store.upsert_incident(
        _record(
            "20260610-NG-EP",
            country="Nigeria",
            incident_type="Disease",
            disease_name="Cholera",
            first_reported_date="2026-06-10",
            event_date="2026-06-10",
            last_updated_date="2026-06-10",
        )
    )
    k3 = store.upsert_incident(
        _record(
            "20260620-NG-EP",
            country="Nigeria",
            incident_type="Disease",
            disease_name="Cholera",
            first_reported_date="2026-06-20",
            event_date="2026-06-20",
            last_updated_date="2026-06-20",
        )
    )
    store.link_news(k1, _article(url="https://n/a"))
    store.link_news(k2, _article(url="https://n/b"))
    store.link_news(k3, _article(url="https://n/c"))

    deltas = store.merge_duplicate_disease_incidents(dry_run=False)
    # k2 and k3 chain into k1 (gaps <= 30) -> 2 merges.
    assert len(deltas) == 2
    # Only the survivor (k1, earliest) remains.
    assert store.count_incidents() == 1
    assert store.find_by_incident_id("20260601-NG-EP") is not None
    # All news re-pointed to the survivor.
    assert len(store.get_incident_news(k1)) == 3

    # Idempotent: a second run produces no deltas.
    again = store.merge_duplicate_disease_incidents(dry_run=False)
    assert again == []
    assert store.count_incidents() == 1


def test_merge_duplicate_disease_incidents_keeps_separate_outbreaks(store):
    # Two Cholera/Nigeria outbreaks >30 days apart must NOT merge.
    store.upsert_incident(
        _record(
            "20260101-NG-EP",
            country="Nigeria",
            incident_type="Disease",
            disease_name="Cholera",
            first_reported_date="2026-01-01",
            event_date="2026-01-01",
            last_updated_date="2026-01-01",
        )
    )
    store.upsert_incident(
        _record(
            "20260615-NG-EP",
            country="Nigeria",
            incident_type="Disease",
            disease_name="Cholera",
            first_reported_date="2026-06-15",
            event_date="2026-06-15",
            last_updated_date="2026-06-15",
        )
    )
    deltas = store.merge_duplicate_disease_incidents(dry_run=False)
    assert deltas == []
    assert store.count_incidents() == 2
