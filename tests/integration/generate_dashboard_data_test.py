from __future__ import annotations

from datetime import datetime, timezone

from scripts.generate_dashboard_data import _resolve_region, generate_md_report


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
