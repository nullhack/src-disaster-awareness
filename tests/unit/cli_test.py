"""Tests for CLI module."""


from disaster_surveillance_reporter.cli import DisasterSurveillanceCLI


def test_cli_status_should_show_zero_incidents(tmp_path):
    """
    Given: A CLI instance with storage path
    When: status() is called
    Then: Should show zero incidents
    """
    cli = DisasterSurveillanceCLI(storage_path=str(tmp_path), mock_ai=True)
    cli.status()


def test_cli_status_should_show_incidents(tmp_path):
    """
    Given: A CLI with storage containing incidents
    When: status() is called
    Then: Should show incident counts
    """
    from datetime import datetime, timezone

    from disaster_surveillance_reporter.storage.jsonl import JSONLBackend

    storage = JSONLBackend(tmp_path, date=datetime(2026, 4, 9, tzinfo=timezone.utc))
    storage.write(
        [
            {
                "incident_id": "001",
                "status": "Active",
                "priority": "HIGH",
                "country": "Indonesia",
            },
            {
                "incident_id": "002",
                "status": "Resolved",
                "priority": "LOW",
                "country": "Japan",
            },
        ]
    )

    cli = DisasterSurveillanceCLI(storage_path=str(tmp_path), mock_ai=True)
    cli.status()


def test_cli_fetch_should_call_adapter():
    """
    Given: A CLI instance
    When: fetch() is called
    Then: Should fetch incidents from source
    """
    cli = DisasterSurveillanceCLI(mock_ai=True)
    cli.fetch("gdacs")


def test_cli_full_cycle_should_run_pipeline():
    """
    Given: A CLI instance
    When: full_cycle() is called
    Then: Should run complete pipeline
    """
    cli = DisasterSurveillanceCLI(mock_ai=True)
    cli.full_cycle("gdacs")


def test_cli_store_should_show_storage_status(tmp_path):
    """
    Given: A CLI instance
    When: store() is called
    Then: Should show storage status
    """
    cli = DisasterSurveillanceCLI(storage_path=str(tmp_path), mock_ai=True)
    cli.store()


def test_cli_classify_with_incidents(tmp_path):
    """
    Given: A CLI with stored incidents
    When: classify() is called
    Then: Should classify incidents
    """
    from datetime import datetime, timezone

    from disaster_surveillance_reporter.storage.jsonl import JSONLBackend

    storage = JSONLBackend(tmp_path, date=datetime(2026, 4, 9, tzinfo=timezone.utc))
    storage.write([{"incident_id": "001", "country": "Indonesia"}])

    cli = DisasterSurveillanceCLI(storage_path=str(tmp_path), mock_ai=True)
    cli.classify()
