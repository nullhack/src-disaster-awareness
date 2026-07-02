"""Behaviour tests for the classification engine.

One test per behaviour branch of ``classify``; the full ingest/report flow is
exercised end-to-end in ``tests/e2e/``. These unit tests cover the decision
branches the e2e suite does not reach (de-escalation, event_status suppression,
pp-primary gating, tier-A corroboration, the matrix noise fix).
"""
from __future__ import annotations

import pytest

pytest.importorskip("disaster_report.classification", reason="classification not implemented")

from disaster_report import classification as cls
from disaster_report.classification import (
    PANDEMIC_CRITICAL,
    PANDEMIC_HIGH,
    PANDEMIC_MEDIUM,
    PANDEMIC_NONE,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    ClassifyContext,
    classify,
    configure_disease_tiers,
    configure_endemics,
    country_group,
    de_escalate_pandemic_potential,
    derive_initial_severity,
    derive_severity,
)


@pytest.fixture(autouse=True)
def _restore_defaults():
    """configure_disease_tiers/configure_endemics mutate module state; reset after each test."""
    risk = set(cls.DEFAULT_PANDEMIC_RISK_DISEASES)
    concern = set(cls.DEFAULT_OUTBREAK_OF_CONCERN_DISEASES)
    endemic = set(cls.DEFAULT_ENDEMIC_DISEASES)
    yield
    cls._PANDEMIC_RISK_DISEASES.clear()
    cls._PANDEMIC_RISK_DISEASES.update(risk)
    cls._OUTBREAK_OF_CONCERN_DISEASES.clear()
    cls._OUTBREAK_OF_CONCERN_DISEASES.update(concern)
    cls._ENDEMIC_DISEASES.clear()
    cls._ENDEMIC_DISEASES.update(endemic)


class _StubRaw:
    """Minimal stand-in for RawIncident."""

    def __init__(self, source_name: str, raw_fields: dict | None = None) -> None:
        self.source_name = source_name
        self.raw_fields = raw_fields or {}


# --------------------------------------------------------------------------- #
# country_group helper (retained for dim_country seeding)
# --------------------------------------------------------------------------- #

def test_country_group_maps_known_countries_and_unknown_to_c():
    assert country_group("Philippines") == "A"
    assert country_group("PH") == "A"  # iso2 accepted directly
    assert country_group("Australia") == "B"
    assert country_group("Atlantis") == "C"  # unknown -> group C


# --------------------------------------------------------------------------- #
# baseline priority matrix  (the Phase 1.3 noise fix is the key invariant)
# --------------------------------------------------------------------------- #

def test_matrix_low_severity_never_reports_even_for_group_a():
    """Phase 1.3 noise fix: (LOW, A) flipped MEDIUM/True -> LOW/False so trivial
    HealthMap/keyword-leak incidents stop auto-reporting."""
    assert classify(ClassifyContext(level=SEVERITY_LOW, country_group="A")) == ("LOW", False)
    assert classify(ClassifyContext(level=SEVERITY_LOW, country_group="C")) == ("LOW", False)


def test_matrix_high_severity_reports_with_escalating_priority_by_group():
    assert classify(ClassifyContext(level=SEVERITY_CRITICAL, country_group="C")) == ("HIGH", True)
    assert classify(ClassifyContext(level=SEVERITY_HIGH, country_group="A")) == ("HIGH", True)
    assert classify(ClassifyContext(level=SEVERITY_HIGH, country_group="C")) == ("MEDIUM", True)
    assert classify(ClassifyContext(level=SEVERITY_MEDIUM, country_group="C")) == ("LOW", False)


# --------------------------------------------------------------------------- #
# keyword-tier fallback  (only when disease-type AND pandemic_potential is None)
# --------------------------------------------------------------------------- #

def test_pandemic_risk_disease_force_reports_even_at_low_severity():
    # Ebola/Marburg/Nipah are first-case-flag pathogens -> HIGH + report at LOW.
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease", disease_name="Ebola"
    )) == ("HIGH", True)


def test_outbreak_of_concern_reports_only_at_medium_severity_and_above():
    # Cholera/Measles force-report only when severity is already MEDIUM+.
    assert classify(ClassifyContext(
        level=SEVERITY_MEDIUM, country_group="C", incident_type="Disease", disease_name="Cholera"
    )) == ("MEDIUM", True)
    # At LOW severity the outbreak-of-concern tier is silent.
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease", disease_name="Cholera"
    )) == ("LOW", False)


def test_disease_factors_are_gated_on_disease_incident_type():
    # Ebola name present but incident_type physical -> no disease override.
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Earthquake", disease_name="Ebola"
    )) == ("LOW", False)


def test_non_reportable_disease_does_not_override_baseline():
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease", disease_name="Common Cold"
    )) == ("LOW", False)


# --------------------------------------------------------------------------- #
# AI pandemic_potential is the PRIMARY disease signal
# --------------------------------------------------------------------------- #

def test_pandemic_potential_high_or_medium_forces_report():
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease", pandemic_potential=PANDEMIC_HIGH
    )) == ("HIGH", True)
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease", pandemic_potential=PANDEMIC_MEDIUM
    )) == ("MEDIUM", True)


def test_explicit_pandemic_none_suppresses_keyword_fallback():
    """PANDEMIC_NONE (0, AI-set) is distinct from None (not-yet-digested): the
    keyword fallback must NOT run when the AI explicitly assessed NONE."""
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease",
        disease_name="Ebola", pandemic_potential=PANDEMIC_NONE,
    )) == ("LOW", False)


