from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from disaster_report.reporting.markdown import MarkdownRenderer
    from disaster_report.reporting.report import ReportDocument
    from disaster_report.store.base import Warehouse

GEOPHYSICAL_INCIDENT_ID: int = 1782000000600
DISEASE_INCIDENT_ID: int = 1782000000700
UNESCAPED_AI_SUMMARY: str = "<script>alert(1)</script>"
GEOPHYSICAL_TIMELINE_SUMMARY: str = "magnitude 6.2 quake reported"


class TestReportDocument:
    def test_build_report_surfaces_incidents_from_read_model(
        self, db_url, clock
    ) -> None:
        from disaster_report.reporting.report import build_report

        document = build_report(build_populated_warehouse(db_url), clock)
        assert {incident.incident_id for incident in document.incidents} == {
            GEOPHYSICAL_INCIDENT_ID,
            DISEASE_INCIDENT_ID,
        }

    def test_build_report_surfaces_timeline_from_read_model(
        self, db_url, clock
    ) -> None:
        from disaster_report.reporting.report import build_report

        document = build_report(build_populated_warehouse(db_url), clock)
        assert {row.summary for row in document.timeline} == {
            GEOPHYSICAL_TIMELINE_SUMMARY,
            UNESCAPED_AI_SUMMARY,
        }

    def test_build_report_surfaces_news_from_read_model(self, db_url, clock) -> None:
        from disaster_report.reporting.report import build_report

        document = build_report(build_populated_warehouse(db_url), clock)
        assert {news.title for news in document.news} == {
            "quake headline",
            "cholera headline",
        }

    def test_report_document_is_json_serialisable(self, db_url, clock) -> None:
        import json

        from disaster_report.reporting.report import build_report

        document = build_report(build_populated_warehouse(db_url), clock)
        json.dumps(_to_jsonable(document))


class TestMarkdownRenderer:
    renderer: MarkdownRenderer

    def test_renders_over_report_document(self, db_url, clock) -> None:
        from disaster_report.reporting.markdown import MarkdownRenderer
        from disaster_report.reporting.report import build_report

        rendered = MarkdownRenderer().render(
            build_report(build_populated_warehouse(db_url), clock)
        )
        assert isinstance(rendered, str) and rendered != ""

    def test_splits_geophysical_and_disease_parts(self, db_url, clock) -> None:
        from disaster_report.reporting.markdown import MarkdownRenderer
        from disaster_report.reporting.report import build_report

        rendered = (
            MarkdownRenderer()
            .render(build_report(build_populated_warehouse(db_url), clock))
            .lower()
        )
        assert "geophysical" in rendered
        assert "disease" in rendered
        assert rendered.index("geophysical") < rendered.index("disease")

    def test_renders_type_subsections_under_categories(self) -> None:
        from disaster_report.models import Incident, IncidentLog
        from disaster_report.reporting.markdown import MarkdownRenderer
        from disaster_report.reporting.report import ReportDocument

        document = ReportDocument(
            generated_at="2026-07-04T12:00:00+00:00",
            incidents=[
                Incident(
                    incident_id=100,
                    incident_category="geophysical",
                    incident_type="Earthquake",
                    name="Test Quake",
                    first_seen_at="2026-07-01",
                    genesis_report_id=1,
                ),
                Incident(
                    incident_id=200,
                    incident_category="disease",
                    incident_type="Cholera",
                    name="Test Cholera",
                    first_seen_at="2026-07-01",
                    genesis_report_id=2,
                ),
            ],
            timeline=[
                IncidentLog(
                    incident_id=100,
                    log_datetime="2026-07-04T12:00:00",
                    summary="quake",
                ),
                IncidentLog(
                    incident_id=200,
                    log_datetime="2026-07-04T12:00:00",
                    summary="cholera",
                ),
            ],
            news=[],
        )
        rendered = MarkdownRenderer().render(document)
        assert "### Earthquake" in rendered
        assert "### Cholera" in rendered

    def test_disease_incident_with_real_who_id_routes_to_disease_not_geophysical(
        self, db_url, clock
    ) -> None:
        from disaster_report.models import IncidentLog, ReportPlace, SourceReport
        from disaster_report.reporting.markdown import MarkdownRenderer
        from disaster_report.reporting.report import build_report
        from disaster_report.store.base import Warehouse

        incident_id = 1782000000800
        warehouse = Warehouse(db_url, clock=clock)
        rid = warehouse.ingest_source_report(
            SourceReport(
                source="WHO",
                source_id="3325c520",
                incident_type="Ebola",
                name="Ebola disease caused by Bundibugyo virus",
                places=[
                    ReportPlace(country_code="CD", subdivision="Ituri", locality="")
                ],
                report_date="2026-07-01",
                raw_fields={},
            )
        )
        warehouse.ingest_report_places(
            rid, [ReportPlace(country_code="CD", subdivision="Ituri", locality="")]
        )
        warehouse.add_report_incident(rid, incident_id)
        warehouse.append_timeline(
            IncidentLog(
                incident_id=incident_id,
                log_datetime="2026-07-04T12:00:00",
                summary="Ebola outbreak developing",
            )
        )
        rendered = MarkdownRenderer().render(build_report(warehouse, clock))
        assert "## Disease" in rendered
        assert "### Ebola" in rendered
        geophysical_section = rendered.split("## Disease")[0]
        assert "Ebola" not in geophysical_section

    def test_escapes_unconstrained_ai_summary_text(self, db_url, clock) -> None:
        from disaster_report.reporting.markdown import MarkdownRenderer
        from disaster_report.reporting.report import build_report

        rendered = MarkdownRenderer().render(
            build_report(build_populated_warehouse(db_url), clock)
        )
        assert UNESCAPED_AI_SUMMARY not in rendered
        assert "&lt;script&gt;" in rendered

    def test_render_surfaces_read_model_timeline(self, db_url, clock) -> None:
        from disaster_report.reporting.markdown import MarkdownRenderer
        from disaster_report.reporting.report import build_report

        rendered = MarkdownRenderer().render(
            build_report(build_populated_warehouse(db_url), clock)
        )
        assert GEOPHYSICAL_TIMELINE_SUMMARY in rendered

    def test_render_path_has_no_ai_dependency(self) -> None:
        import inspect

        from disaster_report.reporting.markdown import MarkdownRenderer

        init_params = inspect.signature(MarkdownRenderer.__init__).parameters
        render_params = inspect.signature(MarkdownRenderer.render).parameters
        assert "ai" not in init_params and "digester" not in init_params
        assert set(render_params) == {"self", "document"}


