from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("disaster_report.pipeline", reason="pipeline not implemented")
pytest.importorskip("disaster_report.store", reason="store not implemented")
pytest.importorskip("disaster_report.resolver", reason="resolver not implemented")

from disaster_report.config import Config
from disaster_report.pipeline import Pipeline
from disaster_report.resolver import IncidentResolver
from disaster_report.sources.base import RawIncident
from disaster_report.store import SqliteIncidentStore
from sqlalchemy import select

from tests.e2e.conftest import FakeDigester, StubNews, StubSource, article, quake


def _store(db_url):
    return SqliteIncidentStore(db_url)


def _pipeline(store, *, sources, news, digester, today, window_days=7):
    return Pipeline(
        sources=sources,
        news=news,
        resolver=IncidentResolver(),
        digester=digester,
        store=store,
        config=Config(tracking_window_days=window_days),
        clock=lambda: today,
    )


def test_new_incidents_are_persisted_and_duplicates_collapsed(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    src = StubSource("USGS", [quake(), quake()])

    _pipeline(store, sources=[src], news=StubNews({}), digester=dig, today=date(2026, 6, 29)).run()

    assert store.count_incidents() == 1
    assert dig.call_count == 1


def test_same_incident_from_two_sources_resolves_to_one(db_url):
    store = _store(db_url)
    usgs = quake(source="USGS")
    gdacs = RawIncident(
        source_name="GDACS",
        incident_name=usgs.incident_name,
        country=usgs.country,
        disaster_type=usgs.disaster_type,
        report_date=usgs.report_date,
        source_url="https://gdacs.example/x",
        raw_fields={},
    )
    dig = FakeDigester()

    _pipeline(
        store,
        sources=[StubSource("USGS", [usgs]), StubSource("GDACS", [gdacs])],
        news=StubNews({}),
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    assert store.count_incidents() == 1
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert len(store.get_incident_sources(incident.incident_key)) == 2
    assert dig.call_count == 1


def test_ai_digest_called_once_per_unique_incident(db_url):
    store = _store(db_url)
    a = quake(name="Quake A", country="Indonesia", source="USGS")
    b = RawIncident("WHO", "Cholera Outbreak", "Nigeria", "Disease", "2026-06-29T00:00:00Z", "u", {})
    dig = FakeDigester()

    _pipeline(
        store,
        sources=[StubSource("Feed", [a, b])],
        news=StubNews({}),
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    assert store.count_incidents() == 2
    assert dig.call_count == 2


def test_new_incident_bootstrap_news_is_linked_and_fed_to_digester(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    bootstrap_query = "2026-06-29 Earthquake Philippines"
    news = StubNews(
        {bootstrap_query: [article("https://n/1", "2026-06-29T08:00:00Z", "Magnitude 6 quake strikes Philippines")]}
    )

    _pipeline(
        store,
        sources=[StubSource("USGS", [quake()])],
        news=news,
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    linked = store.get_incident_news(incident.incident_key)
    assert len(linked) == 1
    assert linked[0].url == "https://n/1"

    assert dig.call_count == 1
    fed = dig.calls[0]
    materials = fed if isinstance(fed, list) else [fed]
    assert any("https://n/1" in str(m) for m in materials), (
        "bootstrap news must be fed into the AI digest"
    )


def test_filter_rejects_irrelevant_bootstrap_news(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    bootstrap_query = "2026-06-29 Earthquake Philippines"
    news = StubNews({
        bootstrap_query: [
            article("https://rel/1", "2026-06-29T08:00:00Z", "Magnitude 6 quake strikes Philippines"),
            article("https://spam/1", "2026-06-29T09:00:00Z", "NUDE NATIVE AMERICAN GIRLS PORN"),
            article("https://spam/2", "2026-06-29T10:00:00Z", "Venezuela earthquake rubble"),
            article("https://spam/3", "2026-06-29T11:00:00Z", "Knicks beat Celtics in basketball"),
        ]
    })

    _pipeline(
        store,
        sources=[StubSource("USGS", [quake()])],
        news=news,
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    linked = store.get_incident_news(incident.incident_key)
    assert {a.url for a in linked} == {"https://rel/1"}, (
        "only the article mentioning earthquake+Philippines must be linked"
    )


def test_development_within_window_extends_tracking(db_url):
    store = _store(db_url)
    dig = FakeDigester(returns={"search_keys": ["q"]})
    first = StubSource("USGS", [quake(report_date="2026-06-10T00:00:00Z")])

    _pipeline(store, sources=[first], news=StubNews({}), digester=dig, today=date(2026, 6, 10)).run()
    active = store.get_active_incidents(as_of=date(2026, 6, 10), within_days=7)
    assert len(active) == 1

    dev = StubNews({"q": [article("https://n/2", "2026-06-15T00:00:00Z", "Philippines quake aid")]})
    _pipeline(store, sources=[], news=dev, digester=dig, today=date(2026, 6, 15)).run()
    active = store.get_active_incidents(as_of=date(2026, 6, 15), within_days=7)
    assert len(active) == 1
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident.last_updated >= date(2026, 6, 15)

    _pipeline(store, sources=[], news=StubNews({}), digester=dig, today=date(2026, 6, 20)).run()
    active = store.get_active_incidents(as_of=date(2026, 6, 20), within_days=7)
    assert len(active) == 1, "bumped on 6/15 still within 7d window from 6/20"

    _pipeline(store, sources=[], news=StubNews({}), digester=dig, today=date(2026, 6, 23)).run()
    active = store.get_active_incidents(as_of=date(2026, 6, 23), within_days=7)
    assert len(active) == 0, "8 days after last bump on 6/15 -> expired"


def test_no_development_beyond_window_expires_from_active(db_url):
    store = _store(db_url)
    dig = FakeDigester(returns={"search_keys": ["q"]})
    first = StubSource("USGS", [quake(report_date="2026-06-10T00:00:00Z")])

    _pipeline(store, sources=[first], news=StubNews({}), digester=dig, today=date(2026, 6, 10)).run()
    active = store.get_active_incidents(as_of=date(2026, 6, 10), within_days=7)
    assert len(active) == 1

    _pipeline(store, sources=[], news=StubNews({}), digester=dig, today=date(2026, 6, 18)).run()
    active = store.get_active_incidents(as_of=date(2026, 6, 18), within_days=7)
    assert len(active) == 0, "8 days after last_updated -> expired"


def test_re_running_ingest_is_idempotent(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    src = StubSource("USGS", [quake()])

    _pipeline(store, sources=[src], news=StubNews({}), digester=dig, today=date(2026, 6, 29)).run()
    first_count = store.count_incidents()
    first_digests = dig.call_count

    _pipeline(store, sources=[src], news=StubNews({}), digester=dig, today=date(2026, 6, 29)).run()

    assert store.count_incidents() == first_count
    assert dig.call_count == first_digests


def test_backlog_incident_is_persisted_but_not_digested(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    backlog = quake(report_date="2026-06-01T00:00:00Z")
    news = StubNews({})

    _pipeline(
        store,
        sources=[StubSource("USGS", [backlog])],
        news=news,
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    assert store.count_incidents() == 1
    assert dig.call_count == 0
    assert news.calls == []
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident is not None
    assert incident.search_keys == []


def test_yesterday_incident_is_persisted_but_not_digested(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    yesterday = quake(report_date="2026-06-28T00:00:00Z")
    news = StubNews({"2026-06-28 Earthquake Philippines": [article("https://n/y", "2026-06-28T08:00:00Z")]})

    _pipeline(
        store,
        sources=[StubSource("USGS", [yesterday])],
        news=news,
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    assert dig.call_count == 0, "only today's incidents are AI-digested; yesterday is backlog"
    assert news.calls == [], "yesterday's incident must not trigger any news search"
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident.search_keys == []


def test_news_search_receives_timelimit_derived_from_window(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    news = StubNews({})

    _pipeline(
        store,
        sources=[StubSource("USGS", [quake()])],
        news=news,
        digester=dig,
        today=date(2026, 6, 29),
        window_days=7,
    ).run()

    assert news.calls, "bootstrap search must have been invoked"
    _, timelimit = news.calls[0]
    assert timelimit == "w"


def test_news_search_skipped_entirely_for_backlog_incident(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    backlog = quake(report_date="2020-01-01T00:00:00Z")
    news = StubNews({"2020-01-01 Earthquake Philippines": [article("https://old/1", "2020-01-01T08:00:00Z")]})

    _pipeline(
        store,
        sources=[StubSource("USGS", [backlog])],
        news=news,
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    assert news.calls == [], "backlog incident must not trigger any news search"
    assert dig.call_count == 0
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert store.get_incident_news(incident.incident_key) == []


def test_low_severity_group_C_incident_is_persisted_with_should_report_false(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    germany_quake = RawIncident(
        source_name="USGS",
        incident_name="M2.5 quake Germany",
        country="Germany",
        disaster_type="Earthquake",
        report_date="2026-06-29T00:00:00Z",
        source_url="https://u/de",
        raw_fields={"event_id": "de1"},
    )

    _pipeline(
        store,
        sources=[StubSource("USGS", [germany_quake])],
        news=StubNews({}),
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    with store._session() as session:
        from disaster_report.models import FactIncident
        row = session.execute(select(FactIncident)).scalar_one()
        assert row.should_report is False
        assert row.priority_key is not None


def test_disease_name_flows_to_dim_disease_for_disease_incidents(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    marburg = RawIncident(
        source_name="WHO",
        incident_name="Marburg virus disease - Tanzania",
        country="Tanzania",
        disaster_type="Disease",
        report_date="2026-06-29T00:00:00Z",
        source_url="https://who/marburg",
        raw_fields={"event_id": "who-marburg", "disease": "Marburg virus disease"},
    )

    _pipeline(
        store,
        sources=[StubSource("WHO", [marburg])],
        news=StubNews({}),
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    with store._session() as session:
        from sqlalchemy import select as _sel
        from disaster_report.models import DimDisease, FactIncident
        disease = session.execute(
            _sel(DimDisease).where(DimDisease.disease_name == "Marburg virus disease")
        ).scalar_one()
        incident = session.execute(_sel(FactIncident)).scalar_one()
        assert incident.disease_key == disease.disease_key


def test_develop_re_digests_when_threshold_new_articles_arrive(db_url):
    store = _store(db_url)
    dig = FakeDigester(
        returns={"search_keys": ["k"], "summary": "initial", "severity": "LOW"}
    )
    first = StubSource("USGS", [quake(report_date="2026-06-28T00:00:00Z")])
    _pipeline(store, sources=[first], news=StubNews({}), digester=dig, today=date(2026, 6, 28)).run()
    assert dig.call_count == 1

    dev = StubNews({"k": [
        article("https://n/2", "2026-06-29T08:00:00Z", "Philippines quake casualties"),
        article("https://n/3", "2026-06-29T09:00:00Z", "Philippines quake shelter"),
        article("https://n/4", "2026-06-29T10:00:00Z", "Philippines quake damage"),
    ]})
    pipeline = Pipeline(
        sources=[],
        news=dev,
        resolver=IncidentResolver(),
        digester=dig,
        store=store,
        config=Config(tracking_window_days=7, develop_re_digest_threshold=3),
        clock=lambda: date(2026, 6, 29),
    )
    pipeline.run()

    assert dig.call_count == 2, "re-digest must fire after >=3 new articles"
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident.last_updated == date(2026, 6, 29)


def test_develop_does_not_re_digest_below_threshold(db_url):
    store = _store(db_url)
    dig = FakeDigester(returns={"search_keys": ["k"]})
    _pipeline(store, sources=[StubSource("USGS", [quake(report_date="2026-06-28T00:00:00Z")])], news=StubNews({}), digester=dig, today=date(2026, 6, 28)).run()

    dev = StubNews({"k": [article("https://n/2", "2026-06-29T08:00:00Z")]})
    Pipeline(
        sources=[],
        news=dev,
        resolver=IncidentResolver(),
        digester=dig,
        store=store,
        config=Config(tracking_window_days=7, develop_re_digest_threshold=3),
        clock=lambda: date(2026, 6, 29),
    ).run()

    assert dig.call_count == 1, "below threshold: no re-digest"


def test_newly_enriched_incident_gets_dev_searched_in_same_run(db_url):
    store = _store(db_url)
    dig = FakeDigester(returns={"search_keys": ["k1"], "summary": "init", "severity": "LOW"})
    dev = StubNews({
        "k1": [
            article("https://n/1", "2026-06-29T08:00:00Z", "Philippines quake death toll rises"),
            article("https://n/2", "2026-06-29T09:00:00Z", "Philippines quake shelter update"),
            article("https://n/3", "2026-06-29T10:00:00Z", "Philippines quake damage report"),
        ],
    })
    pipeline = Pipeline(
        sources=[StubSource("USGS", [quake()])],
        news=dev,
        resolver=IncidentResolver(),
        digester=dig,
        store=store,
        config=Config(tracking_window_days=7, develop_re_digest_threshold=3),
        clock=lambda: date(2026, 6, 29),
    )
    pipeline.run()

    assert dig.call_count == 2, (
        "newly-enriched incident must be dev-searched in the same run; "
        "call #1=initial digest, call #2=re-digest after 3 new articles"
    )
    assert len(dev.calls) == 2, (
        "dev-search must fire once for the search_key 'k1' (bootstrap doesn't use search_keys)"
    )
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident.last_updated == date(2026, 6, 29)


def test_develop_re_digest_passes_incident_identity_in_source_reports(db_url):
    store = _store(db_url)
    dig = FakeDigester(queue=[
        {"canonical_name": "Afghanistan Earthquake", "summary": "initial", "severity": "LOW", "search_keys": ["k"]},
        {"canonical_name": "Afghanistan Earthquake", "summary": "still afghanistan", "severity": "LOW", "search_keys": ["k"]},
    ])
    dev = StubNews({"k": [
        article("https://n/1", "2026-06-29T08:00:00Z", "Afghanistan quake Jurm deaths"),
        article("https://n/2", "2026-06-29T09:00:00Z", "Afghanistan quake shelter"),
        article("https://n/3", "2026-06-29T10:00:00Z", "Afghanistan quake damage"),
    ]})
    pipeline = Pipeline(
        sources=[StubSource("USGS", [quake(country="Afghanistan", name="Jurm earthquake")])],
        news=dev,
        resolver=IncidentResolver(),
        digester=dig,
        store=store,
        config=Config(tracking_window_days=7, develop_re_digest_threshold=3),
        clock=lambda: date(2026, 6, 29),
    )
    pipeline.run()

    assert dig.call_count == 2
    second_call = dig.calls[1]
    assert isinstance(second_call, dict)
    assert "source_reports" in second_call
    identity = second_call["source_reports"][0]
    assert identity["source_name"] == "PRIOR_DIGEST"
    assert identity["incident_name"] == "Afghanistan Earthquake"
    assert identity["country"] == "Afghanistan"
    assert identity["disaster_type"] == "Earthquake"
    assert identity["raw_fields"]["prior_summary"] == "initial"
    assert len(second_call["news_articles"]) == 3


def test_develop_skips_incidents_outside_window(db_url):
    store = _store(db_url)
    dig = FakeDigester(returns={"search_keys": ["q"]})
    backlog = quake(report_date="2026-06-01T00:00:00Z")
    _pipeline(
        store,
        sources=[StubSource("USGS", [backlog])],
        news=StubNews({}),
        digester=dig,
        today=date(2026, 6, 2),
    ).run()

    dev = StubNews({"q": [article("https://n/1", "2026-06-30T08:00:00Z", "Philippines quake aid")]})
    Pipeline(
        sources=[],
        news=dev,
        resolver=IncidentResolver(),
        digester=dig,
        store=store,
        config=Config(tracking_window_days=7),
        clock=lambda: date(2026, 6, 30),
    ).run()

    assert dev.calls == [], "incident outside window must not be dev-searched"
