"""Tests for source adapters module."""

from unittest.mock import patch

from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter


def test_gdacs_adapter_should_return_source_name():
    """
    Given: A GDACSAdapter instance
    When: source_name property is accessed
    Then: Should return 'GDACS'
    """
    adapter = GDACSAdapter()
    assert adapter.source_name == "GDACS"


def test_gdacs_adapter_fetch_should_return_list():
    """
    Given: A GDACSAdapter instance
    When: fetch() is called
    Then: Should return a list of RawIncidentData
    """
    adapter = GDACSAdapter()
    result = adapter.fetch()
    assert isinstance(result, list)


@patch("disaster_surveillance_reporter.adapters.gdacs.httpx")
def test_gdacs_adapter_fetch_should_return_empty_on_error(mock_httpx):
    """
    Given: A GDACSAdapter with HTTP error
    When: fetch() is called
    Then: Should return empty list
    """
    mock_httpx.Client.return_value.__enter__.return_value.get.return_value.status_code = 500

    adapter = GDACSAdapter()
    result = adapter.fetch()

    assert result == []


@patch("disaster_surveillance_reporter.adapters.gdacs.httpx")
def test_gdacs_adapter_fetch_should_return_empty_on_timeout(mock_httpx):
    """
    Given: A GDACSAdapter with timeout
    When: fetch() is called
    Then: Should return empty list
    """
    import httpx

    mock_httpx.Client.return_value.__enter__.side_effect = httpx.TimeoutException(
        "timeout"
    )

    adapter = GDACSAdapter()
    result = adapter.fetch()

    assert result == []


@patch("disaster_surveillance_reporter.adapters.gdacs.httpx")
def test_gdacs_adapter_fetch_should_return_empty_on_timeout(mock_httpx):
    """
    Given: A GDACSAdapter with timeout
    When: fetch() is called
    Then: Should return empty list
    """
    import httpx

    mock_httpx.Client.return_value.__enter__.side_effect = httpx.TimeoutException(
        "timeout"
    )

    adapter = GDACSAdapter()
    result = adapter.fetch()

    assert result == []