def build_populated_warehouse(db_url: str) -> Warehouse:
    from disaster_report.models import IncidentLog, NewsItem, ReportPlace, SourceReport
    from disaster_report.store.base import Warehouse

    warehouse = Warehouse(db_url)
    quake_rid = warehouse.ingest_source_report(
        SourceReport(
            source="USGS",
            source_id="us7000abcd",
            incident_type="Earthquake",
            name="Test Quake",
            places=[ReportPlace(country_code="US", subdivision="", locality="")],
            report_date="2026-07-01",
            raw_fields={},
        )
    )
    cholera_rid = warehouse.ingest_source_report(
        SourceReport(
            source="WHO",
            source_id="DON1",
            incident_type="Cholera",
            name="Test Cholera",
            places=[ReportPlace(country_code="IN", subdivision="", locality="")],
            report_date="2026-07-01",
            raw_fields={},
        )
    )
    quake_news_id = warehouse.ingest_news_item(
        NewsItem(
            url="https://news.example/quake",
            title="quake headline",
            body="body",
            published_date="2026-07-03",
            source="example",
            domain="news.example",
            image="",
        )
    )
    cholera_news_id = warehouse.ingest_news_item(
        NewsItem(
            url="https://news.example/cholera",
            title="cholera headline",
            body="body",
            published_date="2026-07-02",
            source="example",
            domain="news.example",
            image="",
        )
    )
    warehouse.assign_news_to_incident(quake_news_id, GEOPHYSICAL_INCIDENT_ID)
    warehouse.add_report_incident(quake_rid, GEOPHYSICAL_INCIDENT_ID)
    warehouse.assign_news_to_incident(cholera_news_id, DISEASE_INCIDENT_ID)
    warehouse.add_report_incident(cholera_rid, DISEASE_INCIDENT_ID)
    warehouse.append_timeline(
        IncidentLog(
            incident_id=GEOPHYSICAL_INCIDENT_ID,
            log_datetime="2026-07-04T12:00:00",
            summary=GEOPHYSICAL_TIMELINE_SUMMARY,
        )
    )
    warehouse.append_timeline(
        IncidentLog(
            incident_id=DISEASE_INCIDENT_ID,
            log_datetime="2026-07-04T12:00:00",
            summary=UNESCAPED_AI_SUMMARY,
        )
    )
    return warehouse


def build_report_document(db_url: str, clock: Callable[[], datetime]) -> ReportDocument:
    from disaster_report.reporting.report import build_report
    from disaster_report.store.base import Warehouse

    return build_report(Warehouse(db_url, clock=clock), clock)


def _to_jsonable(value: object) -> object:
    import dataclasses

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _to_jsonable(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value
