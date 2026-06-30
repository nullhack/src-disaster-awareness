from __future__ import annotations

import pytest

pytest.importorskip("disaster_report.classification", reason="classification not implemented")

from disaster_report.classification import classify, country_group


def test_country_group_returns_A_for_philippines():
    assert country_group("Philippines") == "A"


def test_country_group_returns_B_for_japan_region_or_oceania():
    assert country_group("Australia") == "B"


def test_country_group_returns_C_for_unknown_country():
    assert country_group("Atlantis") == "C"


@pytest.mark.parametrize(
    "level,country,expected_priority,expected_report",
    [
        (4, "Philippines", "HIGH", True),
        (4, "Atlantis", "HIGH", True),
        (3, "Philippines", "HIGH", True),
        (3, "Australia", "MEDIUM", True),
        (2, "Philippines", "MEDIUM", True),
        (2, "Germany", "LOW", False),
        (1, "Philippines", "MEDIUM", True),
        (1, "Germany", "LOW", False),
    ],
)
def test_classify_uses_priority_matrix(level, country, expected_priority, expected_report):
    priority, should_report = classify(level, country)
    assert priority == expected_priority
    assert should_report is expected_report


def test_classify_accepts_iso2_directly():
    assert country_group("PH") == "A"
    assert country_group("AU") == "B"
