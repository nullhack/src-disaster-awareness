from __future__ import annotations

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError

from disaster_report.models import (
    Incident,
    IncidentLog,
    NewsItem,
    ReportPlace,
    SourceReport,
)
from disaster_report.store.base import Warehouse

ACTIVE_WINDOW_DAYS = 7


class TestSourceReportIngest:
    def test_ingest_new_source_report_persists_record_with_report_id(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        report = build_source_report()
        report_id = wh.ingest_source_report(report)
        assert isinstance(report_id, int)
        reports = wh.read_source_reports()
        assert len(reports) == 1
        assert reports[0].source == report.source
        assert reports[0].source_id == report.source_id

    def test_re_ingest_same_source_and_source_id_is_idempotent(self, db_url) -> None:
        wh = Warehouse(db_url)
        report = build_source_report()
        rid1 = wh.ingest_source_report(report)
        rid2 = wh.ingest_source_report(report)
        assert rid1 == rid2
        assert len(wh.read_source_reports()) == 1

    def test_each_source_keeps_own_raw_schema_in_raw_fields(self, db_url) -> None:
        wh = Warehouse(db_url)
        wh.ingest_source_report(
            build_source_report(source="USGS", raw_fields={"mag": 5.5})
        )
        wh.ingest_source_report(
            build_source_report(
                source="WHO",
                source_id="don123",
                raw_fields={"don_id": "2026-DON609"},
            )
        )
        reports = wh.read_source_reports()
        assert len(reports) == 2

    def test_two_sources_same_internal_id_stay_distinct(self, db_url) -> None:
        wh = Warehouse(db_url)
        wh.ingest_source_report(build_source_report(source="USGS", source_id="abc"))
        wh.ingest_source_report(build_source_report(source="GDACS", source_id="abc"))
        assert len(wh.read_source_reports()) == 2

    def test_source_report_has_no_places_json_column(self, db_url) -> None:
        wh = Warehouse(db_url)
        wh.ingest_source_report(build_source_report())
        report = wh.read_source_reports()[0]
        assert not hasattr(report, "places") or report.places == []


class TestReportPlaces:
    def test_ingest_report_places_persists_one_row_per_place(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(build_source_report())
        places = [
            ReportPlace(country_code="VE", subdivision="Yaracuy", locality="Yumare")
        ]
        wh.ingest_report_places(rid, places)
        result = wh.read_report_places(rid)
        assert len(result) == 1
        assert result[0].country_code == "VE"

    def test_report_with_multiple_countries_has_multiple_place_rows(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(build_source_report())
        places = [
            ReportPlace(country_code="CD", subdivision="Ituri", locality=""),
            ReportPlace(country_code="UG", subdivision="Bundibugyo", locality=""),
        ]
        wh.ingest_report_places(rid, places)
        assert len(wh.read_report_places(rid)) == 2

    def test_read_report_places_returns_all_rows_for_report(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(build_source_report())
        wh.ingest_report_places(
            rid,
            [
                ReportPlace(country_code="US", subdivision="Oregon", locality=""),
            ],
        )
        result = wh.read_report_places(rid)
        assert len(result) == 1
        assert result[0].subdivision == "Oregon"

    def test_ocean_report_has_empty_country_code(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(build_source_report())
        wh.ingest_report_places(
            rid,
            [
                ReportPlace(country_code="", subdivision="", locality="Ocean"),
            ],
        )
        result = wh.read_report_places(rid)
        assert result[0].country_code == ""

    def test_duplicate_place_row_is_idempotent(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(build_source_report())
        place = ReportPlace(country_code="VE", subdivision="", locality="")
        wh.ingest_report_places(rid, [place])
        wh.ingest_report_places(rid, [place])
        assert len(wh.read_report_places(rid)) == 1


class TestNewsItemIngest:
    def test_ingest_new_news_item_persists_record_with_news_id(self, db_url) -> None:
        wh = Warehouse(db_url)
        item = build_news_item()
        news_id = wh.ingest_news_item(item)
        assert isinstance(news_id, int)
        assert wh.read_news_item(news_id).url == item.url

    def test_re_ingest_same_url_is_idempotent(self, db_url) -> None:
        wh = Warehouse(db_url)
        item = build_news_item()
        nid1 = wh.ingest_news_item(item)
        nid2 = wh.ingest_news_item(item)
        assert nid1 == nid2

    def test_published_date_is_sticky_on_re_ingest(self, db_url) -> None:
        wh = Warehouse(db_url)
        original = build_news_item(published_date="2026-06-24T12:00:00Z")
        nid = wh.ingest_news_item(original)
        wh.ingest_news_item(build_news_item(published_date="2026-07-01T12:00:00Z"))
        assert wh.read_news_item(nid).published_date == "2026-06-24T12:00:00Z"


class TestReportIncidents:
    def test_insert_report_incident_persists_membership(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(build_source_report())
        wh.add_report_incident(rid, 1782000000600)
        assert rid in wh.read_report_ids_for_incident(1782000000600)

    def test_report_in_multiple_incidents_has_multiple_rows(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(build_source_report())
        wh.add_report_incident(rid, 1782000000600)
        wh.add_report_incident(rid, 1782000000700)
        assert rid in wh.read_report_ids_for_incident(1782000000600)
        assert rid in wh.read_report_ids_for_incident(1782000000700)

    def test_duplicate_report_incident_is_idempotent(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(build_source_report())
        wh.add_report_incident(rid, 1782000000600)
        wh.add_report_incident(rid, 1782000000600)
        assert len(wh.read_report_ids_for_incident(1782000000600)) == 1


class TestNewsIncidents:
    def test_birth_new_news_assigns_new_incident_id(self, db_url) -> None:
        wh = Warehouse(db_url)
        nid = wh.ingest_news_item(build_news_item())
        assert wh.read_incident_for_news(nid) is None
        wh.assign_news_to_incident(nid, 1782000000600)
        assert wh.read_incident_for_news(nid) == 1782000000600

    def test_join_existing_news_keeps_existing_incident_id(self, db_url) -> None:
        wh = Warehouse(db_url)
        nid = wh.ingest_news_item(build_news_item())
        wh.assign_news_to_incident(nid, 1782000000600)
        assert wh.read_incident_for_news(nid) == 1782000000600

    def test_news_incident_pk_enforces_one_incident_per_news(self, db_url) -> None:
        wh = Warehouse(db_url)
        nid = wh.ingest_news_item(build_news_item())
        wh.assign_news_to_incident(nid, 1782000000600)
        wh.assign_news_to_incident(nid, 1782000000700)
        assert wh.read_incident_for_news(nid) == 1782000000700

    def test_read_incidents_for_news_returns_mapping(self, db_url) -> None:
        wh = Warehouse(db_url)
        n1 = wh.ingest_news_item(build_news_item(url="https://a.com"))
        n2 = wh.ingest_news_item(build_news_item(url="https://b.com"))
        wh.assign_news_to_incident(n1, 1782000000600)
        wh.assign_news_to_incident(n2, 1782000000700)
        mapping = wh.read_incidents_for_news({n1, n2})
        assert mapping[n1] == {1782000000600}
        assert mapping[n2] == {1782000000700}

    def test_read_incidents_for_news_empty_for_unknown_news(self, db_url) -> None:
        wh = Warehouse(db_url)
        assert wh.read_incidents_for_news({999999}) == {}


class TestTimeline:
    def test_append_row_keyed_by_incident_id_and_log_datetime(self, db_url) -> None:
        wh = Warehouse(db_url)
        log = build_timeline_row(incident_id=100, log_datetime="2026-06-24T12:00:00Z")
        wh.append_timeline(log)
        result = wh.read_timeline(100)
        assert len(result) == 1
        assert result[0].summary == log.summary

    def test_multiple_logs_same_incident_distinct_datetimes_admitted(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        wh.append_timeline(
            build_timeline_row(incident_id=100, log_datetime="2026-06-24T12:00:00Z")
        )
        wh.append_timeline(
            build_timeline_row(incident_id=100, log_datetime="2026-07-01T12:00:00Z")
        )
        assert len(wh.read_timeline(100)) == 2


class TestReadModel:
    def test_read_incidents_returns_view_derived_incidents(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(
            build_source_report(source="USGS", incident_type="Earthquake")
        )
        wh.add_report_incident(rid, 1782000000600)
        incidents = wh.read_incidents()
        assert len(incidents) == 1
        assert incidents[0].incident_id == 1782000000600
        assert incidents[0].incident_category == "geophysical"

    def test_read_incidents_genesis_is_earliest_by_date_report(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid1 = wh.ingest_source_report(
            build_source_report(source="USGS", report_date="2026-06-24")
        )
        rid2 = wh.ingest_source_report(
            build_source_report(
                source="USGS",
                source_id="us6000other",
                report_date="2026-06-25",
            )
        )
        wh.add_report_incident(rid1, 1782000000600)
        wh.add_report_incident(rid2, 1782000000600)
        incidents = wh.read_incidents()
        assert incidents[0].genesis_report_id == rid1

    def test_read_incidents_category_derived_from_source(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(
            build_source_report(source="WHO", incident_type="Ebola")
        )
        wh.add_report_incident(rid, 1782000000800)
        incidents = wh.read_incidents()
        assert incidents[0].incident_category == "disease"
        assert incidents[0].incident_type == "Ebola"

    def test_read_timeline_returns_story_for_incident(self, db_url) -> None:
        wh = Warehouse(db_url)
        wh.append_timeline(
            build_timeline_row(
                incident_id=100, log_datetime="2026-06-24T12:00:00Z", summary="event"
            )
        )
        tl = wh.read_timeline(100)
        assert len(tl) == 1
        assert tl[0].summary == "event"

    def test_read_news_returns_items_for_incident_via_news_incidents(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        nid = wh.ingest_news_item(build_news_item(url="https://a.com"))
        wh.assign_news_to_incident(nid, 1782000000600)
        news = wh.read_news(1782000000600)
        assert len(news) == 1
        assert news[0].url == "https://a.com"


class TestResumabilityStamp:
    def test_mark_report_searched_adds_key_to_searched_set(self, db_url) -> None:
        wh = Warehouse(db_url)
        wh.ingest_source_report(build_source_report())
        wh.mark_report_searched("USGS", "us6000test", "2026-07-04T12:00:00Z")
        keys = wh.read_searched_report_keys()
        assert "USGS:us6000test" in keys

    def test_unmarked_report_absent_from_searched_set(self, db_url) -> None:
        wh = Warehouse(db_url)
        wh.ingest_source_report(build_source_report())
        keys = wh.read_searched_report_keys()
        assert "USGS:us6000test" not in keys

    def test_stamp_persisted_in_raw_fields_news_searched_at(self, db_url) -> None:
        wh = Warehouse(db_url)
        wh.ingest_source_report(build_source_report())
        wh.mark_report_searched("USGS", "us6000test", "2026-07-04T12:00:00Z")
        report = wh.read_source_reports()[0]
        assert report.raw_fields.get("_news_searched_at") == "2026-07-04T12:00:00Z"

    def test_re_marking_report_searched_is_idempotent(self, db_url) -> None:
        wh = Warehouse(db_url)
        wh.ingest_source_report(build_source_report())
        wh.mark_report_searched("USGS", "us6000test", "2026-07-04T12:00:00Z")
        wh.mark_report_searched("USGS", "us6000test", "2026-07-05T12:00:00Z")
        keys = wh.read_searched_report_keys()
        assert len(keys) == 1
        report = wh.read_source_reports()[0]
        assert report.raw_fields.get("_news_searched_at") == "2026-07-05T12:00:00Z"


class TestNoChurn:
    def test_incident_view_has_no_stored_mutable_recency_field(self, db_url) -> None:
        wh = Warehouse(db_url)
        rid = wh.ingest_source_report(build_source_report())
        wh.add_report_incident(rid, 1782000000600)
        incidents = wh.read_incidents()
        for inc in incidents:
            forbidden = {"recency_score", "last_updated", "activity_score"}
            assert not any(hasattr(inc, f) for f in forbidden)


class TestActiveIncidents:
    def test_active_incidents_derived_from_publication_date_within_window(
        self, db_url, clock
    ) -> None:
        wh = Warehouse(db_url, clock=clock)
        rid = wh.ingest_source_report(build_source_report())
        nid = wh.ingest_news_item(
            build_news_item(published_date="2026-07-03T12:00:00Z")
        )
        wh.assign_news_to_incident(nid, 1782000000600)
        wh.add_report_incident(rid, 1782000000600)
        active = wh.active_incidents(ACTIVE_WINDOW_DAYS)
        assert any(i.incident_id == 1782000000600 for i in active)

    def test_incident_with_only_old_publication_date_is_not_active(
        self, db_url, clock
    ) -> None:
        wh = Warehouse(db_url, clock=clock)
        rid = wh.ingest_source_report(build_source_report())
        nid = wh.ingest_news_item(
            build_news_item(published_date="2026-01-01T12:00:00Z")
        )
        wh.assign_news_to_incident(nid, 1782000000600)
        wh.add_report_incident(rid, 1782000000600)
        active = wh.active_incidents(ACTIVE_WINDOW_DAYS)
        assert not any(i.incident_id == 1782000000600 for i in active)


class TestIncidentLogNews:
    def test_read_summarized_news_ids_empty_for_incident_with_no_logs(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        assert wh.read_summarized_news_ids(1782000000600) == set()

    def test_read_summarized_news_ids_returns_linked_ids_after_provenance_write(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        n1 = wh.ingest_news_item(build_news_item(url="https://a.com"))
        n2 = wh.ingest_news_item(build_news_item(url="https://b.com"))
        wh.append_timeline_with_provenance(
            build_timeline_row(
                incident_id=1782000000600, log_datetime="2026-07-04T12:00:00Z"
            ),
            {n1, n2},
        )
        assert wh.read_summarized_news_ids(1782000000600) == {n1, n2}

    def test_read_summarized_news_ids_grows_as_new_logs_with_new_news_added(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        n1 = wh.ingest_news_item(build_news_item(url="https://a.com"))
        n2 = wh.ingest_news_item(build_news_item(url="https://b.com"))
        n3 = wh.ingest_news_item(build_news_item(url="https://c.com"))
        wh.append_timeline_with_provenance(
            build_timeline_row(
                incident_id=1782000000600, log_datetime="2026-07-04T12:00:00Z"
            ),
            {n1, n2},
        )
        assert wh.read_summarized_news_ids(1782000000600) == {n1, n2}
        wh.append_timeline_with_provenance(
            build_timeline_row(
                incident_id=1782000000600, log_datetime="2026-07-05T12:00:00Z"
            ),
            {n3},
        )
        assert wh.read_summarized_news_ids(1782000000600) == {n1, n2, n3}

    def test_read_summarized_news_ids_scoped_per_incident(self, db_url) -> None:
        wh = Warehouse(db_url)
        n1 = wh.ingest_news_item(build_news_item(url="https://a.com"))
        n2 = wh.ingest_news_item(build_news_item(url="https://b.com"))
        wh.append_timeline_with_provenance(
            build_timeline_row(
                incident_id=1782000000600, log_datetime="2026-07-04T12:00:00Z"
            ),
            {n1},
        )
        wh.append_timeline_with_provenance(
            build_timeline_row(
                incident_id=1782000000700, log_datetime="2026-07-04T12:00:00Z"
            ),
            {n2},
        )
        assert wh.read_summarized_news_ids(1782000000600) == {n1}
        assert wh.read_summarized_news_ids(1782000000700) == {n2}

    def test_append_timeline_with_provenance_writes_log_row_and_junction_rows(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        n1 = wh.ingest_news_item(build_news_item(url="https://a.com"))
        n2 = wh.ingest_news_item(build_news_item(url="https://b.com"))
        log = build_timeline_row(
            incident_id=1782000000600, log_datetime="2026-07-04T12:00:00Z"
        )
        wh.append_timeline_with_provenance(log, {n1, n2})
        timeline = wh.read_timeline(1782000000600)
        assert len(timeline) == 1
        assert timeline[0].summary == log.summary
        assert timeline[0].log_datetime == log.log_datetime
        assert wh.read_summarized_news_ids(1782000000600) == {n1, n2}

    def test_append_timeline_with_provenance_junction_links_exactly_given_news_ids(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        n1 = wh.ingest_news_item(build_news_item(url="https://a.com"))
        n2 = wh.ingest_news_item(build_news_item(url="https://b.com"))
        n3 = wh.ingest_news_item(build_news_item(url="https://c.com"))
        wh.append_timeline_with_provenance(
            build_timeline_row(
                incident_id=1782000000600, log_datetime="2026-07-04T12:00:00Z"
            ),
            {n1, n2},
        )
        linked = _junction_news_ids(wh, 1782000000600, "2026-07-04T12:00:00Z")
        assert linked == {n1, n2}
        assert n3 not in linked

    def test_append_timeline_with_provenance_is_idempotent_on_log_pk_collision(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        n1 = wh.ingest_news_item(build_news_item(url="https://a.com"))
        log = build_timeline_row(
            incident_id=1782000000600, log_datetime="2026-07-04T12:00:00Z"
        )
        wh.append_timeline_with_provenance(log, {n1})
        wh.append_timeline_with_provenance(log, {n1})
        assert len(wh.read_timeline(1782000000600)) == 1
        assert _junction_news_ids(wh, 1782000000600, "2026-07-04T12:00:00Z") == {n1}

    def test_append_timeline_with_provenance_rolls_back_on_junction_fk_failure(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        with wh._engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS incident_log_news"))
            conn.execute(
                text(
                    "CREATE TABLE incident_log_news ("
                    "incident_id INTEGER NOT NULL, "
                    "log_datetime VARCHAR NOT NULL, "
                    "news_id INTEGER NOT NULL, "
                    "PRIMARY KEY (incident_id, log_datetime, news_id), "
                    "FOREIGN KEY (incident_id, log_datetime) "
                    "REFERENCES incident_logs (incident_id, log_datetime) "
                    "ON DELETE CASCADE, "
                    "FOREIGN KEY (news_id) REFERENCES news_items (news_id) "
                    "ON DELETE CASCADE)"
                )
            )
        event.listen(wh._engine, "connect", _enable_foreign_keys)
        wh._engine.dispose()
        n1 = wh.ingest_news_item(build_news_item(url="https://a.com"))
        log = build_timeline_row(
            incident_id=1782000000600, log_datetime="2026-07-04T12:00:00Z"
        )
        with pytest.raises(IntegrityError):
            wh.append_timeline_with_provenance(log, {n1, 999999})
        assert len(wh.read_timeline(1782000000600)) == 0
        assert wh.read_summarized_news_ids(1782000000600) == set()

    def test_append_timeline_with_provenance_parallel_to_append_timeline(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        n1 = wh.ingest_news_item(build_news_item(url="https://a.com"))
        wh.append_timeline(
            build_timeline_row(
                incident_id=1782000000600, log_datetime="2026-07-04T12:00:00Z"
            )
        )
        assert len(wh.read_timeline(1782000000600)) == 1
        assert wh.read_summarized_news_ids(1782000000600) == set()
        wh.append_timeline_with_provenance(
            build_timeline_row(
                incident_id=1782000000600, log_datetime="2026-07-05T12:00:00Z"
            ),
            {n1},
        )
        assert len(wh.read_timeline(1782000000600)) == 2
        assert wh.read_summarized_news_ids(1782000000600) == {n1}


class TestIncidentLogNewsBackfill:
    def test_backfill_links_existing_logs_to_news_published_before_log_datetime(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        _create_junction_table(wh)
        n1 = wh.ingest_news_item(
            build_news_item(url="https://a.com", published_date="2026-07-03")
        )
        n2 = wh.ingest_news_item(
            build_news_item(url="https://b.com", published_date="2026-07-04")
        )
        wh.assign_news_to_incident(n1, 1782000000600)
        wh.assign_news_to_incident(n2, 1782000000600)
        wh.append_timeline(
            build_timeline_row(
                incident_id=1782000000600, log_datetime="2026-07-05T12:00:00Z"
            )
        )
        _run_backfill(wh)
        assert _junction_news_ids(wh, 1782000000600, "2026-07-05T12:00:00Z") == {n1, n2}

    def test_backfill_does_not_link_news_published_after_log_datetime(
        self, db_url
    ) -> None:
        wh = Warehouse(db_url)
        _create_junction_table(wh)
        n_before = wh.ingest_news_item(
            build_news_item(url="https://a.com", published_date="2026-07-03")
        )
        n_after = wh.ingest_news_item(
            build_news_item(url="https://b.com", published_date="2026-07-06")
        )
        wh.assign_news_to_incident(n_before, 1782000000600)
        wh.assign_news_to_incident(n_after, 1782000000600)
        wh.append_timeline(
            build_timeline_row(
                incident_id=1782000000600, log_datetime="2026-07-05T12:00:00Z"
            )
        )
        _run_backfill(wh)
        linked = _junction_news_ids(wh, 1782000000600, "2026-07-05T12:00:00Z")
        assert n_before in linked
        assert n_after not in linked

    def test_backfill_is_idempotent_under_rerun(self, db_url) -> None:
        wh = Warehouse(db_url)
        _create_junction_table(wh)
        n1 = wh.ingest_news_item(
            build_news_item(url="https://a.com", published_date="2026-07-03")
        )
        n2 = wh.ingest_news_item(
            build_news_item(url="https://b.com", published_date="2026-07-04")
        )
        wh.assign_news_to_incident(n1, 1782000000600)
        wh.assign_news_to_incident(n2, 1782000000600)
        wh.append_timeline(
            build_timeline_row(
                incident_id=1782000000600, log_datetime="2026-07-05T12:00:00Z"
            )
        )
        _run_backfill(wh)
        _run_backfill(wh)
        assert _junction_news_ids(wh, 1782000000600, "2026-07-05T12:00:00Z") == {n1, n2}


def build_source_report(
    *,
    source: str = "USGS",
    source_id: str = "us6000test",
    incident_type: str = "Earthquake",
    name: str = "M 5.0 - Test",
    places: list[ReportPlace] | None = None,
    report_date: str = "2026-07-04",
    raw_fields: dict[str, object] | None = None,
) -> SourceReport:
    return SourceReport(
        source=source,
        source_id=source_id,
        incident_type=incident_type,
        name=name,
        places=places or [ReportPlace(country_code="US", subdivision="", locality="")],
        report_date=report_date,
        raw_fields=raw_fields or {},
    )


def build_news_item(
    *,
    url: str = "https://example.com/news",
    title: str = "Test News",
    body: str = "Test body",
    published_date: str = "2026-07-04T12:00:00Z",
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


def build_timeline_row(
    *,
    incident_id: int = 100,
    log_datetime: str = "2026-07-04T12:00:00Z",
    summary: str = "new developments",
) -> IncidentLog:
    return IncidentLog(
        incident_id=incident_id,
        log_datetime=log_datetime,
        summary=summary,
    )


def warehouse_with(warehouse: Warehouse, *rows: object) -> Warehouse:
    return warehouse


def first_incident(incidents: list[Incident]) -> Incident:
    return incidents[0]


def _junction_news_ids(
    warehouse: Warehouse, incident_id: int, log_datetime: str
) -> set[int]:
    with warehouse._engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT news_id FROM incident_log_news "
                "WHERE incident_id = :iid AND log_datetime = :dt"
            ),
            {"iid": incident_id, "dt": log_datetime},
        ).fetchall()
    return {int(row[0]) for row in rows}


def _create_junction_table(warehouse: Warehouse) -> None:
    with warehouse._engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS incident_log_news ("
                "incident_id INTEGER NOT NULL, "
                "log_datetime VARCHAR NOT NULL, "
                "news_id INTEGER NOT NULL, "
                "PRIMARY KEY (incident_id, log_datetime, news_id))"
            )
        )


def _run_backfill(warehouse: Warehouse) -> None:
    with warehouse._engine.begin() as conn:
        conn.execute(
            text(
                "INSERT OR IGNORE INTO incident_log_news "
                "(incident_id, log_datetime, news_id) "
                "SELECT il.incident_id, il.log_datetime, ni.news_id "
                "FROM incident_logs il "
                "JOIN news_incidents ni ON ni.incident_id = il.incident_id "
                "JOIN news_items n ON n.news_id = ni.news_id "
                "WHERE n.published_date <= il.log_datetime"
            )
        )


def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
