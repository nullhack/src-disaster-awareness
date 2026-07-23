from __future__ import annotations

from scripts.generate_dashboard_data import _resolve_region


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
