from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from disaster_report.models import (
    IncidentLog,
    NewsItem,
    ReportPlace,
    SourceReport,
)
from disaster_report.store._tree import (
    incident_dir,
    incident_news_path,
    log_news_path,
    log_path,
    news_staging_path,
    report_staging_path,
    report_uuid,
)
from disaster_report.store.content import ContentStore

FIXED_NOW = datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc)
WINDOW = 7


def _clock() -> datetime:
    return FIXED_NOW


def _build_report(
    *,
    source: str = "USGS",
    source_id: str = "us6000test",
    incident_type: str = "Earthquake",
    name: str = "M 5.0 - Test",
    places: list[ReportPlace] | None = None,
    report_date: str = "2026-07-01",
    raw_fields: dict[str, object] | None = None,
) -> SourceReport:
    return SourceReport(
        source=source,
        source_id=source_id,
        incident_type=incident_type,
        name=name,
        places=places if places is not None else [],
        report_date=report_date,
        raw_fields=raw_fields if raw_fields is not None else {},
    )


def _build_news(
    *,
    url: str = "https://example.com/news",
    title: str = "Test News",
    body: str = "Test body",
    published_date: str = "2026-07-02T10:00:00Z",
    source: str = "ddg",
    domain: str = "example.com",
    image: str = "",
) -> NewsItem:
    return NewsItem(
        url=url,
        title=title,
        body=body,
        published_date=published_date,
        source=source,
        domain=domain,
        image=image,
    )


def _build_log(
    *,
    incident_id: str,
    log_date: str = "2026-07-03",
    summary: str = "new developments",
) -> IncidentLog:
    return IncidentLog(incident_id=incident_id, log_date=log_date, summary=summary)


def _new_incident_id() -> str:
    return uuid.uuid4().hex


