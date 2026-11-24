from __future__ import annotations

from disaster_report._search_keys import derive_repoll_keys, derive_search_keys
from disaster_report.models import SourceReport


def _report(
    *,
    incident_type: str = "El Niño",
    scope: str = "regional",
    region_code: str = "035",
    region_name: str = "South-Eastern Asia",
) -> SourceReport:
    return SourceReport(
        source="MANUAL",
        source_id="manual-1",
        incident_type=incident_type,
        name="El Niño — South-Eastern Asia",
        places=[],
        report_date="2026-09-17",
        raw_fields={},
        scope=scope,
        region_code=region_code,
        region_name=region_name,
    )


class TestRegionalSearchKeys:
    def test_repoll_keys_use_region_name(self) -> None:
        assert derive_repoll_keys(_report()) == [
            "South-Eastern Asia El Niño latest 2026",
            "South-Eastern Asia El Niño 2026",
        ]

    def test_search_keys_use_region_name_when_no_places(self) -> None:
        assert derive_search_keys(_report()) == (
            "",
            "El Niño South-Eastern Asia 2026",
        )

    def test_repoll_keys_fall_back_to_type_for_global_scope(self) -> None:
        assert derive_repoll_keys(
            _report(scope="global", region_code="", region_name="")
        ) == ["El Niño latest 2026", "El Niño 2026"]

    def test_repoll_keys_empty_without_type_or_region(self) -> None:
        assert derive_repoll_keys(
            _report(incident_type="", region_code="", region_name="")
        ) == []
