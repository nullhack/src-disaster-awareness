from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("disaster_report.pipeline", reason="pipeline not implemented")
pytest.importorskip("disaster_report.store", reason="store not implemented")
pytest.importorskip("disaster_report.resolver", reason="resolver not implemented")

from disaster_report.config import Config
from disaster_report.deriver import DeriveInput, derive_search_keys
from disaster_report.pipeline import Pipeline
from disaster_report.resolver import IncidentResolver
from disaster_report.sources.base import RawIncident
from disaster_report.store import SqliteIncidentStore
from sqlalchemy import select

from tests.e2e.conftest import FakeDigester, StubNews, StubSource, article, quake


def _store(db_url):
    return SqliteIncidentStore(db_url)


def _dev_key(
    *,
    country="Philippines",
    disaster_type="Earthquake",
    event_date=date(2026, 6, 29),
    place="near Sarangani, Philippines",
):
    """Longest derived search key for a quake - the one _develop tries first.

    set_digest now derives canonical_name/search_keys from the incident's
    structured facts (AI no longer authors them), so StubNews must be keyed on
    the actual derived key instead of an arbitrary FakeDigester return value.
    """
    keys = derive_search_keys(
        DeriveInput(
            incident_type=disaster_type,
            country=country,
            event_date=event_date,
            place=place,
        )
    )
    return max(keys, key=len) if keys else ""


def _dev_key_set(
    *,
    country="Philippines",
    disaster_type="Earthquake",
    event_date=date(2026, 6, 29),
    place="near Sarangani, Philippines",
):
    """Full derived search_keys list (set_digest persists these deterministically)."""
    return derive_search_keys(
        DeriveInput(
            incident_type=disaster_type,
            country=country,
            event_date=event_date,
            place=place,
        )
    )


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


def test_develop_does_not_extend_tracking_window(db_url):
    store = _store(db_url)
    dig = FakeDigester(returns={"search_keys": ["q"]})
    first = StubSource("USGS", [quake(report_date="2026-06-10T00:00:00Z")])

    _pipeline(store, sources=[first], news=StubNews({}), digester=dig, today=date(2026, 6, 10)).run()
    active = store.get_active_incidents(as_of=date(2026, 6, 10), within_days=7)
    assert len(active) == 1

    dev = StubNews({_dev_key(event_date=date(2026, 6, 10)): [article("https://n/2", "2026-06-15T00:00:00Z", "Philippines quake aid")]})
    _pipeline(store, sources=[], news=dev, digester=dig, today=date(2026, 6, 15)).run()
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident.last_updated == date(2026, 6, 10), "_develop must not bump last_updated"
    assert len(store.get_incident_news(incident.incident_key)) >= 1, "news still linked"

    _pipeline(store, sources=[], news=StubNews({}), digester=dig, today=date(2026, 6, 18)).run()
    active = store.get_active_incidents(as_of=date(2026, 6, 18), within_days=7)
    assert len(active) == 0, "8 days after ingest with no bump -> expired naturally"


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


def test_backlog_incident_is_digested_without_news_search(db_url):
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
    assert dig.call_count == 1, "backlog incidents are still AI-digested at ingest"
    assert news.calls == [], "backlog incidents must not trigger any news search"
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident is not None
    assert incident.ai_digest_date_key is not None, "backlog incident must be AI-digested"


def test_inwindow_incident_triggers_bootstrap_news_search(db_url):
    """Incidents whose report_date is within the tracking window (not just today)
    trigger bootstrap news search — fixes the past-dated WHO DON gap where
    publication date < today blocked all news fetching."""
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

    assert dig.call_count == 1, "every new incident is AI-digested at ingest"
    assert len(news.calls) == 1, "in-window (yesterday) incident must trigger bootstrap search"
    assert news.calls[0][0] == "2026-06-28 Earthquake Philippines"
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident.ai_digest_date_key is not None, "yesterday incident must be AI-digested"


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
    assert dig.call_count == 1, "backlog incident is still AI-digested at ingest"
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


