"""Deterministic severity derivation for geophysical incidents.

Covers the six web-verified ``gold'' earthquakes plus the guard rails agreed
during design (magnitude alone never forces CRITICAL; significance < 600 is
ignored; GDACS population is intentionally not a severity factor).
"""
from __future__ import annotations

from disaster_report.classification import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    GeophysicalFacts,
    derive_geophysical_severity,
)


def _derive(**kwargs: object):
    return derive_geophysical_severity(GeophysicalFacts(**kwargs))


def test_news_confirms_high_impact_aftershock_to_critical() -> None:
    # 20260629-VE-EQ: M4.6 aftershock of the M7.2 Venezuela catastrophe (1.7k+
    # deaths). Instrumentation is low but heavy news coverage confirms impact.
    assert _derive(max_magnitude=4.6, max_significance=357, news_count=68) == SEVERITY_CRITICAL


def test_news_confirms_to_high() -> None:
    # 20260629-PH-EQ: M5.2 aftershock of the M7.8 Sarangani event.
    assert _derive(max_magnitude=5.2, max_significance=416, news_count=19) == SEVERITY_HIGH


def test_magnitude_six_without_impact_is_medium() -> None:
    # 20260630-MX-EQ: M6.0 Gulf of California, no casualties/damage.
    assert _derive(max_magnitude=6.0, max_significance=559, news_count=8) == SEVERITY_MEDIUM


def test_gdacs_green_felt_quakes_are_medium() -> None:
    # 20260702-GR-EQ (Karpathos) and 20260702-GS-EQ (South Sandwich, uninhabited):
    # moderate magnitude, no impact, no news -> MEDIUM, never HIGH.
    assert _derive(max_magnitude=5.2, max_significance=418) == SEVERITY_MEDIUM
    assert _derive(max_magnitude=5.3, max_significance=432) == SEVERITY_MEDIUM


def test_mag_seven_does_not_force_critical_without_impact() -> None:
    # Magnitude alone caps at HIGH; CRITICAL requires a confirmed impact signal.
    assert _derive(max_magnitude=7.4, max_significance=900) == SEVERITY_HIGH


def test_significance_below_six_hundred_ignored() -> None:
    # sig>=400 used to over-fire HIGH on GDACS-Green no-impact quakes (the bug).
    assert _derive(max_magnitude=5.2, max_significance=418) == SEVERITY_MEDIUM
    assert _derive(max_significance=599) == SEVERITY_LOW
    assert _derive(max_significance=600) == SEVERITY_HIGH


def test_tsunami_floors_high() -> None:
    assert _derive(max_magnitude=5.5, tsunami=True) == SEVERITY_HIGH


def test_gdacs_alertlevel_ladder() -> None:
    assert _derive(gdacs_alertlevel="Red") == SEVERITY_HIGH
    assert _derive(gdacs_alertlevel="Orange") == SEVERITY_MEDIUM
    assert _derive(gdacs_alertlevel="Green") == SEVERITY_LOW


def test_news_ladder() -> None:
    assert _derive(news_count=50) == SEVERITY_CRITICAL
    assert _derive(news_count=15) == SEVERITY_HIGH
    assert _derive(news_count=5) == SEVERITY_MEDIUM
    assert _derive(news_count=4) == SEVERITY_LOW


def test_no_data_is_low() -> None:
    assert _derive() == SEVERITY_LOW


def test_combines_as_max_of_ladders() -> None:
    # M6.5 (MEDIUM) + GDACS Orange (MEDIUM) + 20 news (HIGH) -> HIGH.
    assert (
        _derive(max_magnitude=6.5, gdacs_alertlevel="Orange", news_count=20)
        == SEVERITY_HIGH
    )
