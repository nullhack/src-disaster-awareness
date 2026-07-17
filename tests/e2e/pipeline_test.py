from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from disaster_report.ai.base import FilterResult
    from disaster_report.models import IncidentLog, NewsItem, SourceReport
    from disaster_report.store.base import Warehouse


class TestIngestSourceReports:
    def test_ingest_stores_all_fetched_reports_unconditionally(self) -> None:
        from disaster_report.pipeline import ingest_source_reports

        adapters = _adapters(None)
        warehouse = _warehouse()
        ingest_source_reports(adapters, warehouse)
        assert len(warehouse.read_source_reports()) >= 2

    def test_ingest_source_reports_counts_all_stored(self) -> None:
        from disaster_report.pipeline import ingest_source_reports

        adapters = _adapters(None)
        warehouse = _warehouse()
        kept = ingest_source_reports(adapters, warehouse)
        assert kept == len(warehouse.read_source_reports())

    def test_re_ingest_source_reports_is_no_churn(self) -> None:
        from disaster_report.pipeline import ingest_source_reports

        adapters = _adapters(None)
        warehouse = _warehouse()
        first = ingest_source_reports(adapters, warehouse)
        second = ingest_source_reports(adapters, warehouse)
        assert second == 0
        assert first == len(warehouse.read_source_reports())

    def test_ingest_source_reports_makes_no_ddg_no_ai_calls(self) -> None:
        from disaster_report.pipeline import ingest_source_reports

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        digester = _digester()
        ingest_source_reports(adapters, warehouse)
        assert len(ddg.queries) == 0
        assert digester.filter_calls == 0

    def test_ingest_stores_report_places(self) -> None:
        from disaster_report.pipeline import ingest_source_reports

        report = _source_report("USGS", "us-001", "Earthquake", "M5 Quake")
        adapters: list[object] = [_FakeAdapter([report])]
        warehouse = _warehouse()
        ingest_source_reports(adapters, warehouse)
        rid = warehouse.ingest_source_report(report)
        assert len(warehouse.read_report_places(rid)) >= 1

    def test_ingest_is_fail_isolated_per_source(self) -> None:
        from disaster_report.pipeline import ingest_source_reports

        adapters = _adapters("USGS")
        warehouse = _warehouse()
        kept = ingest_source_reports(adapters, warehouse)
        assert kept >= 1
        assert len(warehouse.read_source_reports()) >= 1