def test_ai_disease_label_used_when_adapter_label_empty(db_url):
    """When the source adapter provides no disease (brittle title parse failed),
    the AI's disease_name from the digest is authoritative and must populate
    disease_key."""
    store = _store(db_url)
    dig = FakeDigester(returns={"disease_name": "Ebola"})
    # Simulates a WHO title whose separator the adapter failed to split.
    unlabeled = RawIncident(
        source_name="WHO",
        incident_name="Ebola disease caused by Bundibugyo virus",
        country="Uganda",
        disaster_type="Disease",
        report_date="2026-06-29T00:00:00Z",
        source_url="https://who/ebola-bundi",
        raw_fields={"event_id": "who-ebola-bundi", "disease": ""},
    )

    _pipeline(
        store,
        sources=[StubSource("WHO", [unlabeled])],
        news=StubNews({}),
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    with store._session() as session:
        from sqlalchemy import select as _sel
        from disaster_report.models import DimDisease, FactIncident
        disease = session.execute(
            _sel(DimDisease).where(DimDisease.disease_name == "Ebola")
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

    dev = StubNews({_dev_key(event_date=date(2026, 6, 28)): [
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
    assert incident.last_updated == date(2026, 6, 28), "_develop no longer bumps last_updated"


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
    _k = _dev_key(event_date=date(2026, 6, 29))
    dev = StubNews({
        _k: [
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
        "dev-search must fire once for the derived search_key (bootstrap doesn't use search_keys)"
    )
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident.last_updated == date(2026, 6, 29)


def test_develop_re_digest_passes_incident_identity_in_source_reports(db_url):
    store = _store(db_url)
    dig = FakeDigester(queue=[
        {"canonical_name": "Afghanistan Earthquake", "summary": "initial", "severity": "LOW", "search_keys": ["k"]},
        {"canonical_name": "Afghanistan Earthquake", "summary": "still afghanistan", "severity": "LOW", "search_keys": ["k"]},
    ])
    _k = _dev_key(country="Afghanistan", event_date=date(2026, 6, 29))
    dev = StubNews({_k: [
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
    # canonical_name is now DERIVED (not AI-authored) -> "{Type} {place} {Month YYYY}".
    assert identity["incident_name"] == "Earthquake Sarangani June 2026"
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


def test_digest_failure_persists_incident_and_news_degraded(db_url):
    store = _store(db_url)
    dig = FakeDigester(raises=RuntimeError("all 3 models failed; last=429 rate-limited"))
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

    assert store.count_incidents() == 1, "incident must be persisted even when digest fails"
    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident is not None
    assert incident.ai_digest_date_key is None, "degraded incident has no digest"
    assert incident.summary == ""
    linked = store.get_incident_news(incident.incident_key)
    assert len(linked) == 1 and linked[0].url == "https://n/1", (
        "bootstrap news must be persisted before the digest is attempted"
    )


def test_digest_failure_does_not_abort_other_incidents(db_url):
    store = _store(db_url)
    a = quake(name="Quake A", country="Indonesia", source="USGS")
    b = RawIncident("WHO", "Cholera Outbreak", "Nigeria", "Disease", "2026-06-29T00:00:00Z", "u", {})
    dig = FakeDigester(raises=RuntimeError("429"))

    _pipeline(
        store,
        sources=[StubSource("Feed", [a, b])],
        news=StubNews({}),
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    assert store.count_incidents() == 2, "both incidents persisted despite digest failures"


def test_degraded_incident_is_re_digested_on_next_run(db_url):
    store = _store(db_url)
    dig = FakeDigester(raises=RuntimeError("429"))
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
    assert incident.ai_digest_date_key is None

    dig.raises = None
    dig.returns = {
        "canonical_name": "Sarangani Quake",
        "summary": "A quake struck Sarangani.",
        "severity": "LOW",
        "search_keys": ["k"],
    }
    _pipeline(
        store,
        sources=[],
        news=StubNews({}),
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident.ai_digest_date_key is not None, "retry pass must complete the pending digest"
    assert incident.summary == "A quake struck Sarangani."
    assert incident.search_keys == _dev_key_set(event_date=date(2026, 6, 29))


def test_non_event_disease_incident_drops_news_but_keeps_row(db_url):
    """AI-as-judge: a non_event disease verdict drops candidate news while the
    incident row is kept (suppressed, should_report=False)."""
    store = _store(db_url)
    dig = FakeDigester(returns={
        "canonical_name": "Cholera Outbreak Nigeria",
        "summary": "A cholera outbreak was reported in Nigeria.",
        "severity": "MEDIUM",
        "pandemic_potential": "NONE",
        "event_status": "non_event",
        "search_keys": ["k"],
    })
    cholera = RawIncident(
        source_name="WHO",
        incident_name="Cholera Outbreak Nigeria",
        country="Nigeria",
        disaster_type="Disease",
        report_date="2026-06-29T00:00:00Z",
        source_url="https://who/cholera",
        raw_fields={"event_id": "who-cholera", "disease": "Cholera"},
    )
    bootstrap_query = "2026-06-29 Disease Nigeria"
    news = StubNews({
        bootstrap_query: [
            article("https://n/1", "2026-06-29T08:00:00Z", "Nigeria cholera outbreak cases rise"),
        ]
    })

    _pipeline(
        store,
        sources=[StubSource("WHO", [cholera])],
        news=news,
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert incident is not None, "incident row must be kept even when non_event"
    assert store.get_incident_news(incident.incident_key) == [], (
        "candidate news must be dropped for a non_event verdict"
    )
    with store._session() as session:
        from disaster_report.models import FactIncident
        row = session.execute(select(FactIncident)).scalar_one()
        assert row.should_report is False, "non_event must be suppressed"
        assert (row.event_status or "") == "non_event"


def test_real_disease_incident_links_news_and_reports(db_url):
    """A new_outbreak + HIGH pandemic_potential verdict keeps the news linked and
    the incident reporting."""
    store = _store(db_url)
    dig = FakeDigester(returns={
        "canonical_name": "Ebola Outbreak Uganda",
        "summary": "A new Ebola outbreak was reported in Uganda.",
        "severity": "HIGH",
        "pandemic_potential": "HIGH",
        "event_status": "new_outbreak",
        "search_keys": ["k"],
    })
    ebola = RawIncident(
        source_name="WHO",
        incident_name="Ebola Outbreak Uganda",
        country="Uganda",
        disaster_type="Disease",
        report_date="2026-06-29T00:00:00Z",
        source_url="https://who/ebola",
        raw_fields={"event_id": "who-ebola", "disease": "Ebola"},
    )
    bootstrap_query = "2026-06-29 Disease Uganda"
    news = StubNews({
        bootstrap_query: [
            article("https://n/1", "2026-06-29T08:00:00Z", "Uganda ebola outbreak cases"),
        ]
    })

    _pipeline(
        store,
        sources=[StubSource("WHO", [ebola])],
        news=news,
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    linked = store.get_incident_news(incident.incident_key)
    assert len(linked) == 1 and linked[0].url == "https://n/1", (
        "real-outbreak news must be linked"
    )
    with store._session() as session:
        from disaster_report.models import FactIncident
        row = session.execute(select(FactIncident)).scalar_one()
        assert row.should_report is True


def test_elimination_declared_disease_incident_drops_news(db_url):
    """An elimination_declared verdict (e.g. polio-free milestone) drops news too."""
    store = _store(db_url)
    dig = FakeDigester(returns={
        "canonical_name": "Polio-free Declaration",
        "summary": "An area was declared polio-free.",
        "severity": "LOW",
        "pandemic_potential": "NONE",
        "event_status": "elimination_declared",
        "search_keys": ["k"],
    })
    polio = RawIncident(
        source_name="WHO",
        incident_name="Polio-free Declaration",
        country="Nigeria",
        disaster_type="Disease",
        report_date="2026-06-29T00:00:00Z",
        source_url="https://who/polio",
        raw_fields={"event_id": "who-polio", "disease": "Polio"},
    )
    bootstrap_query = "2026-06-29 Disease Nigeria"
    news = StubNews({
        bootstrap_query: [
            article("https://n/1", "2026-06-29T08:00:00Z", "Nigeria polio-free milestone declared"),
        ]
    })

    _pipeline(
        store,
        sources=[StubSource("WHO", [polio])],
        news=news,
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    incident = store.find_by_incident_id(store.all_incident_ids()[0])
    assert store.get_incident_news(incident.incident_key) == [], (
        "elimination_declared news must be dropped"
    )


def test_retry_pass_skips_backlog_incidents(db_url):
    store = _store(db_url)
    dig = FakeDigester()
    backlog = quake(report_date="2026-06-01T00:00:00Z")
    _pipeline(
        store,
        sources=[StubSource("USGS", [backlog])],
        news=StubNews({}),
        digester=dig,
        today=date(2026, 6, 29),
    ).run()
    assert dig.call_count == 1, "ingest digests every new incident, including backlog"

    _pipeline(
        store,
        sources=[],
        news=StubNews({}),
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    assert dig.call_count == 1, "retry pass must not re-digest already-digested backlog incidents"


def test_disease_re_report_merges_into_existing_incident(db_url):
    """A recurring re-report of a recent (disease, country) outbreak merges into
    the existing incident instead of creating a new row."""
    from disaster_report.store import IncidentRecord

    store = _store(db_url)
    # Seed an existing Cholera/Nigeria outbreak updated recently (in-window).
    seed_key = store.upsert_incident(
        IncidentRecord(
            incident_id="20260620-NG-EP",
            canonical_name="Cholera Outbreak Nigeria",
            summary="existing",
            country="Nigeria",
            incident_type="Disease",
            priority="MEDIUM",
            severity_level=2,
            event_date="2026-06-20",
            first_reported_date="2026-06-20",
            last_updated_date="2026-06-20",
            should_report=True,
            search_keys=["k"],
            disease="Cholera",
        )
    )
    dig = FakeDigester(returns={
        "canonical_name": "Cholera Outbreak Nigeria",
        "summary": "updated re-report",
        "severity": "MEDIUM",
        "pandemic_potential": "MEDIUM",
        "event_status": "ongoing",
        "search_keys": ["k"],
    })
    # New re-report of the SAME disease+country, dated today.
    cholera = RawIncident(
        source_name="WHO",
        incident_name="Cholera Outbreak Nigeria",
        country="Nigeria",
        disaster_type="Disease",
        report_date="2026-06-29T00:00:00Z",
        source_url="https://who/cholera-repeat",
        raw_fields={"event_id": "who-cholera-2", "disease": "Cholera"},
    )
    news = StubNews({
        "2026-06-29 Disease Nigeria": [
            article("https://n/new", "2026-06-29T08:00:00Z", "Nigeria cholera outbreak cases"),
        ]
    })

    _pipeline(
        store,
        sources=[StubSource("WHO", [cholera])],
        news=news,
        digester=dig,
        today=date(2026, 6, 29),
    ).run()

    # No new incident row — the re-report merged into the seed.
    assert store.count_incidents() == 1
    assert store.all_incident_ids() == ["20260620-NG-EP"]
    # The seed incident absorbed the new source + news.
    assert store.get_incident_news(seed_key) != []
    # last_updated bumped to today (a real new source arrived).
    with store._session() as session:
        from disaster_report.models import FactIncident
        row = session.execute(select(FactIncident)).scalar_one()
        assert row.last_updated_date_key == 20260629
        assert row.summary == "updated re-report"


def test_backdated_disease_re_report_merges_without_bumping_last_updated(db_url):
    """A backdated re-report (report_date < today) merges into the survivor and
    links its source, but does NOT bump last_updated — Edit 2/A: only today's
    re-reports keep the survivor alive, so old re-issues can age out."""
    from disaster_report.store import IncidentRecord

    store = _store(db_url)
    seed_key = store.upsert_incident(
        IncidentRecord(
            incident_id="20260620-NG-EP",
            canonical_name="Cholera Outbreak Nigeria",
            summary="existing",
            country="Nigeria",
            incident_type="Disease",
            priority="MEDIUM",
            severity_level=2,
            event_date="2026-06-20",
            first_reported_date="2026-06-20",
            last_updated_date="2026-06-20",
            should_report=True,
            search_keys=["k"],
            disease="Cholera",
        )
    )
    cholera = RawIncident(
        source_name="WHO",
        incident_name="Cholera Outbreak Nigeria",
        country="Nigeria",
        disaster_type="Disease",
        report_date="2026-06-25T00:00:00Z",  # backdated, NOT today
        source_url="https://who/cholera-backdated",
        raw_fields={"event_id": "who-cholera-back", "disease": "Cholera"},
    )

    _pipeline(
        store,
        sources=[StubSource("WHO", [cholera])],
        news=StubNews({}),
        digester=FakeDigester(),
        today=date(2026, 6, 29),
    ).run()

    assert store.count_incidents() == 1
    assert store.all_incident_ids() == ["20260620-NG-EP"]
    with store._session() as session:
        from disaster_report.models import FactIncident

        row = session.execute(select(FactIncident)).scalar_one()
        assert row.last_updated_date_key == 20260620  # UNCHANGED — no bump for backdated
    # backdated -> is_today=False -> no news fetched
    assert store.get_incident_news(seed_key) == []


def test_develop_skips_suppressed_incidents(db_url):
    """_develop only follows up on should_report=1 incidents — a suppressed
    incident gets no news search (Edit 1/B)."""
    from disaster_report.store import IncidentRecord

    store = _store(db_url)
    store.upsert_incident(
        IncidentRecord(
            incident_id="20260628-PH-EQ",
            canonical_name="Philippines Quake",
            summary="minor",
            country="Philippines",
            incident_type="Earthquake",
            priority="LOW",
            severity_level=1,
            event_date="2026-06-28",
            first_reported_date="2026-06-28",
            last_updated_date="2026-06-28",
            should_report=False,
            search_keys=["Philippines quake casualties"],
        )
    )
    news = StubNews(
        {
            "Philippines quake casualties": [
                article("https://n/1", "2026-06-29T00:00:00Z", "Philippines quake aid"),
            ]
        }
    )
    _pipeline(
        store,
        sources=[],
        news=news,
        digester=FakeDigester(),
        today=date(2026, 6, 29),
    ).run()

    assert news.calls == []  # suppressed -> excluded from _develop


def test_develop_searches_longest_key_first_and_stops_at_first_hit(db_url):
    """_develop tries search_keys longest-first and stops at the first one that
    yields relevant articles — NOT one search per key (Edit 4/D)."""
    from disaster_report.store import IncidentRecord

    store = _store(db_url)
    long_key = "longest impact key phrase philippines"
    short_key = "short"
    store.upsert_incident(
        IncidentRecord(
            incident_id="20260628-PH-EQ",
            canonical_name="Philippines Quake",
            summary="minor",
            country="Philippines",
            incident_type="Earthquake",
            priority="MEDIUM",
            severity_level=2,
            event_date="2026-06-28",
            first_reported_date="2026-06-28",
            last_updated_date="2026-06-28",
            should_report=True,
            search_keys=[short_key, long_key],
        )
    )
    news = StubNews(
        {
            long_key: [
                article("https://n/1", "2026-06-29T00:00:00Z", "Philippines quake aid"),
            ]
        }
    )
    _pipeline(
        store,
        sources=[],
        news=news,
        digester=FakeDigester(),
        today=date(2026, 6, 29),
    ).run()

    # Only the longest key was tried (and it hit), so the short key was never searched.
    assert [c[0] for c in news.calls] == [long_key]
