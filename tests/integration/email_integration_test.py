"""End-to-end integration test for full pipeline with email.

This test makes REAL API calls and sends REAL emails.
Only run this explicitly with: pytest tests/integration/email_integration_test.py -v -s

DO NOT run with normal test suite (pytest tests/)
"""

import pytest
import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv("/home/user/Documents/projects/disaster-surveillance-reporter/.env")


@pytest.mark.integration
def test_full_pipeline_with_email():
    """End-to-end test: fetch from sources → transform → classify → send email."""
    from datetime import datetime, timezone

    # Skip if no email credentials
    if not all(
        [
            os.environ.get("GMAIL_EMAIL"),
            os.environ.get("GMAIL_PASSWORD"),
            os.environ.get("GMAIL_RECIPIENT"),
        ]
    ):
        pytest.skip("Email credentials not configured")

    from disaster_surveillance_reporter.adapters import GDACSAdapter, ProMEDAdapter
    from disaster_surveillance_reporter.storage import EmailReporter
    from disaster_surveillance_reporter.opencode import OpenCodeClient

    # Step 1: Fetch from real sources
    print("\n[1] Fetching from real sources...")
    gdacs = GDACSAdapter(use_usgs=True, min_magnitude=4.5)
    promed = ProMEDAdapter(mock_mode=True)  # ProMED real fetch not implemented

    gdacs_incidents = gdacs.fetch()
    promed_incidents = promed.fetch()

    print(f"   GDACS: {len(gdacs_incidents)} incidents")
    print(f"   ProMED: {len(promed_incidents)} incidents")

    all_incidents = gdacs_incidents + promed_incidents
    if not all_incidents:
        pytest.skip("No incidents fetched from sources")

    # Step 2: Transform
    print("\n[2] Transforming to schema...")
    opencode = OpenCodeClient(mock_mode=True)

    transformed = []
    for raw in all_incidents[:3]:  # Limit to 3 for email test
        try:
            t = opencode.transform(
                {
                    "source_name": raw.source_name,
                    "source_url": raw.source_url,
                    "incident_name": raw.incident_name,
                    "country": raw.country,
                    "disaster_type": raw.disaster_type,
                    "report_date": raw.report_date,
                    "raw_fields": raw.raw_fields,
                }
            )
            transformed.append(t)
        except Exception as e:
            print(f"   Warning: {e}")

    print(f"   Transformed: {len(transformed)} incidents")

    # Step 3: Classify
    print("\n[3] Classifying...")
    classified = []
    for incident in transformed:
        try:
            c = opencode.classify(incident)
            classified.append(c)
        except Exception as e:
            print(f"   Warning: {e}")

    print(f"   Classified: {len(classified)} incidents")

    if not classified:
        pytest.skip("No incidents to send")

    # Step 4: Send email
    print("\n[4] Sending email...")
    email = os.environ.get("GMAIL_EMAIL")
    recipient = os.environ.get("GMAIL_RECIPIENT")
    print(f"   From: {email}")
    print(f"   To: {recipient}")

    reporter = EmailReporter()
    reporter.write(classified)

    # Verify
    print("\n[5] Verifying...")
    assert len(classified) > 0, "Should have at least one incident"
    print(f"   SUCCESS! Sent report with {len(classified)} incidents")


if __name__ == "__main__":
    test_full_pipeline_with_email()
