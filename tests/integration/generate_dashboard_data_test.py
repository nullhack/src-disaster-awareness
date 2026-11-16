from __future__ import annotations

from datetime import datetime, timezone

from scripts.generate_dashboard_data import (
    _resolve_region,
    generate_md_report,
    select_key_links,
)
from disaster_report.sources.gdacs import _resolve_gdacs_link


class TestResolveRegion:
    def test_global_in_name_returns_global(self) -> None:
        assert _resolve_region("Dengue Global 2024-05-30", None, True) == "Global"

    def test_disease_without_global_in_name_returns_global(self) -> None:
        assert _resolve_region("Ebola Uganda 2025-09-05", None, True) == "Global"

    def test_drought_with_europe_in_summary_returns_europe(self) -> None:
        summary = "Severe drought and heat causing water shortages in the Netherlands."
        assert _resolve_region("Drought 2025-12-21", summary, False) == "Europe"

    def test_non_disease_no_summary_no_global_returns_unknown(self) -> None:
        assert _resolve_region("Drought 2025-12-21", None, False) == "Unknown"

    def test_disease_with_country_in_summary_returns_that_region(self) -> None:
        summary = "Outbreak reported in Japan with rising case counts."
        assert _resolve_region("Disease Japan 2025-01-01", summary, True) == "Asia"


class TestResolveGdacsLink:
    def test_link_field_used_directly_when_present(self) -> None:
        rf: dict[str, object] = {"link": "https://www.gdacs.org/report.aspx?eventid=1&episodeid=2&eventtype=EQ"}
        assert _resolve_gdacs_link(rf) == rf["link"]

    def test_url_dict_report_subkey_used_when_no_link(self) -> None:
        rf: dict[str, object] = {"url": {"report": "https://www.gdacs.org/report.aspx?eventid=2&episodeid=3&eventtype=WF"}}
        assert _resolve_gdacs_link(rf) == "https://www.gdacs.org/report.aspx?eventid=2&episodeid=3&eventtype=WF"

    def test_constructed_from_eventid_and_episodeid_for_degenerate_drought(self) -> None:
        rf: dict[str, object] = {"alertlevel": "Green", "severity": "Minor", "population": 0, "episodeid": "14", "eventid": "1018332", "eventtype": "DR"}
        url = _resolve_gdacs_link(rf)
        assert url == "https://www.gdacs.org/report.aspx?eventid=1018332&episodeid=14&eventtype=DR"

    def test_eventid_in_raw_fields_preferred(self) -> None:
        rf: dict[str, object] = {"eventid": "999", "episodeid": "5", "eventtype": "FL"}
        url = _resolve_gdacs_link(rf)
        assert "eventid=999" in url
        assert "episodeid=5" in url

    def test_returns_empty_when_nothing_reconstructable(self) -> None:
        rf: dict[str, object] = {}
        assert _resolve_gdacs_link(rf) == ""


