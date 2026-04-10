"""Tests for OpenCode client module."""

from unittest.mock import Mock, patch

from disaster_surveillance_reporter.opencode import OpenCodeClient


def test_given_opencode_client_when_model_then_should_return_current():
    """
    Given: An OpenCodeClient instance
    When: model property is accessed
    Then: Should return the current model
    """
    client = OpenCodeClient(mock_mode=True)
    assert client.model == "opencode/nemotron-3-super-free"


def test_given_opencode_client_when_available_models_then_should_contain_both():
    """
    Given: An OpenCodeClient instance
    When: AVAILABLE_MODELS is accessed
    Then: Should contain both nemotron-3-super-free and minimax-m2.5-free models
    """
    client = OpenCodeClient(mock_mode=True)
    assert "opencode/nemotron-3-super-free" in client.AVAILABLE_MODELS
    assert "opencode/minimax-m2.5-free" in client.AVAILABLE_MODELS
    assert len(client.AVAILABLE_MODELS) == 2


def test_given_opencode_client_when_switch_model_then_should_use_next():
    """
    Given: An OpenCodeClient with current model
    When: _switch_to_fallback_model() is called
    Then: Should switch to next model in list
    """
    client = OpenCodeClient(mock_mode=True)
    initial_model = client.model
    result = client._switch_to_fallback_model()
    assert result is True
    assert client.model != initial_model
    assert client.model == "opencode/minimax-m2.5-free"


def test_given_opencode_client_when_all_models_used_then_should_cycle():
    """
    Given: An OpenCodeClient that has used all models
    When: _switch_to_fallback_model() is called again
    Then: Should cycle back to first model (nemotron)
    """
    client = OpenCodeClient(mock_mode=True)
    client._switch_to_fallback_model()  # Go to minimax
    client._switch_to_fallback_model()  # Should cycle back to first
    assert client.model == "opencode/nemotron-3-super-free"


def test_transform_should_return_schema_fields():
    """
    Given: An OpenCodeClient in mock mode
    When: transform() is called with raw incident
    Then: Should return dict with required schema fields
    """
    client = OpenCodeClient(mock_mode=True)
    raw = {
        "source_name": "GDACS",
        "incident_name": "Test Event",
        "country": "Indonesia",
        "disaster_type": "Earthquake",
        "report_date": "2026-03-12T00:00:00Z",
    }
    result = client.transform(raw)

    assert "incident_id" in result
    assert "incident_name" in result
    assert "created_date" in result
    assert "status" in result
    assert result["status"] == "Active"
    assert "summary" in result
    assert "estimated_affected" in result
    assert "estimated_deaths" in result


def test_transform_should_include_new_fields():
    """
    Given: An OpenCodeClient in mock mode with raw_fields
    When: transform() is called
    Then: Should include summary, estimated_affected, estimated_deaths
    """
    client = OpenCodeClient(mock_mode=True)
    raw = {
        "incident_name": "M5.0 Earthquake Test",
        "country": "Indonesia",
        "disaster_type": "Earthquake",
        "report_date": "2026-03-12T00:00:00Z",
        "raw_fields": {
            "title": "M 5.0 - Test earthquake",
            "felt": 100,
            "deaths": 5,
        },
    }
    result = client.transform(raw)

    assert result["summary"] == "M 5.0 - Test earthquake"
    assert result["estimated_affected"] == 100
    assert result["estimated_deaths"] == 5


def test_transform_should_include_sources_list():
    """
    Given: An OpenCodeClient in mock mode
    When: transform() is called
    Then: Should include sources list in output
    """
    client = OpenCodeClient(mock_mode=True)
    raw = {
        "source_name": "GDACS",
        "incident_name": "Test Event",
        "country": "Indonesia",
        "disaster_type": "Earthquake",
        "report_date": "2026-03-12T00:00:00Z",
    }
    result = client.transform(raw)

    assert "sources" in result
    assert isinstance(result["sources"], list)


def test_transform_should_have_non_empty_sources():
    """
    Given: An OpenCodeClient in mock mode
    When: transform() is called
    Then: Sources list should never be empty
    """
    client = OpenCodeClient(mock_mode=True)
    raw = {
        "source_name": "GDACS",
        "incident_name": "Test Event",
        "country": "Indonesia",
    }
    result = client.transform(raw)

    assert len(result["sources"]) > 0


def test_transform_should_include_source_details():
    """
    Given: An OpenCodeClient in mock mode
    When: transform() is called with source_name and source_url
    Then: Sources should contain name, type, url, accessed_date
    """
    client = OpenCodeClient(mock_mode=True)
    raw = {
        "source_name": "GDACS",
        "source_url": "https://www.gdacs.org/event/12345",
        "incident_name": "Test Event",
        "country": "Indonesia",
        "report_date": "2026-03-12T00:00:00Z",
    }
    result = client.transform(raw)

    source = result["sources"][0]
    assert "name" in source
    assert source["name"] == "GDACS"
    assert "type" in source
    assert "url" in source
    assert source["url"] == "https://www.gdacs.org/event/12345"
    assert "accessed_date" in source


def test_transform_should_not_have_null_summary():
    """
    Given: An OpenCodeClient in mock mode with no source data
    When: transform() is called
    Then: Summary should never be null - code should generate fallback
    """
    client = OpenCodeClient(mock_mode=True)
    raw = {
        "incident_name": "M5.0 Earthquake Test",
        "country": "Indonesia",
        "disaster_type": "Earthquake",
    }
    result = client.transform(raw)

    assert result["summary"] is not None
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0


