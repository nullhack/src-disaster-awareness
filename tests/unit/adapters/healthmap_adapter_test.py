"""Tests for HealthMapAdapter."""


from disaster_surveillance_reporter.adapters import HealthMapAdapter, RawIncidentData


def test_given_healthmap_adapter_when_source_name_then_should_return_healthmap():
    """
    Given: A HealthMapAdapter instance
    When: source_name property is accessed
    Then: Should return "HealthMap"
    """
    adapter = HealthMapAdapter()
    assert adapter.source_name == "HealthMap"


def test_given_healthmap_adapter_when_fetch_with_mock_then_should_return_incidents():
    """
    Given: A HealthMapAdapter in mock mode
    When: fetch() is called
    Then: Should return list of RawIncidentData with disease surveillance data
    """
    adapter = HealthMapAdapter(mock_mode=True)
    incidents = adapter.fetch()

    assert isinstance(incidents, list)
    assert len(incidents) == 5

    # Check first incident
    incident = incidents[0]
    assert isinstance(incident, RawIncidentData)
    assert incident.source_name == "HealthMap"
    assert incident.disaster_type in ["H1N1", "Measles", "Dengue", "Cholera", "MERS"]


def test_given_healthmap_adapter_when_fetch_with_mock_then_should_have_disease_data():
    """
    Given: A HealthMapAdapter in mock mode
    When: fetch() is called
    Then: Should return incidents with raw_fields containing disease data
    """
    adapter = HealthMapAdapter(mock_mode=True)
    incidents = adapter.fetch()

    for incident in incidents:
        assert "cases" in incident.raw_fields or "deaths" in incident.raw_fields


def test_given_healthmap_adapter_when_fetch_real_then_should_return_empty():
    """
    Given: A HealthMapAdapter with mock_mode=False
    When: fetch() is called (real fetch not implemented)
    Then: Should return empty list (stub implementation)
    """
    adapter = HealthMapAdapter(mock_mode=False)
    incidents = adapter.fetch()

    assert isinstance(incidents, list)
    assert len(incidents) == 0