class TestSelectKeyLinks:
    def test_uses_latest_official_and_two_relevant_log_news(self) -> None:
        source_links = [
            {"type": "WHO", "label": "Old", "url": "https://who/old", "date": "2026-11-01"},
            {"type": "WHO", "label": "New", "url": "https://who/new", "date": "2026-11-10"},
        ]
        logs = [{
            "log_date": "2026-11-11",
            "summary": "",
            "news": [
                {
                    "headline": "Ebola cases rise in DR Congo",
                    "url": "https://news/1",
                    "outlet": "Reuters",
                    "published_date": "2026-11-11",
                },
                {
                    "headline": "Ebola update",
                    "url": "https://news/2",
                    "outlet": "AP",
                    "published_date": "2026-11-10",
                },
                {
                    "headline": "Unrelated celebrity news",
                    "url": "https://news/3",
                    "outlet": "MSN",
                    "published_date": "2026-11-12",
                },
            ],
        }]
        incident = {
            "canonical_name": "Ebola Kinshasa, DR Congo 2026-11-01",
            "country": "DR Congo",
            "physical": {},
            "search_keys": [],
        }
        links = select_key_links(source_links, logs, [], incident)
        assert [link["kind"] for link in links] == ["official", "news", "news"]
        assert links[0]["url"] == "https://who/new"
        assert {link["url"] for link in links[1:]} == {
            "https://news/1",
            "https://news/2",
        }

    def test_fills_news_from_older_logs(self) -> None:
        logs = [
            {
                "log_date": "2026-11-09",
                "summary": "",
                "news": [
                    {
                        "headline": "Ebola cases reported",
                        "url": "https://news/1",
                        "outlet": "Reuters",
                        "published_date": "2026-11-09",
                    },
                    {
                        "headline": "Ebola response grows",
                        "url": "https://news/2",
                        "outlet": "AP",
                        "published_date": "2026-11-09",
                    },
                ],
            },
            {
                "log_date": "2026-11-11",
                "summary": "",
                "news": [
                    {
                        "headline": "Ebola latest update",
                        "url": "https://news/3",
                        "outlet": "BBC",
                        "published_date": "2026-11-11",
                    },
                ],
            },
        ]
        incident = {
            "canonical_name": "Ebola Kinshasa, DR Congo 2026-11-01",
            "country": "DR Congo",
            "physical": {},
            "search_keys": [],
        }
        links = select_key_links([], logs, [], incident)
        assert len(links) == 3

    def test_manual_incident_shows_three_news(self) -> None:
        news = [
            {
                "headline": "Flood hits Greece",
                "url": "https://news/1",
                "outlet": "Reuters",
                "published_date": "2026-11-11",
            },
            {
                "headline": "Greece flood worsens",
                "url": "https://news/2",
                "outlet": "AP",
                "published_date": "2026-11-10",
            },
            {
                "headline": "Flood damage assessed",
                "url": "https://news/3",
                "outlet": "BBC",
                "published_date": "2026-11-09",
            },
        ]
        incident = {
            "canonical_name": "Flood Greece 2026-11-01",
            "country": "Greece",
            "physical": {},
            "search_keys": [],
        }
        links = select_key_links([], [], news, incident)
        assert len(links) == 3
        assert all(link["kind"] == "news" for link in links)

    def test_term_match_beats_newer_unrelated_news(self) -> None:
        news = [
            {
                "headline": "Ebola outbreak worsens",
                "url": "https://news/1",
                "outlet": "Reuters",
                "published_date": "2026-11-01",
            },
            {
                "headline": "Celebrity news",
                "url": "https://news/2",
                "outlet": "AP",
                "published_date": "2026-11-12",
            },
        ]
        incident = {
            "canonical_name": "Ebola Kinshasa, DR Congo 2026-11-01",
            "country": "DR Congo",
            "physical": {},
            "search_keys": [],
        }
        links = select_key_links([], [], news, incident)
        assert links[0]["url"] == "https://news/1"

    def test_dedupes_same_headline(self) -> None:
        news = [
            {
                "headline": "Flood hits Greece",
                "url": "https://news/1",
                "outlet": "Reuters",
                "published_date": "2026-11-11",
            },
            {
                "headline": "Flood hits Greece",
                "url": "https://news/2",
                "outlet": "AP",
                "published_date": "2026-11-10",
            },
            {
                "headline": "Greece flood worsens",
                "url": "https://news/3",
                "outlet": "BBC",
                "published_date": "2026-11-09",
            },
        ]
        incident = {
            "canonical_name": "Flood Greece 2026-11-01",
            "country": "Greece",
            "physical": {},
            "search_keys": [],
        }
        links = select_key_links([], [], news, incident)
        assert len(links) == 2

    def test_fills_short_news_pool_with_additional_official(self) -> None:
        source_links = [
            {"type": "USGS", "label": "Older", "url": "https://usgs/old", "date": "2026-11-01"},
            {"type": "USGS", "label": "Newer", "url": "https://usgs/new", "date": "2026-11-10"},
            {"type": "USGS", "label": "Oldest", "url": "https://usgs/oldest", "date": "2026-10-01"},
        ]
        incident = {
            "canonical_name": "Earthquake Vanuatu 2026-11-01",
            "country": "Vanuatu",
            "physical": {},
            "search_keys": [],
        }
        links = select_key_links(source_links, [], [], incident)
        assert len(links) == 3
        assert all(link["kind"] == "official" for link in links)