class TestReportIngest:
    def test_ingest_returns_deterministic_id_from_natural_key(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        report = _build_report()
        rid = store.ingest_source_report(report)
        assert rid == report_uuid(report.source, report.source_id)

    def test_re_ingest_same_natural_key_is_idempotent(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        report = _build_report()
        rid1 = store.ingest_source_report(report)
        rid2 = store.ingest_source_report(report)
        assert rid1 == rid2
        assert len(store.read_source_reports()) == 1

    def test_two_sources_same_internal_id_stay_distinct(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        store.ingest_source_report(_build_report(source="USGS", source_id="abc"))
        store.ingest_source_report(_build_report(source="GDACS", source_id="abc"))
        assert len(store.read_source_reports()) == 2

    def test_report_file_lands_in_source_partition_staging(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        report = _build_report(source="USGS", source_id="us6001")
        rid = store.ingest_source_report(report)
        expected = report_staging_path(tmp_path, "USGS", rid)
        assert expected.exists()

    def test_read_source_report_keys_returns_colon_natural_keys(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        store.ingest_source_report(_build_report(source="USGS", source_id="us6001"))
        keys = store.read_source_report_keys()
        assert "USGS:us6001" in keys


class TestReportPlaces:
    def test_ingest_and_read_places(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(_build_report())
        places = [ReportPlace(country_code="VE", subdivision="Yaracuy", locality="Yumare")]
        store.ingest_report_places(rid, places)
        result = store.read_report_places(rid)
        assert len(result) == 1
        assert result[0].country_code == "VE"

    def test_duplicate_place_ingest_is_idempotent(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(_build_report())
        place = ReportPlace(country_code="VE", subdivision="", locality="")
        store.ingest_report_places(rid, [place])
        store.ingest_report_places(rid, [place])
        assert len(store.read_report_places(rid)) == 1

    def test_places_survive_report_move_to_incident(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(_build_report())
        store.ingest_report_places(rid, [ReportPlace(country_code="VE", subdivision="", locality="")])
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        assert len(store.read_report_places(rid)) == 1


class TestNewsIngest:
    def test_ingest_returns_deterministic_id_from_url(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        news = _build_news()
        nid = store.ingest_news_item(news)
        from disaster_report.store._tree import news_uuid
        assert nid == news_uuid(news.url)

    def test_re_ingest_same_url_is_idempotent(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        news = _build_news()
        nid1 = store.ingest_news_item(news)
        nid2 = store.ingest_news_item(news)
        assert nid1 == nid2

    def test_news_file_lands_in_staging(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        news = _build_news(url="https://example.com/a")
        nid = store.ingest_news_item(news)
        assert news_staging_path(tmp_path, nid).exists()


class TestNewsIncidentLink:
    def test_assign_moves_news_to_incident_dir(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        nid = store.ingest_news_item(_build_news())
        inc = _new_incident_id()
        store.assign_news_to_incident(nid, inc)
        assert incident_news_path(tmp_path, inc, nid).exists()
        assert not news_staging_path(tmp_path, nid).exists()

    def test_read_incident_for_news(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        nid = store.ingest_news_item(_build_news())
        assert store.read_incident_for_news(nid) is None
        inc = _new_incident_id()
        store.assign_news_to_incident(nid, inc)
        assert store.read_incident_for_news(nid) == inc

    def test_reassign_pending_news_moves_between_incidents(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        nid = store.ingest_news_item(_build_news())
        inc_a = _new_incident_id()
        inc_b = _new_incident_id()
        store.assign_news_to_incident(nid, inc_a)
        store.assign_news_to_incident(nid, inc_b)
        assert incident_news_path(tmp_path, inc_b, nid).exists()
        assert not incident_news_path(tmp_path, inc_a, nid).exists()
        assert store.read_incident_for_news(nid) == inc_b

    def test_assign_refuses_summarized_news(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path, clock=_clock)
        nid = store.ingest_news_item(_build_news())
        inc = _new_incident_id()
        store.assign_news_to_incident(nid, inc)
        store.append_timeline_with_provenance(
            _build_log(incident_id=inc), {nid}
        )
        other = _new_incident_id()
        store.assign_news_to_incident(nid, other)
        assert store.read_incident_for_news(nid) == inc


class TestReportIncidentLink:
    def test_link_moves_report_to_incident_dir(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(_build_report())
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        assert (incident_dir(tmp_path, inc) / "reports").exists()
        from disaster_report.store._tree import incident_report_path
        assert incident_report_path(tmp_path, inc, "USGS", rid).exists()
        assert not report_staging_path(tmp_path, "USGS", rid).exists()

    def test_link_auto_fills_search_keys_from_birthing_report(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        report = _build_report(
            places=[ReportPlace(country_code="VE", subdivision="", locality="")]
        )
        rid = store.ingest_source_report(report)
        store.ingest_report_places(rid, report.places)
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        manifest_path = incident_dir(tmp_path, inc) / "incident.yaml"
        import yaml
        manifest = yaml.safe_load(manifest_path.read_text())
        assert manifest["id"] == inc
        assert len(manifest["search_keys"]) > 0

    def test_second_link_does_not_overwrite_search_keys(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid1 = store.ingest_source_report(
            _build_report(source_id="us-first", places=[ReportPlace(country_code="VE", subdivision="", locality="")])
        )
        rid2 = store.ingest_source_report(
            _build_report(source_id="us-second", places=[ReportPlace(country_code="BR", subdivision="", locality="")])
        )
        inc = _new_incident_id()
        store.add_report_incident(rid1, inc)
        import yaml
        manifest_path = incident_dir(tmp_path, inc) / "incident.yaml"
        first_keys = yaml.safe_load(manifest_path.read_text())["search_keys"]
        store.add_report_incident(rid2, inc)
        second_keys = yaml.safe_load(manifest_path.read_text())["search_keys"]
        assert first_keys == second_keys

    def test_read_report_ids_for_incident(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(_build_report())
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        assert rid in store.read_report_ids_for_incident(inc)

    def test_read_incident_ids_for_report(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(_build_report())
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        assert inc in store.read_incident_ids_for_report(rid)


class TestTimeline:
    def test_append_creates_log_file(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        inc = _new_incident_id()
        store.append_timeline(_build_log(incident_id=inc, summary="first"))
        assert log_path(tmp_path, inc, "2026-07-03").exists()

    def test_same_day_upsert_merges_with_single_newline(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        inc = _new_incident_id()
        store.append_timeline(_build_log(incident_id=inc, summary="alpha"))
        store.append_timeline(_build_log(incident_id=inc, summary="beta"))
        timeline = store.read_timeline(inc)
        assert len(timeline) == 1
        assert timeline[0].summary == "alpha\nbeta"

    def test_distinct_dates_admitted(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        inc = _new_incident_id()
        store.append_timeline(_build_log(incident_id=inc, log_date="2026-07-01"))
        store.append_timeline(_build_log(incident_id=inc, log_date="2026-07-02"))
        assert len(store.read_timeline(inc)) == 2

    def test_read_timeline_ordered_by_date_ascending(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        inc = _new_incident_id()
        store.append_timeline(_build_log(incident_id=inc, log_date="2026-07-03"))
        store.append_timeline(_build_log(incident_id=inc, log_date="2026-07-01"))
        timeline = store.read_timeline(inc)
        assert timeline[0].log_date == "2026-07-01"
        assert timeline[1].log_date == "2026-07-03"


class TestTimelineWithProvenance:
    def test_moves_news_into_log_dir(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path, clock=_clock)
        nid = store.ingest_news_item(_build_news())
        inc = _new_incident_id()
        store.assign_news_to_incident(nid, inc)
        store.append_timeline_with_provenance(
            _build_log(incident_id=inc, log_date="2026-07-03"), {nid}
        )
        assert log_news_path(tmp_path, inc, "2026-07-03", nid).exists()
        assert not incident_news_path(tmp_path, inc, nid).exists()

    def test_read_summarized_news_ids(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path, clock=_clock)
        nid = store.ingest_news_item(_build_news())
        inc = _new_incident_id()
        store.assign_news_to_incident(nid, inc)
        assert store.read_summarized_news_ids(inc) == set()
        store.append_timeline_with_provenance(
            _build_log(incident_id=inc), {nid}
        )
        assert nid in store.read_summarized_news_ids(inc)

    def test_read_logs_with_news_co_locates(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path, clock=_clock)
        nid = store.ingest_news_item(_build_news())
        inc = _new_incident_id()
        store.assign_news_to_incident(nid, inc)
        store.append_timeline_with_provenance(
            _build_log(incident_id=inc), {nid}
        )
        logs = store.read_logs_with_news(inc)
        assert len(logs) == 1
        log, news = logs[0]
        assert log.log_date == "2026-07-03"
        assert len(news) == 1
        assert news[0].url == "https://example.com/news"

    def test_rerun_does_not_duplicate(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path, clock=_clock)
        nid = store.ingest_news_item(_build_news())
        inc = _new_incident_id()
        store.assign_news_to_incident(nid, inc)
        store.append_timeline_with_provenance(
            _build_log(incident_id=inc), {nid}
        )
        store.append_timeline_with_provenance(
            _build_log(incident_id=inc, summary="second"), {nid}
        )
        timeline = store.read_timeline(inc)
        assert len(timeline) == 1
        assert "\n" in timeline[0].summary


class TestReadIncidents:
    def test_genesis_is_earliest_report_by_date(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid_early = store.ingest_source_report(
            _build_report(source_id="us-early", name="Early", report_date="2026-06-01")
        )
        rid_late = store.ingest_source_report(
            _build_report(source_id="us-late", name="Late", report_date="2026-07-01")
        )
        inc = _new_incident_id()
        store.add_report_incident(rid_late, inc)
        store.add_report_incident(rid_early, inc)
        incidents = store.read_incidents()
        assert len(incidents) == 1
        assert incidents[0].name == "Early"

    def test_category_disease_for_who_source(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(
            _build_report(source="WHO", source_id="don001", incident_type="Ebola")
        )
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        incidents = store.read_incidents()
        assert incidents[0].incident_category == "disease"

    def test_category_geophysical_for_usgs(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(_build_report(source="USGS"))
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        incidents = store.read_incidents()
        assert incidents[0].incident_category == "geophysical"

    def test_empty_store_returns_empty_list(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        assert store.read_incidents() == []


class TestActiveIncidents:
    def test_active_fires_on_pending_news_in_window(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path, clock=_clock)
        rid = store.ingest_source_report(_build_report())
        nid = store.ingest_news_item(_build_news(published_date="2026-06-30T10:00:00Z"))
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        store.assign_news_to_incident(nid, inc)
        active = store.active_incidents(WINDOW)
        assert len(active) == 1
        assert active[0].incident_id == inc

    def test_active_ignores_old_pending_news(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path, clock=_clock)
        rid = store.ingest_source_report(_build_report())
        nid = store.ingest_news_item(_build_news(published_date="2025-01-01T00:00:00Z"))
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        store.assign_news_to_incident(nid, inc)
        assert store.active_incidents(WINDOW) == []

    def test_active_ignores_summarized_news(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path, clock=_clock)
        rid = store.ingest_source_report(_build_report())
        nid = store.ingest_news_item(_build_news(published_date="2026-06-30T10:00:00Z"))
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        store.assign_news_to_incident(nid, inc)
        store.append_timeline_with_provenance(
            _build_log(incident_id=inc), {nid}
        )
        assert store.active_incidents(WINDOW) == []


class TestMergeIncidents:
    def test_merge_moves_reports(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(_build_report())
        source = _new_incident_id()
        target = _new_incident_id()
        store.add_report_incident(rid, source)
        store.set_search_keys(target, [])
        store.merge_incidents(source, target)
        assert rid in store.read_report_ids_for_incident(target)
        assert store.read_report_ids_for_incident(source) == []
        assert not incident_dir(tmp_path, source).exists()

    def test_merge_moves_pending_news(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        nid = store.ingest_news_item(_build_news())
        source = _new_incident_id()
        target = _new_incident_id()
        store.assign_news_to_incident(nid, source)
        store.set_search_keys(target, [])
        store.merge_incidents(source, target)
        assert store.read_incident_for_news(nid) == target

    def test_merge_moves_logs_and_summarized_news(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path, clock=_clock)
        nid = store.ingest_news_item(_build_news())
        source = _new_incident_id()
        target = _new_incident_id()
        store.assign_news_to_incident(nid, source)
        store.append_timeline_with_provenance(
            _build_log(incident_id=source, log_date="2026-07-03"), {nid}
        )
        store.set_search_keys(target, [])
        store.merge_incidents(source, target)
        assert log_news_path(tmp_path, target, "2026-07-03", nid).exists()
        logs = store.read_logs_with_news(target)
        assert len(logs) == 1

    def test_merge_same_date_logs_join_with_newline(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path, clock=_clock)
        nid_s = store.ingest_news_item(_build_news(url="https://a.com"))
        nid_t = store.ingest_news_item(_build_news(url="https://b.com"))
        source = _new_incident_id()
        target = _new_incident_id()
        store.assign_news_to_incident(nid_s, source)
        store.assign_news_to_incident(nid_t, target)
        store.append_timeline_with_provenance(
            _build_log(incident_id=source, log_date="2026-07-03", summary="alpha"), {nid_s}
        )
        store.append_timeline_with_provenance(
            _build_log(incident_id=target, log_date="2026-07-03", summary="beta"), {nid_t}
        )
        store.merge_incidents(source, target)
        timeline = store.read_timeline(target)
        assert len(timeline) == 1
        assert "\n" in timeline[0].summary
        assert "alpha" in timeline[0].summary
        assert "beta" in timeline[0].summary

    def test_merge_keeps_target_search_keys(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(
            _build_report(places=[ReportPlace(country_code="VE", subdivision="", locality="")])
        )
        source = _new_incident_id()
        target = _new_incident_id()
        store.add_report_incident(rid, source)
        store.set_search_keys(target, ["target-key"])
        store.merge_incidents(source, target)
        import yaml
        manifest = yaml.safe_load((incident_dir(tmp_path, target) / "incident.yaml").read_text())
        assert manifest["search_keys"] == ["target-key"]

    def test_merge_noop_on_missing_source(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        target = _new_incident_id()
        store.set_search_keys(target, ["k"])
        store.merge_incidents("nonexistent", target)
        assert store.read_incidents() == []


class TestSetSearchKeys:
    def test_set_keys_writes_to_manifest(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        inc = _new_incident_id()
        store.set_search_keys(inc, ["key1", "key2"])
        import yaml
        manifest = yaml.safe_load((incident_dir(tmp_path, inc) / "incident.yaml").read_text())
        assert manifest["search_keys"] == ["key1", "key2"]

    def test_set_keys_overwrites(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        inc = _new_incident_id()
        store.set_search_keys(inc, ["old"])
        store.set_search_keys(inc, ["new"])
        import yaml
        manifest = yaml.safe_load((incident_dir(tmp_path, inc) / "incident.yaml").read_text())
        assert manifest["search_keys"] == ["new"]


class TestPersistence:
    def test_reload_rebuilds_indexes_from_disk(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        rid = store.ingest_source_report(_build_report())
        nid = store.ingest_news_item(_build_news())
        inc = _new_incident_id()
        store.add_report_incident(rid, inc)
        store.assign_news_to_incident(nid, inc)
        store.append_timeline_with_provenance(
            _build_log(incident_id=inc), {nid}
        )
        reloaded = ContentStore(tmp_path, clock=_clock)
        assert rid in reloaded.read_report_ids_for_incident(inc)
        assert reloaded.read_incident_for_news(nid) == inc
        assert nid in reloaded.read_news(inc)[0].url or len(reloaded.read_news(inc)) == 1
        assert len(reloaded.read_logs_with_news(inc)) == 1
        assert len(reloaded.read_timeline(inc)) == 1


class TestResumabilityStamp:
    def test_mark_report_searched_makes_key_appear(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        store.ingest_source_report(_build_report(source="USGS", source_id="us6001"))
        store.mark_report_searched("USGS", "us6001", "2026-07-04T12:00:00Z")
        keys = store.read_searched_report_keys()
        assert "USGS:us6001" in keys

    def test_unsearched_report_absent(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        store.ingest_source_report(_build_report(source="USGS", source_id="us6001"))
        assert store.read_searched_report_keys() == set()