class TestSearchNews:
    def test_search_news_bare_stores_report_with_no_candidate_news(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert len(warehouse.read_searched_report_keys()) >= 1

    def test_search_news_calls_digester_filter_for_candidate_news(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        digester = _digester()
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            digester,
            clock=_clock(None),
        )
        assert digester.filter_calls >= 1

    def test_search_news_does_not_call_digester_summarize(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        digester = _digester()
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            digester,
            clock=_clock(None),
        )
        assert digester.summarize_calls == 0

    def test_search_news_writes_no_incident_logs(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        for incident in warehouse.read_incidents():
            assert len(warehouse.read_timeline(incident.incident_id)) == 0

    def test_search_news_ai_not_called_when_no_candidate_news(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(())
        digester = _digester()
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            digester,
            clock=_clock(None),
        )
        assert digester.filter_calls == 0

    def test_shared_news_joins_reports_into_one_incident(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_shared_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert len(warehouse.read_source_reports()) >= 2
        assert len(warehouse.read_incidents()) == 1

    def test_search_news_births_incident_for_new_news(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert len(warehouse.read_incidents()) >= 1

    def test_search_news_joins_existing_incident_for_known_news(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_shared_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert len(warehouse.read_incidents()) == 1

    def test_search_news_marks_report_searched(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert len(warehouse.read_searched_report_keys()) >= 1

    def test_search_news_skips_already_searched_report(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        ddg.queries.clear()
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert len(ddg.queries) == 0

    def test_unmonitored_report_has_no_news_search(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapter: Any = _GatedAdapter(monitor=False)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports([adapter], warehouse)
        search_news(
            warehouse,
            [adapter],
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert len(ddg.queries) == 0

    def test_source_id_bypasses_should_monitor(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapter: Any = _GatedAdapter(monitor=False)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports([adapter], warehouse)
        search_news(
            warehouse,
            [adapter],
            ddg,
            _digester(),
            clock=_clock(None),
            source_id="gated-001",
        )
        assert len(ddg.queries) > 0

    def test_source_id_does_not_affect_other_reports(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        reports = [
            _source_report("TEST", "gated-001", "Earthquake", "Gated Report"),
            _source_report("TEST", "gated-002", "Earthquake", "Other Report"),
        ]
        adapter: Any = _FakeAdapter(reports)
        adapter.should_monitor = lambda r: False  # type: ignore[method-assign]
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports([adapter], warehouse)
        search_news(
            warehouse,
            [adapter],
            ddg,
            _digester(),
            clock=_clock(None),
            source_id="gated-001",
        )
        assert len(ddg.queries) == 1
        assert "Other Report" not in ddg.queries

    def test_search_news_strict_first_loose_only_when_strict_empty(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapter: Any = _KeyedAdapter(strict="Strict Query", loose="Loose Query")
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports([adapter], warehouse)
        search_news(
            warehouse,
            [adapter],
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert "Strict Query" in ddg.queries

    def test_search_news_skips_loose_when_strict_returns_results(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapter: Any = _KeyedAdapter(strict="Strict Query", loose="Loose Query")
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports([adapter], warehouse)
        search_news(
            warehouse,
            [adapter],
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert "Loose Query" not in ddg.queries

    def test_search_news_skips_search_when_both_keys_empty(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapter: Any = _KeyedAdapter(strict="", loose="")
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        digester = _digester()
        ingest_source_reports([adapter], warehouse)
        search_news(
            warehouse,
            [adapter],
            ddg,
            digester,
            clock=_clock(None),
        )
        assert digester.filter_calls == 0

    def test_search_news_passes_news_timelimit_to_ddg(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
            news_timelimit="d",
        )
        assert ddg.last_timelimit == "d"

    def test_search_news_defaults_news_timelimit_to_one_week(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert ddg.last_timelimit == "w"

    def test_re_ingested_news_keeps_original_published_date(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        second_ddg = _ddg(_some_news("2099-12-31"))
        search_news(
            warehouse,
            adapters,
            second_ddg,
            _digester(),
            clock=_clock(None),
            source_id="us-001",
        )
        incidents = warehouse.read_incidents()
        assert len(incidents) > 0
        news = warehouse.read_news(incidents[0].incident_id)
        assert len(news) > 0
        assert news[0].published_date == "2026-07-04"

    def test_active_incident_is_repolled_on_second_run(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        ddg.queries.clear()
        search_news(
            warehouse,
            [],
            ddg,
            _digester(),
            clock=_clock(None),
            active_window_days=7,
        )
        assert len(ddg.queries) > 0

    def test_dormant_incident_not_repolled(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        incident = warehouse.read_incidents()[0]
        _age_out_incident_news(warehouse, incident.incident_id)
        ddg.queries.clear()
        search_news(
            warehouse,
            [],
            ddg,
            _digester(),
            clock=_clock(None),
            active_window_days=7,
        )
        assert len(ddg.queries) == 0

    def test_repoll_is_per_incident_not_per_report(self) -> None:
        from disaster_report.pipeline import ingest_source_reports, search_news

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_shared_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        assert len(warehouse.read_source_reports()) >= 2
        assert len(warehouse.read_incidents()) == 1
        ddg.queries.clear()
        search_news(
            warehouse,
            [],
            ddg,
            _digester(),
            clock=_clock(None),
            active_window_days=7,
        )
        assert 1 <= len(ddg.queries) <= 2

    def test_repoll_no_churn_when_no_new_news(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        incident = warehouse.read_incidents()[0]
        before = len(warehouse.read_timeline(incident.incident_id))
        search_news(
            warehouse,
            [],
            ddg,
            _digester(),
            clock=_clock(None),
            active_window_days=7,
        )
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        after = len(warehouse.read_timeline(incident.incident_id))
        assert after == before


class TestGenerateLogs:
    def test_generate_logs_appends_timeline_when_genuinely_new_news(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        incident = warehouse.read_incidents()[0]
        timeline = warehouse.read_timeline(incident.incident_id)
        assert len(timeline) == 1
        assert warehouse.read_summarized_news_ids(incident.incident_id) == {
            n.news_id for n in warehouse.read_news(incident.incident_id)
        }

    def test_generate_logs_no_churn_when_all_news_already_logged(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        before = sum(
            len(warehouse.read_timeline(i.incident_id))
            for i in warehouse.read_incidents()
        )
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        after = sum(
            len(warehouse.read_timeline(i.incident_id))
            for i in warehouse.read_incidents()
        )
        assert after == before

    def test_generate_logs_calls_digester_summarize_not_filter(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        digester = _digester()
        generate_logs(warehouse, digester, min_news_threshold=1)
        assert digester.summarize_calls >= 1
        assert digester.filter_calls == 0

    def test_generate_logs_passes_prior_summaries_to_summarize(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        digester = _PriorCapturingDigester()
        generate_logs(warehouse, digester, min_news_threshold=1)
        assert len(digester.captured_priors) >= 1
        assert digester.captured_priors[0] == []

    def test_log_date_uses_run_date(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        news = _some_news("2026-06-15")
        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(news)
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        incident = warehouse.read_incidents()[0]
        timeline = warehouse.read_timeline(incident.incident_id)
        assert len(timeline) > 0
        assert timeline[0].log_date == "2026-07-04"

    def test_generate_logs_batches_one_timeline_row_per_incident(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        for incident in warehouse.read_incidents():
            assert len(warehouse.read_timeline(incident.incident_id)) == 1

    def test_generate_logs_reads_news_committed_by_search_news(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        incidents_before = warehouse.read_incidents()
        assert len(incidents_before) >= 1
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        for incident in incidents_before:
            news = warehouse.read_news(incident.incident_id)
            timeline = warehouse.read_timeline(incident.incident_id)
            assert len(news) >= 1
            assert len(timeline) >= 1
            assert all(n.news_id != 0 for n in news)

    def test_generate_logs_fetches_only_unsummarized_news(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news("2026-07-05"))
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        incident = warehouse.read_incidents()[0]
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        late_ids: set[int] = set()
        for item in _late_news():
            nid = warehouse.ingest_news_item(item)
            warehouse.assign_news_to_incident(nid, incident.incident_id)
            late_ids.add(nid)
        capturer = _NewsCapturingDigester()
        generate_logs(warehouse, capturer, min_news_threshold=1)
        assert capturer.summarize_calls == 1
        assert {n.news_id for n in capturer.captured_news[0]} == late_ids

    def test_generate_logs_writes_provenance_junction(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        incident = warehouse.read_incidents()[0]
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        assert warehouse.read_summarized_news_ids(incident.incident_id) == {
            n.news_id for n in warehouse.read_news(incident.incident_id)
        }

    def test_generate_logs_no_churn_when_all_news_summarized(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        incident = warehouse.read_incidents()[0]
        before = len(warehouse.read_timeline(incident.incident_id))
        capturer = _NewsCapturingDigester()
        generate_logs(warehouse, capturer, min_news_threshold=1)
        assert capturer.summarize_calls == 0
        after = len(warehouse.read_timeline(incident.incident_id))
        assert after == before

    def test_generate_logs_handles_late_arriving_news(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news("2026-07-05"))
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        incident = warehouse.read_incidents()[0]
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        first_log_date = warehouse.read_timeline(incident.incident_id)[
            0
        ].log_date
        for item in _late_news():
            nid = warehouse.ingest_news_item(item)
            warehouse.assign_news_to_incident(nid, incident.incident_id)
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        timeline = warehouse.read_timeline(incident.incident_id)
        assert len(timeline) == 1
        assert timeline[0].log_date == first_log_date
        assert warehouse.read_summarized_news_ids(incident.incident_id) == {
            n.news_id for n in warehouse.read_news(incident.incident_id)
        }

    def test_generate_logs_atomic_log_and_provenance(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        incident = warehouse.read_incidents()[0]
        capturer = _NewsCapturingDigester()
        generate_logs(warehouse, capturer, min_news_threshold=1)
        assert capturer.summarize_calls == 1
        timeline = warehouse.read_timeline(incident.incident_id)
        assert len(timeline) == 1
        summarized_ids = {n.news_id for n in capturer.captured_news[0]}
        assert (
            warehouse.read_summarized_news_ids(incident.incident_id) == summarized_ids
        )

    def test_generate_logs_upserts_same_day_log_on_rerun(self) -> None:
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        clock = _clock(None)
        ddg = _ddg(_some_news("2026-07-04"))
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=clock,
        )
        incident = warehouse.read_incidents()[0]
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        assert len(warehouse.read_timeline(incident.incident_id)) == 1
        for item in _late_news():
            nid = warehouse.ingest_news_item(item)
            warehouse.assign_news_to_incident(nid, incident.incident_id)
        generate_logs(warehouse, _digester(), min_news_threshold=1)
        timeline = warehouse.read_timeline(incident.incident_id)
        assert len(timeline) == 1
        assert timeline[0].log_date == "2026-07-04"
        assert timeline[0].summary == "incident summary\n\nincident summary"
        assert warehouse.read_summarized_news_ids(incident.incident_id) == {
            n.news_id for n in warehouse.read_news(incident.incident_id)
        }

    def test_generate_logs_skips_below_threshold(self) -> None:
        from disaster_report.models import NewsItem
        from disaster_report.pipeline import (
            generate_logs,
            ingest_source_reports,
            search_news,
        )

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg((
            NewsItem(
                url="https://news.example/threshold-1",
                title="First article",
                body="Story one",
                published_date="2026-07-04",
                source="reuters",
                domain="news.example",
                image="",
            ),
            NewsItem(
                url="https://news.example/threshold-2",
                title="Second article",
                body="Story two",
                published_date="2026-07-04",
                source="ap",
                domain="news.example",
                image="",
            ),
        ))
        ingest_source_reports(adapters, warehouse)
        search_news(
            warehouse,
            adapters,
            ddg,
            _digester(),
            clock=_clock(None),
        )
        incident = warehouse.read_incidents()[0]
        capturer = _NewsCapturingDigester()
        generate_logs(warehouse, capturer, min_news_threshold=3)
        assert capturer.summarize_calls == 0
        assert len(warehouse.read_timeline(incident.incident_id)) == 0
        assert warehouse.read_summarized_news_ids(incident.incident_id) == set()
    def test_run_pipeline_runs_all_three_phases_in_order(self) -> None:
        from disaster_report.pipeline import run_pipeline

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        digester = _digester()
        run_pipeline(
            adapters,
            warehouse,
            ddg,
            digester,
            _clock(None),
            min_news_threshold=1,
        )
        assert len(warehouse.read_source_reports()) >= 2
        assert digester.filter_calls >= 1
        assert digester.summarize_calls >= 1

    def test_run_pipeline_returns_summed_ingest_report(self) -> None:
        from disaster_report.pipeline import IngestReport, run_pipeline

        adapters = _adapters(None)
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        report = run_pipeline(
            adapters,
            warehouse,
            ddg,
            _digester(),
            _clock(None),
        )
        assert isinstance(report, IngestReport)
        assert report.source_reports_kept >= 1
        assert report.ai_calls >= 0
        assert report.ddg_calls >= 0

    def test_run_pipeline_continues_to_phase_three_after_partial_phase_two(
        self,
    ) -> None:
        from disaster_report.pipeline import run_pipeline

        adapters: list[object] = [
            _BrokenAdapter(),
            _FakeAdapter(_adapters_report_list()),
        ]
        warehouse = _warehouse()
        ddg = _ddg(_some_news())
        digester = _digester()
        run_pipeline(
            adapters,
            warehouse,
            ddg,
            digester,
            _clock(None),
            min_news_threshold=1,
        )
        assert len(warehouse.read_source_reports()) >= 1
        assert digester.summarize_calls >= 1


class _FakeAdapter:
    def __init__(self, reports: list[SourceReport]) -> None:
        self._reports = reports

    def fetch(self) -> list[SourceReport]:
        return list(self._reports)

    def should_monitor(self, report: SourceReport) -> bool:
        return True

    def derive_keys(self, report: SourceReport) -> tuple[str, str]:
        return (report.name, report.name)


class _BrokenAdapter:
    def fetch(self) -> list[SourceReport]:
        from disaster_report.sources.errors import SourceFetchError

        raise SourceFetchError("source unavailable")

    def should_monitor(self, report: SourceReport) -> bool:
        return True

    def derive_keys(self, report: SourceReport) -> tuple[str, str]:
        return ("", "")


class _FakeDDG:
    def __init__(self, news: tuple[NewsItem, ...]) -> None:
        self._news = news
        self.last_timelimit: str | None = None
        self.queries: list[str] = []

    def search(self, query: str, timelimit: str | None = None) -> list[NewsItem]:
        self.last_timelimit = timelimit
        self.queries.append(query)
        return list(self._news)


class _KeyedAdapter:
    def __init__(self, strict: str, loose: str) -> None:
        self._strict = strict
        self._loose = loose

    def fetch(self) -> list[SourceReport]:
        return [_source_report("TEST", "t-001", "Earthquake", "test report")]

    def should_monitor(self, report: SourceReport) -> bool:
        return True

    def derive_keys(self, report: SourceReport) -> tuple[str, str]:
        return (self._strict, self._loose)


class _GatedAdapter:
    def __init__(self, monitor: bool) -> None:
        self._monitor = monitor

    def fetch(self) -> list[SourceReport]:
        return [_source_report("TEST", "gated-001", "Earthquake", "Gated Report")]

    def should_monitor(self, report: SourceReport) -> bool:
        return self._monitor

    def derive_keys(self, report: SourceReport) -> tuple[str, str]:
        return (report.name, report.name)


class _FakeDigester:
    def __init__(self) -> None:
        self.filter_calls = 0
        self.summarize_calls = 0

    def filter(
        self,
        candidate_news: list[NewsItem],
        *,
        incident_type: str,
        incident_name: str,
        incident_places: list,
        incident_date: str,
    ) -> FilterResult:
        from disaster_report.ai.base import FilterResult

        self.filter_calls += 1
        return FilterResult(
            selected_news=list(candidate_news),
            relevance_scores={item.url: 1.0 for item in candidate_news},
        )

    def summarize(
        self,
        selected_news: list[NewsItem],
        prior_summaries: list[IncidentLog],
        *,
        incident_type: str,
        incident_name: str,
        incident_places: list,
        incident_date: str,
    ) -> SummaryResult:
        from disaster_report.ai.base import SummaryResult

        self.summarize_calls += 1
        return SummaryResult(summary="incident summary", has_relevant_updates=True)


class _PriorCapturingDigester:
    def __init__(self) -> None:
        self.captured_priors: list[list[IncidentLog]] = []

    def filter(
        self,
        candidate_news: list[NewsItem],
        *,
        incident_type: str,
        incident_name: str,
        incident_places: list,
        incident_date: str,
    ) -> FilterResult:
        from disaster_report.ai.base import FilterResult

        return FilterResult(
            selected_news=list(candidate_news),
            relevance_scores={item.url: 1.0 for item in candidate_news},
        )

    def summarize(
        self,
        selected_news: list[NewsItem],
        prior_summaries: list[IncidentLog],
        *,
        incident_type: str,
        incident_name: str,
        incident_places: list,
        incident_date: str,
    ) -> SummaryResult:
        from disaster_report.ai.base import SummaryResult

        self.captured_priors.append(list(prior_summaries))
        return SummaryResult(summary="incident summary", has_relevant_updates=True)


class _NewsCapturingDigester:
    def __init__(self) -> None:
        self.captured_news: list[list[NewsItem]] = []
        self.summarize_calls = 0

    def filter(
        self,
        candidate_news: list[NewsItem],
        *,
        incident_type: str,
        incident_name: str,
        incident_places: list,
        incident_date: str,
    ) -> FilterResult:
        from disaster_report.ai.base import FilterResult

        return FilterResult(
            selected_news=list(candidate_news),
            relevance_scores={item.url: 1.0 for item in candidate_news},
        )

    def summarize(
        self,
        selected_news: list[NewsItem],
        prior_summaries: list[IncidentLog],
        *,
        incident_type: str,
        incident_name: str,
        incident_places: list,
        incident_date: str,
    ) -> SummaryResult:
        from disaster_report.ai.base import SummaryResult

        self.captured_news.append(list(selected_news))
        self.summarize_calls += 1
        return SummaryResult(summary="incident summary", has_relevant_updates=True)


def _built_run(
    news_results: tuple[NewsItem, ...] | None = None,
    clock: Callable[[], datetime] | None = None,
    broken_source: str | None = None,
    warehouse: Warehouse | None = None,
    digester: Any | None = None,
) -> tuple[list[object], Warehouse, _FakeDDG, Any, Callable[[], datetime]]:
    if warehouse is None:
        warehouse = _warehouse()
    return (
        _adapters(broken_source),
        warehouse,
        _ddg(news_results),
        digester if digester is not None else _digester(),
        _clock(clock),
    )


def _adapters(broken_source: str | None) -> list[object]:
    if broken_source == "USGS":
        return [_BrokenAdapter(), _FakeAdapter(_adapters_report_list())]
    return [_FakeAdapter(_adapters_report_list())]


def _adapters_report_list() -> list[SourceReport]:
    return [
        _source_report("USGS", "us-001", "Earthquake", "M5 Quake"),
        _source_report("GDACS", "gd-001", "Flood", "Big Flood"),
    ]


def _warehouse() -> Warehouse:
    from disaster_report.store.base import Warehouse

    return Warehouse("sqlite:///:memory:")


def _ddg(news_results: tuple[NewsItem, ...] | None) -> _FakeDDG:
    return _FakeDDG(news_results or ())


def _digester() -> _FakeDigester:
    return _FakeDigester()


def _clock(clock: Callable[[], datetime] | None) -> Callable[[], datetime]:
    import datetime

    if clock is not None:
        return clock
    fixed = datetime.datetime(2026, 7, 4, 12, 0, 0, 0, tzinfo=datetime.timezone.utc)
    return lambda: fixed


def _some_news(published_date: str = "2026-07-04") -> tuple[NewsItem, ...]:
    from disaster_report.models import NewsItem

    return (
        NewsItem(
            url="https://news.example/some-incident",
            title="Some incident report",
            body="Developing story",
            published_date=published_date,
            source="reuters",
            domain="news.example",
            image="",
        ),
    )


def _shared_news() -> tuple[NewsItem, ...]:
    from disaster_report.models import NewsItem

    return (
        NewsItem(
            url="https://news.example/shared-incident",
            title="Shared breaking news",
            body="Coverage from multiple agencies",
            published_date="2026-07-04",
            source="ap",
            domain="news.example",
            image="",
        ),
    )


def _late_news() -> tuple[NewsItem, ...]:
    from disaster_report.models import NewsItem

    return (
        NewsItem(
            url="https://news.example/late-arrival",
            title="Late breaking update",
            body="Update ingested after the first log was written",
            published_date="2026-07-04",
            source="reuters",
            domain="news.example",
            image="",
        ),
    )


def _source_report(
    source: str,
    source_id: str,
    incident_type: str,
    name: str,
) -> SourceReport:
    from disaster_report.models import ReportPlace, SourceReport

    return SourceReport(
        source=source,
        source_id=source_id,
        incident_type=incident_type,
        name=name,
        places=[ReportPlace(country_code="TL", subdivision="", locality="")],
        report_date="2026-07-04",
        raw_fields={},
    )


def _age_out_incident_news(warehouse: Warehouse, incident_id: int) -> None:
    from disaster_report.store.base import (
        _news_incidents_t,  # type: ignore[attr-defined]
        _news_items_t,  # type: ignore[attr-defined]
    )
    from sqlalchemy import update

    with warehouse._engine.begin() as conn:  # type: ignore[attr-defined]
        news_ids = [
            row[0]
            for row in conn.execute(
                _news_incidents_t.select().where(
                    _news_incidents_t.c.incident_id == incident_id
                )
            ).fetchall()
        ]
        conn.execute(
            update(_news_items_t)
            .where(_news_items_t.c.news_id.in_(news_ids))
            .values(published_date="2020-01-01T00:00:00Z")
        )