def _make_incident(
    incident_id: str = "x",
    name: str = "Earthquake M7.5 Yumare, Venezuela 2026-06-24",
    severity: str = "CRITICAL",
    region: str = "Americas",
    country: str = "Venezuela",
    is_disease: bool = False,
    logs: list[dict] | None = None,
) -> dict:
    return {
        "incident_id": incident_id,
        "canonical_name": name,
        "incident_type": "Earthquake" if not is_disease else "Disease",
        "severity": severity,
        "news_total": 3,
        "country": country,
        "region": region,
        "is_disease": is_disease,
        "logs": logs or [],
    }


class TestGenerateMdReportDayPrimary:
    def test_day_primary_shows_3_most_recent_days(self) -> None:
        inc = _make_incident(logs=[
            {"log_date": "2026-06-20T10:00:00+00:00", "summary": "Day 1.", "news": ["a"]},
            {"log_date": "2026-06-22T10:00:00+00:00", "summary": "Day 2.", "news": ["b"]},
            {"log_date": "2026-06-24T10:00:00+00:00", "summary": "Day 3.", "news": ["c"]},
            {"log_date": "2026-06-26T10:00:00+00:00", "summary": "Day 4.", "news": ["d"]},
        ])
        digest = {"summary": {"reportable_total": 1, "disease_outbreaks": 0, "countries_affected": 1, "news_total": 4, "critical": 1, "high": 0, "medium": 0, "low": 0}, "incidents": [inc]}
        md = generate_md_report(digest, datetime(2026, 6, 26, tzinfo=timezone.utc))
        assert "## 2026-06-26" in md
        assert "## 2026-06-24" in md
        assert "## 2026-06-22" in md
        assert "## 2026-06-20" not in md

    def test_each_incident_shows_only_that_day_log(self) -> None:
        inc = _make_incident(logs=[
            {"log_date": "2026-06-24T10:00:00+00:00", "summary": "First log.", "news": ["a", "b"]},
            {"log_date": "2026-06-26T10:00:00+00:00", "summary": "Second log.", "news": ["c"]},
        ])
        digest = {"summary": {"reportable_total": 1, "disease_outbreaks": 0, "countries_affected": 1, "news_total": 3, "critical": 1, "high": 0, "medium": 0, "low": 0}, "incidents": [inc]}
        md = generate_md_report(digest, datetime(2026, 6, 26, tzinfo=timezone.utc))
        day_26 = md.split("## 2026-06-26")[1].split("## 2026-06-24")[0]
        assert "First log." not in day_26
        assert "Second log." in day_26

    def test_empty_days_skipped(self) -> None:
        inc = _make_incident(logs=[
            {"log_date": "2026-06-24T10:00:00+00:00", "summary": "Day A.", "news": ["a"]},
        ])
        digest = {"summary": {"reportable_total": 1, "disease_outbreaks": 0, "countries_affected": 1, "news_total": 1, "critical": 1, "high": 0, "medium": 0, "low": 0}, "incidents": [inc]}
        md = generate_md_report(digest, datetime(2026, 6, 26, tzinfo=timezone.utc))
        assert "## 2026-06-25" not in md
        assert "## 2026-06-26" not in md

    def test_incidents_sorted_by_severity_within_day(self) -> None:
        inc_crit = _make_incident(incident_id="c", name="Critical EQ Venezuela 2026-06-24", severity="CRITICAL", logs=[{"log_date": "2026-06-26T10:00:00+00:00", "summary": "Critical.", "news": ["a"]}])
        inc_med = _make_incident(incident_id="m", name="Medium EQ Chile 2026-06-24", severity="MEDIUM", region="Americas", country="Chile", logs=[{"log_date": "2026-06-26T10:00:00+00:00", "summary": "Medium.", "news": ["b"]}])
        digest = {"summary": {"reportable_total": 2, "disease_outbreaks": 0, "countries_affected": 2, "news_total": 2, "critical": 1, "high": 0, "medium": 1, "low": 0}, "incidents": [inc_med, inc_crit]}
        md = generate_md_report(digest, datetime(2026, 6, 26, tzinfo=timezone.utc))
        crit_pos = md.index("Critical EQ Venezuela")
        med_pos = md.index("Medium EQ Chile")
        assert crit_pos < med_pos

    def test_date_stripped_from_incident_heading(self) -> None:
        inc = _make_incident(logs=[{"log_date": "2026-06-26T10:00:00+00:00", "summary": "Log.", "news": ["a"]}])
        digest = {"summary": {"reportable_total": 1, "disease_outbreaks": 0, "countries_affected": 1, "news_total": 1, "critical": 1, "high": 0, "medium": 0, "low": 0}, "incidents": [inc]}
        md = generate_md_report(digest, datetime(2026, 6, 26, tzinfo=timezone.utc))
        assert "#### Earthquake M7.5 Yumare, Venezuela" in md
        assert "2026-06-24" not in md.split("\n")[0]

    def test_new_badge_on_first_log_date(self) -> None:
        inc = _make_incident(logs=[
            {"log_date": "2026-06-24T10:00:00+00:00", "summary": "First.", "news": ["a"]},
            {"log_date": "2026-06-26T10:00:00+00:00", "summary": "Second.", "news": ["b"]},
        ])
        digest = {"summary": {"reportable_total": 1, "disease_outbreaks": 0, "countries_affected": 1, "news_total": 2, "critical": 1, "high": 0, "medium": 0, "low": 0}, "incidents": [inc]}
        md = generate_md_report(digest, datetime(2026, 6, 26, tzinfo=timezone.utc))
        day_24_section = md.split("## 2026-06-24")[1]
        day_26_section = md.split("## 2026-06-26")[1].split("## 2026-06-24")[0]
        assert "[NEW]" in day_24_section
        assert "[NEW]" not in day_26_section

    def test_region_subheadings_present(self) -> None:
        inc_americas = _make_incident(incident_id="a", name="EQ Venezuela 2026-06-24", region="Americas", country="Venezuela", logs=[{"log_date": "2026-06-26T10:00:00+00:00", "summary": "VZ.", "news": ["a"]}])
        inc_asia = _make_incident(incident_id="b", name="Flood China 2026-06-24", severity="MEDIUM", region="Asia", country="China", logs=[{"log_date": "2026-06-26T10:00:00+00:00", "summary": "CN.", "news": ["b"]}])
        digest = {"summary": {"reportable_total": 2, "disease_outbreaks": 0, "countries_affected": 2, "news_total": 2, "critical": 1, "high": 0, "medium": 1, "low": 0}, "incidents": [inc_americas, inc_asia]}
        md = generate_md_report(digest, datetime(2026, 6, 26, tzinfo=timezone.utc))
        assert "### Americas" in md
        assert "### Asia" in md

    def test_section_header_says_recorded_on_this_date(self) -> None:
        inc = _make_incident(logs=[{"log_date": "2026-06-26T10:00:00+00:00", "summary": "Log.", "news": ["a"]}])
        digest = {"summary": {"reportable_total": 1, "disease_outbreaks": 0, "countries_affected": 1, "news_total": 1, "critical": 1, "high": 0, "medium": 0, "low": 0}, "incidents": [inc]}
        md = generate_md_report(digest, datetime(2026, 6, 26, tzinfo=timezone.utc))
        assert "## 2026-06-26" in md