def test_transform_should_generate_fallback_summary_from_fields():
    """
    Given: An OpenCodeClient with raw incident containing incident_name, disaster_type, country
    When: transform() is called (no source data available)
    Then: Code should generate fallback summary from those fields
    """
    client = OpenCodeClient(mock_mode=True)
    raw = {
        "incident_name": "Tropical Cyclone Warning",
        "country": "Philippines",
        "disaster_type": "Cyclone",
    }
    result = client.transform(raw)

    summary = result["summary"]
    assert summary is not None
    assert "Cyclone" in summary or "Philippines" in summary


def test_transform_should_have_non_null_summary_when_raw_fields_empty():
    """
    Given: An OpenCodeClient with empty raw_fields
    When: transform() is called
    Then: Summary should be generated from basic incident info
    """
    client = OpenCodeClient(mock_mode=True)
    raw = {
        "incident_name": "Flood Warning",
        "country": "Myanmar",
        "disaster_type": "Flood",
    }
    result = client.transform(raw)

    assert result["summary"] is not None
    assert result["summary"] != ""


def test_transform_should_have_optional_fields_as_null_when_missing():
    """
    Given: An OpenCodeClient in mock mode without raw_fields
    When: transform() is called
    Then: estimated_affected and estimated_deaths should be None (optional fields)
    """
    client = OpenCodeClient(mock_mode=True)
    raw = {
        "incident_name": "Test",
        "country": "Indonesia",
        "disaster_type": "Earthquake",
    }
    result = client.transform(raw)

    assert result["estimated_affected"] is None
    assert result["estimated_deaths"] is None


def test_transform_should_include_country():
    """
    Given: An OpenCodeClient in mock mode
    When: transform() is called with country 'Indonesia'
    Then: Should include country in result
    """
    client = OpenCodeClient(mock_mode=True)
    raw = {"country": "Indonesia", "incident_name": "Test"}
    result = client.transform(raw)

    assert result["country"] == "Indonesia"


def test_classify_should_add_classification_fields():
    """
    Given: An OpenCodeClient in mock mode with incident
    When: classify() is called
    Then: Should add classification dict with required fields
    """
    client = OpenCodeClient(mock_mode=True)
    incident = {
        "country": "Indonesia",
        "country_group": "A",
        "incident_type": "Earthquake",
        "incident_level": 2,
        "priority": "MEDIUM",
        "should_report": True,
    }
    result = client.classify(incident)

    assert "classification" in result
    assert result["classification"]["country_group"] == "A"
    assert result["classification"]["incident_level"] == 2


def test_classify_should_add_classification_metadata():
    """
    Given: An OpenCodeClient in mock mode with incident
    When: classify() is called
    Then: Should add classification_metadata
    """
    client = OpenCodeClient(mock_mode=True)
    incident = {"country": "Indonesia", "incident_level": 2}
    result = client.classify(incident)

    assert "classification_metadata" in result
    assert "classified_by" in result["classification_metadata"]
    assert "rationale" in result["classification_metadata"]


@patch("subprocess.run")
def test_real_transform_should_call_opencode_cli(mock_run):
    """
    Given: An OpenCodeClient in real mode
    When: transform() is called
    Then: Should call subprocess.run with opencode command
    """
    mock_run.return_value = Mock(
        returncode=0,
        stdout='{"incident_id": "test", "status": "Active"}',
    )

    client = OpenCodeClient(mock_mode=False)
    raw = {"incident_name": "Test", "country": "Indonesia"}
    client.transform(raw)

    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "opencode" in call_args
    assert "--format" in call_args
    assert "--dangerously-skip-permissions" in call_args


@patch("subprocess.run")
def test_real_classify_should_call_opencode_cli(mock_run):
    """
    Given: An OpenCodeClient in real mode
    When: classify() is called
    Then: Should call subprocess.run with opencode command
    """
    mock_run.return_value = Mock(
        returncode=0,
        stdout='{"incident_id": "test", "priority": "HIGH"}',
    )

    client = OpenCodeClient(mock_mode=False)
    incident = {"incident_id": "test", "country": "Indonesia"}
    client.classify(incident)

    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "opencode" in call_args
    assert "--format" in call_args
    assert "--dangerously-skip-permissions" in call_args


@patch("subprocess.run")
def test_real_transform_should_fallback_on_rate_limit(mock_run):
    """
    Given: An OpenCodeClient in real mode
    When: First model fails with rate limit (returncode 429)
    Then: Should retry with next model automatically
    """
    # First call fails with rate limit, second call succeeds
    mock_run.side_effect = [
        Mock(returncode=429, stdout=""),
        Mock(returncode=0, stdout='{"incident_id": "test", "status": "Active"}'),
    ]

    client = OpenCodeClient(mock_mode=False)
    raw = {"incident_name": "Test", "country": "Indonesia"}
    result = client.transform(raw)

    # Should have tried twice (first model failed, second succeeded)
    assert mock_run.call_count == 2
    assert result["incident_id"] == "test"


@patch("subprocess.run")
def test_real_transform_should_exhaust_all_models_on_failure(mock_run):
    """
    Given: An OpenCodeClient in real mode
    When: All models fail
    Then: Should try all models in AVAILABLE_MODELS before giving up
    """
    # All calls fail
    mock_run.return_value = Mock(returncode=500, stdout="")

    client = OpenCodeClient(mock_mode=False)
    raw = {"incident_name": "Test", "country": "Indonesia"}

    # Should try all models (2 in this case)
    try:
        client.transform(raw)
    except Exception:
        pass

    # Should have tried len(AVAILABLE_MODELS) times
    assert mock_run.call_count == len(client.AVAILABLE_MODELS)
