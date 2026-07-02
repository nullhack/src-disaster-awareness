"""Behavior tests for the deterministic deriver.

The deriver replaces AI-authored canonical_name/search_keys so every incident
has usable, date-anchored keys immediately at ingest (even pre-AI or on
digest failure). These tests pin the date-anchoring + dedup/cap contracts.
"""
from __future__ import annotations

from datetime import date

from disaster_report.deriver import DeriveInput, derive_canonical_name, derive_search_keys


def test_physical_search_keys_are_date_anchored_and_capped():
    ctx = DeriveInput(
        incident_type="Earthquake",
        country="Philippines",
        event_date=date(2026, 6, 29),
        place="near Sarangani, Philippines",
    )
    keys = derive_search_keys(ctx)
    assert len(keys) <= 3
    assert all("2026" in k for k in keys), "every key must carry the event year"
    assert keys[0] == "Sarangani earthquake June 2026"  # place-first, most specific
    assert "Philippines earthquake June 2026" in keys   # country fallback present


def test_disease_search_keys_include_disease_country_year():
    ctx = DeriveInput(
        incident_type="Disease",
        country="Uganda",
        event_date=date(2026, 6, 29),
        disease_name="Ebola",
    )
    keys = derive_search_keys(ctx)
    assert keys[0] == "Ebola Uganda outbreak 2026"
    assert any("Ebola" in k and "Uganda" in k for k in keys)
    assert "Ebola outbreak cases deaths" in keys  # date-less fallback key always present


def test_disease_search_keys_drop_unknown_country():
    """Multi-country WHO DONs normalize to country "Unknown"; the literal token
    must be dropped from keys and the canonical name — DDG returns nothing for
    "Disease Unknown outbreak 2025" and the token appears in no real article."""
    ctx = DeriveInput(
        incident_type="Disease",
        country="Unknown",
        event_date=date(2025, 11, 1),
        disease_name="Diphtheria",
    )
    keys = derive_search_keys(ctx)
    assert keys, "must still produce keys"
    assert not any("unknown" in k.lower() for k in keys), "no key may carry the Unknown token"
    assert keys[0] == "Diphtheria outbreak 2025"
    assert "Diphtheria November 2025" in keys
    assert derive_canonical_name(ctx) == "Diphtheria outbreak November 2025"


def test_canonical_name_physical_uses_cleaned_place():
    ctx = DeriveInput(
        incident_type="Earthquake",
        country="Philippines",
        event_date=date(2026, 6, 29),
        place="near Sarangani, Philippines",
    )
    assert derive_canonical_name(ctx) == "Earthquake Sarangani June 2026"


def test_canonical_name_disease_includes_outbreak_country_month():
    ctx = DeriveInput(
        incident_type="Disease",
        country="Uganda",
        event_date=date(2026, 6, 29),
        disease_name="Ebola",
    )
    assert derive_canonical_name(ctx) == "Ebola outbreak Uganda June 2026"


def test_place_cleaning_strips_near_prefix_and_comma_tail():
    # place cleaning reduces USGS-style "near X, Y" and strips filler prefixes.
    # "near Sarangani, Philippines" -> "Sarangani" (comma split + "near " strip).
    keys = derive_search_keys(
        DeriveInput(
            incident_type="Earthquake",
            country="Philippines",
            event_date=date(2026, 6, 29),
            place="near Sarangani, Philippines",
        )
    )
    assert keys[0] == "Sarangani earthquake June 2026"
    # the country tail ("Philippines") is dropped from the locality, not duplicated.
    assert not any(", " in k for k in keys)


def test_place_cleaning_recursive_filler_strip():
    # Recursive prefix strip: "of the coast of Honshu" reduces past filler words
    # but keeps the locality ("Honshu") in the resulting key.
    keys = derive_search_keys(
        DeriveInput(
            incident_type="Earthquake",
            country="Japan",
            event_date=date(2026, 6, 29),
            place="of the coast of Honshu, Japan",
        )
    )
    assert any("Honshu" in k for k in keys)


def test_missing_event_date_still_yields_usable_keys():
    ctx = DeriveInput(
        incident_type="Earthquake",
        country="Philippines",
        event_date=None,
        place="near Sarangani, Philippines",
    )
    keys = derive_search_keys(ctx)
    assert keys, "must produce at least one key even without a date"
    assert all("Sarangani" in k or "Philippines" in k for k in keys)


def test_keys_deduplicated():
    # place == country so the place-key and country-key would collide -> deduped.
    ctx = DeriveInput(
        incident_type="Earthquake",
        country="Japan",
        event_date=date(2026, 6, 29),
        place="Japan",
    )
    keys = derive_search_keys(ctx)
    assert len(keys) == len(set(keys)), "keys must be de-duplicated"