def test_pandemic_potential_ignored_for_physical_incidents():
    assert classify(ClassifyContext(
        level=SEVERITY_MEDIUM, country_group="A", incident_type="Earthquake", pandemic_potential=PANDEMIC_HIGH
    )) == ("MEDIUM", True)  # baseline (2,A); pp gated off


# --------------------------------------------------------------------------- #
# event_status suppression  (final word, disease-type only)
# --------------------------------------------------------------------------- #

def test_non_event_and_elimination_declared_suppress_disease_report():
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease",
        disease_name="Ebola", event_status="non_event",
    ))[1] is False
    assert classify(ClassifyContext(
        level=SEVERITY_MEDIUM, country_group="A", incident_type="Disease",
        event_status="elimination_declared",
    ))[1] is False


def test_event_status_suppression_ignored_for_physical_incidents():
    # A CRITICAL earthquake stays reported even if a stray non_event leaks in.
    assert classify(ClassifyContext(
        level=SEVERITY_CRITICAL, country_group="C", incident_type="Earthquake", event_status="non_event"
    )) == ("HIGH", True)


# --------------------------------------------------------------------------- #
# physical monotonic factors (apply to all incident types)
# --------------------------------------------------------------------------- #

def test_population_threshold_and_floor_force_report():
    # >=100k forces MEDIUM + report; >=10k floor forces report-only.
    assert classify(ClassifyContext(
        level=SEVERITY_MEDIUM, country_group="C", population=100_000
    )) == ("MEDIUM", True)
    assert classify(ClassifyContext(
        level=SEVERITY_MEDIUM, country_group="C", population=10_000
    )) == ("LOW", True)


def test_tier_a_corroboration_forces_report():
    assert classify(ClassifyContext(
        level=SEVERITY_MEDIUM, country_group="C", source_tiers=("A", "A")
    )) == ("MEDIUM", True)


def test_factors_combine_capped_at_high():
    assert classify(ClassifyContext(
        level=SEVERITY_MEDIUM, country_group="C", disease_name="Ebola",
        population=500_000, incident_type="Disease",
    )) == ("HIGH", True)


# --------------------------------------------------------------------------- #
# config-driven tier overrides
# --------------------------------------------------------------------------- #

def test_configure_disease_tiers_override_changes_classification():
    configure_disease_tiers(pandemic_risk=("custompathogen",), outbreak_of_concern=())
    # Ebola no longer in any tier -> baseline.
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease", disease_name="Ebola"
    )) == ("LOW", False)
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease", disease_name="custompathogen"
    )) == ("HIGH", True)


# --------------------------------------------------------------------------- #
# derive_severity: event-based severity at ingest time
# --------------------------------------------------------------------------- #

def test_derive_severity_bands_per_source():
    assert derive_severity(_StubRaw("USGS Earthquakes", {"mag": 6.5})) == SEVERITY_HIGH
    assert derive_severity(_StubRaw("USGS Earthquakes", {"tsunami": 1})) == SEVERITY_CRITICAL
    assert derive_severity(_StubRaw("GDACS", {"alertlevel": "Red"})) == SEVERITY_HIGH
    assert derive_severity(_StubRaw("WHO Disease Outbreak News")) == SEVERITY_MEDIUM
    assert derive_severity(_StubRaw("HealthMap")) == SEVERITY_LOW


def test_derive_initial_severity_picks_max_and_empty_is_low():
    assert derive_initial_severity([
        _StubRaw("WHO Disease Outbreak News"),
        _StubRaw("USGS Earthquakes", {"mag": 6.5}),
    ]) == SEVERITY_HIGH
    assert derive_initial_severity([]) == SEVERITY_LOW


# --------------------------------------------------------------------------- #
# endemic-pathogen de-escalation (COVID/flu/fever never force-report on pp)
# --------------------------------------------------------------------------- #

def test_endemic_diseases_do_not_force_report_on_pandemic_potential():
    # Seasonal/endemic COVID/Flu with AI pp=CRITICAL must NOT escalate.
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease",
        disease_name="COVID-19", pandemic_potential=PANDEMIC_CRITICAL, event_status="ongoing",
    )) == ("LOW", False)
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="A", incident_type="Disease",
        disease_name="Influenza", pandemic_potential=PANDEMIC_HIGH, event_status="new_outbreak",
    )) == ("LOW", False)


def test_non_endemic_pandemic_prone_pathogen_still_force_reports():
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease",
        disease_name="Ebola", pandemic_potential=PANDEMIC_CRITICAL, event_status="new_outbreak",
    )) == ("HIGH", True)


def test_de_escalate_pandemic_potential_clamps_endemic_and_passes_through():
    assert de_escalate_pandemic_potential("COVID-19", PANDEMIC_CRITICAL) == 1  # PANDEMIC_LOW
    assert de_escalate_pandemic_potential("Ebola", PANDEMIC_CRITICAL) == PANDEMIC_CRITICAL
    assert de_escalate_pandemic_potential("COVID-19", None) is None


def test_configure_endemics_override_de_escalates_custom_pathogen():
    configure_endemics({"ebola"})
    assert classify(ClassifyContext(
        level=SEVERITY_LOW, country_group="C", incident_type="Disease",
        disease_name="Ebola", pandemic_potential=PANDEMIC_CRITICAL, event_status="new_outbreak",
    )) == ("LOW", False)
