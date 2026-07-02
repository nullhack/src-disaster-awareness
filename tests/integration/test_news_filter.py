from __future__ import annotations

from disaster_report.news_filter import is_relevant
from disaster_report.sources.base import RawArticle


def _art(headline: str, body: str = "") -> RawArticle:
    return RawArticle(
        source_name="DDG",
        headline=headline,
        body=body,
        url=f"https://n/{abs(hash(headline))}",
        outlet="Reuters",
        published_date="2026-06-29T08:00:00Z",
    )


def test_physical_single_token_match_still_relevant():
    """Earthquake articles match on a single type token (physical track unchanged)."""
    assert is_relevant(
        _art("Magnitude 6 earthquake strikes Philippines coast"),
        disaster_type="Earthquake",
        country="Philippines",
        incident_name="Sarangani Earthquake",
    )


def test_physical_flood_receding_not_rejected_by_stoplist():
    """The junk stoplist is disease-only; 'flood receding' stays relevant."""
    assert is_relevant(
        _art("Flood receding in Bangladesh after peak"),
        disaster_type="Flood",
        country="Bangladesh",
        incident_name="Bangladesh Flood",
    )


def test_bare_virus_token_no_longer_matches_disease():
    """Bare 'virus' removed from disease synonyms — computer/USB virus is noise."""
    assert not is_relevant(
        _art("Computer virus spreads on USB sticks"),
        disaster_type="Disease",
        country="Germany",
        incident_name="Virus on USB sticks",
    )


def test_bare_fever_token_no_longer_matches_disease():
    """Bare 'fever' removed — election/sports fever is noise."""
    assert not is_relevant(
        _art("Election fever grips the nation"),
        disaster_type="Disease",
        country="Germany",
        incident_name="Election fever",
    )


def test_disease_name_hit_matches():
    """A specific disease-name token always qualifies (single-token pass)."""
    assert is_relevant(
        _art("Cholera outbreak hits Nigeria"),
        disaster_type="Disease",
        country="Nigeria",
        incident_name="Cholera Outbreak Nigeria",
        disease="Cholera",
    )


def test_disease_two_token_overlap_matches_without_disease_name():
    """Without a specific disease, >=2 disease-track tokens still match."""
    assert is_relevant(
        _art("Disease outbreak reported in Nigeria"),
        disaster_type="Disease",
        country="Nigeria",
        incident_name="Disease Outbreak",
    )


def test_disease_single_generic_token_does_not_match():
    """A single generic disease token (e.g. just 'outbreak' in an unrelated story)
    must NOT pass on its own."""
    assert not is_relevant(
        _art("Outbreak of peace in the region"),
        disaster_type="Disease",
        country="Germany",
        incident_name="Unrelated story",
    )


def test_stoplist_polio_free_rejected():
    assert not is_relevant(
        _art("Gujarat declared polio-free after milestone"),
        disaster_type="Disease",
        country="India",
        incident_name="Gujarat polio-free",
        disease="Polio",
    )


def test_stoplist_cases_fall_rejected():
    assert not is_relevant(
        _art("Dengue cases fall 56 percent this year"),
        disaster_type="Disease",
        country="Brazil",
        incident_name="Dengue cases fall",
        disease="Dengue",
    )


def test_stoplist_computer_virus_rejected():
    assert not is_relevant(
        _art("New computer virus detected in the wild"),
        disaster_type="Disease",
        country="Germany",
        incident_name="Computer virus",
        disease="Virus",
    )


def test_place_mismatch_still_rejects():
    """Even with a disease-name hit, a place mismatch rejects the article."""
    assert not is_relevant(
        _art("Cholera confirmed in Lima hospitals"),
        disaster_type="Disease",
        country="Nigeria",
        incident_name="Cholera Outbreak Nigeria",
        disease="Cholera",
    )


def test_disease_state_name_matches_country_incident():
    """Local news names the state, not the country ("Kerala" for India); the
    subdivision-aware place_t must keep such a disease article."""
    assert is_relevant(
        _art("Fresh Nipah case reported in Kerala"),
        disaster_type="Disease",
        country="India",
        incident_name="Nipah outbreak India June 2026",
        disease="Nipah",
    )
    # And it still rejects a same-disease article from a different country.
    assert not is_relevant(
        _art("Fresh Nipah case reported in Kerala"),
        disaster_type="Disease",
        country="Bangladesh",
        incident_name="Nipah outbreak Bangladesh",
        disease="Nipah",
    )


def test_unknown_country_disease_relies_on_disease_hit():
    """A multi-country outbreak (country=Unknown) has no usable place token;
    place_match is relaxed so a disease-name hit alone qualifies."""
    assert is_relevant(
        _art("Diphtheria outbreak reported across multiple regions"),
        disaster_type="Disease",
        country="Unknown",
        incident_name="Diphtheria outbreak Unknown",
        disease="Diphtheria",
    )


def test_unknown_country_without_disease_hit_still_rejects():
    """Relaxing place_match for Unknown country must not let non-disease noise
    through — type_match (disease_hit or >=2 tokens) still gates the article."""
    assert not is_relevant(
        _art("Outbreak of peace in the region"),
        disaster_type="Disease",
        country="Unknown",
        incident_name="Unrelated story",
        disease="Diphtheria",
    )
