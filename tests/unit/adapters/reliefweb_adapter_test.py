"""Tests for ReliefWebAdapter."""

from datetime import datetime, timedelta, timezone

from disaster_surveillance_reporter.adapters import RawIncidentData, ReliefWebAdapter


def test_given_reliefweb_adapter_when_source_name_then_should_return_reliefweb():
    """
    Given: A ReliefWebAdapter instance
    When: source_name property is accessed
    Then: Should return "ReliefWeb"
    """
    adapter = ReliefWebAdapter()
    assert adapter.source_name == "ReliefWeb"


def test_given_reliefweb_adapter_when_fetch_with_mock_then_should_return_incidents():
    """
    Given: A ReliefWebAdapter in mock mode
    When: fetch() is called
    Then: Should return list of RawIncidentData with humanitarian incidents
    """
    adapter = ReliefWebAdapter(mock_mode=True)
    incidents = adapter.fetch()

    assert isinstance(incidents, list)
    assert len(incidents) == 5

    # Check first incident
    incident = incidents[0]
    assert isinstance(incident, RawIncidentData)
    assert incident.source_name == "ReliefWeb"
    assert incident.incident_name == "Floods - Myanmar: Emergency Response Needed"
    assert incident.country == "Myanmar"
    assert incident.disaster_type == "Flood"
    assert (
        incident.source_url
        == "https://reliefweb.int/report/myanmar/floods-myanmar-2026"
    )
    assert incident.raw_fields["affected"] == 150000
    assert incident.raw_fields["displaced"] == 45000
    assert incident.raw_fields["casualties"] == 12


def test_given_reliefweb_adapter_when_fetch_with_mock_then_should_have_correct_dates():
    """
    Given: A ReliefWebAdapter in mock mode
    When: fetch() is called
    Then: Should return incidents with recent dates (within last 7 days)
    """
    adapter = ReliefWebAdapter(mock_mode=True)
    incidents = adapter.fetch()

    now = datetime.now(timezone.utc)
    for incident in incidents:
        report_date = datetime.fromisoformat(
            incident.report_date.replace("Z", "+00:00")
        )
        # Should be within last 7 days (allowing small time difference for test execution)
        assert (now - report_date) <= timedelta(days=7, seconds=1)


def test_given_reliefweb_adapter_when_fetch_real_then_should_return_empty():
    """
    Given: A ReliefWebAdapter with mock_mode=False
    When: fetch() is called (real fetch not implemented)
    Then: Should return empty list (stub implementation)
    """
    adapter = ReliefWebAdapter(mock_mode=False)
    incidents = adapter.fetch()

    assert isinstance(incidents, list)
    assert len(incidents) == 0
