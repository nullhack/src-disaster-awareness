"""Tests for EmailReporter storage."""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from disaster_surveillance_reporter.storage import EmailReporter


def test_given_email_reporter_when_init_with_env_vars_should_load():
    """
    Given: Environment variables GMAIL_EMAIL, GMAIL_PASSWORD, GMAIL_RECIPIENT are set
    When: EmailReporter is initialized
    Then: Should load the configuration from environment
    """
    with patch.dict(
        os.environ,
        {
            "GMAIL_EMAIL": "sender@gmail.com",
            "GMAIL_PASSWORD": "testpassword123",
            "GMAIL_RECIPIENT": "recipient@example.com",
        },
    ):
        reporter = EmailReporter()
        assert reporter._sender_email == "sender@gmail.com"
        assert reporter._recipient_email == "recipient@example.com"


def test_given_email_reporter_when_init_should_raise_without_env():
    """
    Given: Required environment variables are not set
    When: EmailReporter is initialized
    Then: Should raise ValueError
    """
    env_backup = {
        k: os.environ.get(k)
        for k in ["GMAIL_EMAIL", "GMAIL_PASSWORD", "GMAIL_RECIPIENT"]
    }
    for k in ["GMAIL_EMAIL", "GMAIL_PASSWORD", "GMAIL_RECIPIENT"]:
        if k in os.environ:
            del os.environ[k]

    try:
        with pytest.raises(ValueError, match="GMAIL_EMAIL"):
            EmailReporter()
    finally:
        if env_backup["GMAIL_EMAIL"]:
            os.environ["GMAIL_EMAIL"] = env_backup["GMAIL_EMAIL"]
        if env_backup["GMAIL_PASSWORD"]:
            os.environ["GMAIL_PASSWORD"] = env_backup["GMAIL_PASSWORD"]
        if env_backup["GMAIL_RECIPIENT"]:
            os.environ["GMAIL_RECIPIENT"] = env_backup["GMAIL_RECIPIENT"]


def test_given_email_reporter_when_write_should_send_email():
    """
    Given: An EmailReporter with mock SMTP
    When: write is called with incidents
    Then: Should send email with HTML table
    """
    with patch.dict(
        os.environ,
        {
            "GMAIL_EMAIL": "sender@gmail.com",
            "GMAIL_PASSWORD": "testpassword",
            "GMAIL_RECIPIENT": "recipient@example.com",
        },
    ):
        with patch(
            "disaster_surveillance_reporter.storage.email_reporter.smtplib.SMTP"
        ) as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            reporter = EmailReporter()
            incidents = [
                {
                    "incident_id": "20260410-001",
                    "incident_name": "Test Earthquake",
                    "country": "Indonesia",
                    "incident_type": "Earthquake",
                    "priority": "HIGH",
                    "status": "Active",
                }
            ]
            reporter.write(incidents)

            # Verify SMTP was used
            mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with(
                "sender@gmail.com", "testpassword"
            )
            mock_server.send_message.assert_called_once()


def test_given_email_reporter_when_write_should_include_table():
    """
    Given: An EmailReporter
    When: write is called with incidents
    Then: Email body should contain HTML table with incident data
    """
    with patch.dict(
        os.environ,
        {
            "GMAIL_EMAIL": "sender@gmail.com",
            "GMAIL_PASSWORD": "testpassword",
            "GMAIL_RECIPIENT": "recipient@example.com",
        },
    ):
        with patch(
            "disaster_surveillance_reporter.storage.email_reporter.smtplib.SMTP"
        ) as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            reporter = EmailReporter()
            incidents = [
                {
                    "incident_id": "TEST-001",
                    "incident_name": "Flood Warning",
                    "country": "Myanmar",
                    "incident_type": "Flood",
                    "priority": "MEDIUM",
                    "status": "Active",
                }
            ]
            reporter.write(incidents)

            # Get the email that was sent
            mock_server.send_message.assert_called_once()
            call_args = mock_server.send_message.call_args
            msg = call_args[0][0]

            # Check table contains incident data
            body = msg.as_string()
            assert "TEST-001" in body
            assert "Flood Warning" in body
            assert "Myanmar" in body
            assert "<table>" in body


def test_given_email_reporter_when_write_should_have_subject_with_date():
    """
    Given: An EmailReporter
    When: write is called
    Then: Email subject should include today's date
    """
    with patch.dict(
        os.environ,
        {
            "GMAIL_EMAIL": "sender@gmail.com",
            "GMAIL_PASSWORD": "testpassword",
            "GMAIL_RECIPIENT": "recipient@example.com",
        },
    ):
        with patch(
            "disaster_surveillance_reporter.storage.email_reporter.smtplib.SMTP"
        ) as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            reporter = EmailReporter()
            reporter.write(
                [
                    {
                        "incident_id": "TEST",
                        "incident_name": "Test",
                        "country": "Test",
                        "incident_type": "Test",
                        "priority": "LOW",
                        "status": "Active",
                    }
                ]
            )

            mock_server.send_message.assert_called_once()
            call_args = mock_server.send_message.call_args
            msg = call_args[0][0]

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            assert today in msg["Subject"]
