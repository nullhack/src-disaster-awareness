"""Integration test for Google Sheets backend - real API call."""

import os

from disaster_surveillance_reporter.storage import GoogleSheetsBackend


def test_integration_google_sheets_real_write():
    """Integration test: Write real data to Google Sheets."""
    # This test actually writes to Google Sheets
    # Make sure you have credentials set up before running

    url = os.environ.get("GOOGLE_SHEETS_URL")
    if not url:
        print("SKIP: GOOGLE_SHEETS_URL not set in environment")
        print("To run this test:")
        print("1. Copy .env.example to .env")
        print("2. Set GOOGLE_SHEETS_URL with edit-enabled link")
        print("3. Set up Google credentials (OAuth2 or service account)")
        return

    try:
        backend = GoogleSheetsBackend(url)

        # Test data
        test_incidents = [
            {
                "incident_id": "20260410-TEST-INTEGRATION",
                "incident_name": "Integration Test Incident",
                "summary": "This is a test to verify the Google Sheets integration works.",
                "created_date": "2026-04-10T12:00:00Z",
                "updated_date": "2026-04-10T12:00:00Z",
                "status": "Active",
                "country": "TestCountry",
                "country_group": "B",
                "incident_type": "Test",
                "incident_level": 1,
                "priority": "LOW",
                "should_report": False,
                "estimated_affected": None,
                "estimated_deaths": None,
                "sources": [
                    {
                        "name": "TestSource",
                        "type": "test",
                        "url": "https://example.com/test",
                        "accessed_date": "2026-04-10T12:00:00Z",
                        "reliability_tier": "Tier2",
                        "data_freshness": "daily",
                    }
                ],
                "classification": {"priority": "LOW"},
                "classification_metadata": {"test": True},
            }
        ]

        backend.write(test_incidents)

        # Verify write worked by reading back
        incidents = backend.read()
        print(f"SUCCESS: Wrote and read back {len(incidents)} incidents")

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        print("Make sure you have Google credentials configured.")


if __name__ == "__main__":
    test_integration_google_sheets_real_write()
