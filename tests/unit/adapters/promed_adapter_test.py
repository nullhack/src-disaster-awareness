"""Tests for ProMED adapter module."""

from disaster_surveillance_reporter.adapters.promed import ProMEDAdapter


def test_given_promed_adapter_when_source_name_then_should_return_promed():
    """
    Given: A ProMEDAdapter instance
    When: source_name property is accessed
    Then: Should return 'ProMED'
    """
    adapter = ProMEDAdapter()
    assert adapter.source_name == "ProMED"


def test_given_promed_adapter_when_fetch_with_mock_then_should_return_incidents():
    """
    Given: A ProMEDAdapter in mock mode
    When: fetch() is called
    Then: Should return list of RawIncidentData
    """
    adapter = ProMEDAdapter(mock_mode=True)
    result = adapter.fetch()

    assert isinstance(result, list)
    assert len(result) == 5


def test_given_promed_adapter_when_fetch_then_should_have_disease_types():
    """
    Given: A ProMEDAdapter in mock mode
    When: fetch() is called
    Then: Incidents should have disease types
    """
    adapter = ProMEDAdapter(mock_mode=True)
    result = adapter.fetch()

    diseases = {inc.disaster_type for inc in result}
    assert "Measles" in diseases
    assert "Lassa Fever" in diseases


def test_given_promed_adapter_when_fetch_then_should_have_countries():
    """
    Given: A ProMEDAdapter in mock mode
    When: fetch() is called
    Then: Incidents should have countries
    """
    adapter = ProMEDAdapter(mock_mode=True)
    result = adapter.fetch()

    countries = {inc.country for inc in result}
    assert "Peru" in countries
    assert "Nigeria" in countries


def test_given_promed_adapter_when_fetch_then_should_have_raw_fields():
    """
    Given: A ProMEDAdapter in mock mode
    When: fetch() is called
    Then: RawIncidentData should have raw_fields with cases/deaths
    """
    adapter = ProMEDAdapter(mock_mode=True)
    result = adapter.fetch()

    assert result[0].raw_fields is not None
    assert "cases" in result[0].raw_fields
    assert "deaths" in result[0].raw_fields


def test_given_promed_adapter_when_fetch_real_then_should_return_empty():
    """
    Given: A ProMEDAdapter in real mode
    When: fetch() is called
    Then: Should return empty list (real fetch not implemented)
    """
    adapter = ProMEDAdapter(mock_mode=False)
    result = adapter.fetch()

    assert result == []
