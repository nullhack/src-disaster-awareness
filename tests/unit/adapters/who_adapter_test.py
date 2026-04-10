"""Tests for WHOAdapter."""


from disaster_surveillance_reporter.adapters import RawIncidentData, WHOAdapter


def test_given_who_adapter_when_source_name_then_should_return_who():
    """
    Given: A WHOAdapter instance
    When: source_name property is accessed
    Then: Should return "WHO"
    """
    adapter = WHOAdapter()
    assert adapter.source_name == "WHO"


def test_given_who_adapter_when_fetch_with_mock_then_should_return_incidents():
    """
    Given: A WHOAdapter in mock mode
    When: fetch() is called
    Then: Should return list of RawIncidentData with health emergencies
    """
    adapter = WHOAdapter(mock_mode=True)
    incidents = adapter.fetch()

    assert isinstance(incidents, list)
    assert len(incidents) == 5

    incident = incidents[0]
    assert isinstance(incident, RawIncidentData)
    assert incident.source_name == "WHO"


def test_given_who_adapter_when_fetch_with_mock_then_should_have_health_data():
    """
    Given: A WHOAdapter in mock mode
    When: fetch() is called
    Then: Should return incidents with raw_fields containing health data
    """
    adapter = WHOAdapter(mock_mode=True)
    incidents = adapter.fetch()

    for incident in incidents:
        assert "disease" in incident.raw_fields


def test_given_who_adapter_when_fetch_real_then_should_return_empty():
    """
    Given: A WHOAdapter with mock_mode=False
    When: fetch() is called (real fetch not implemented)
    Then: Should return empty list (stub implementation)
    """
    adapter = WHOAdapter(mock_mode=False)
    incidents = adapter.fetch()

    assert isinstance(incidents, list)
    assert len(incidents) == 0
