"""Google Sheets storage backend for disaster incidents."""

import json
import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class GoogleSheetsBackend:
    """Storage backend that writes to Google Sheets.

    Each day is stored in a new tab with ISO YYYY-MM-DD as the name.
    Does not overwrite existing data - appends to next empty row.
    """

    COLUMN_HEADERS = [
        "incident_id",
        "incident_name",
        "summary",
        "created_date",
        "updated_date",
        "status",
        "country",
        "country_group",
        "incident_type",
        "incident_level",
        "priority",
        "should_report",
        "estimated_affected",
        "estimated_deaths",
        "sources",
        "classification",
        "classification_metadata",
    ]

    def __init__(self, spreadsheet_url: str | None = None):
        """Initialize Google Sheets backend.

        Args:
            spreadsheet_url: Optional URL override. If not provided,
                           reads from GOOGLE_SHEETS_URL environment variable.
        """
        self._spreadsheet_url = spreadsheet_url or os.environ.get("GOOGLE_SHEETS_URL")

        if not self._spreadsheet_url:
            raise ValueError(
                "GOOGLE_SHEETS_URL environment variable not set. "
                "Please set it to your Google Sheets URL or provide it explicitly."
            )

        self._spreadsheet_id = self._extract_spreadsheet_id(self._spreadsheet_url)
        self._current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._service = None
        self._worksheet = None

    def _extract_spreadsheet_id(self, url: str) -> str:
        """Extract spreadsheet ID from URL."""
        # URL format: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
        # or: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit?usp=sharing
        parts = url.split("/d/")
        if len(parts) < 2:
            raise ValueError(f"Invalid Google Sheets URL: {url}")

        # parts[1] = "SPREADSHEET_ID/edit" or "SPREADSHEET_ID/edit?usp=..."
        id_part = parts[1].split("/")[0].split("?")[0]
        return id_part

    def _get_service(self):
        """Get or initialize gspread service."""
        if self._service is None:
            import gspread
            from google.oauth2.credentials import Credentials
            import json

            # Try service account first
            service_account_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
            if service_account_path and os.path.exists(service_account_path):
                self._service = gspread.service_account(service_account_path)
                return self._service

            # Try service account from default location
            default_sa = os.path.expanduser("~/.config/gspread/service_account.json")
            if os.path.exists(default_sa):
                self._service = gspread.service_account(default_sa)
                return self._service

            # Try OAuth2 - check for saved credentials
            credentials_path = os.path.expanduser(
                "~/.config/gspread/authorized_user.json"
            )

            if os.path.exists(credentials_path):
                try:
                    with open(credentials_path) as f:
                        creds = Credentials.from_authorized_user_info(
                            json.load(f),
                            scopes=[
                                "https://www.googleapis.com/auth/spreadsheets",
                                "https://www.googleapis.com/auth/drive",
                            ],
                        )
                    if creds and creds.valid:
                        self._service = gspread.Client(auth=creds)
                        return self._service
                    # Try to refresh
                    if creds.refresh_token:
                        creds.refresh()
                        self._service = gspread.Client(auth=creds)
                        return self._service
                except Exception:
                    pass

            # Check for client_secrets.json in common locations
            for secrets_path in [
                "client_secrets.json",
                os.path.expanduser("~/client_secrets.json"),
                os.path.expanduser("~/.config/gspread/client_secrets.json"),
            ]:
                if os.path.exists(secrets_path):
                    from google_auth_oauthlib.flow import InstalledAppFlow

                    flow = InstalledAppFlow.from_client_secrets_file(
                        secrets_path,
                        scopes=[
                            "https://www.googleapis.com/auth/spreadsheets",
                            "https://www.googleapis.com/auth/drive",
                        ],
                    )
                    creds = flow.run_local_server(port=0)
                    # Save for future use
                    os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
                    with open(credentials_path, "w") as f:
                        token_info = {
                            "token": creds.token,
                            "refresh_token": creds.refresh_token,
                            "token_uri": creds.token_uri,
                            "client_id": creds.client_id,
                            "client_secret": creds.client_secret,
                        }
                        json.dump(token_info, f)
                    self._service = gspread.Client(auth=creds)
                    return self._service

            raise RuntimeError(
                "Google Sheets authorization not configured.\n\n"
                "Options to fix:\n"
                "1. Enable 2-Step Verification on your Google account, then:\n"
                "   - Go to https://console.cloud.google.com/apis/credentials\n"
                "   - Create OAuth client ID (Desktop app)\n"
                "   - Download as 'client_secrets.json' in project root\n"
                "2. Or use a service account:\n"
                "   - Create service account in Google Cloud\n"
                "   - Download JSON key\n"
                "   - Set GOOGLE_SERVICE_ACCOUNT_JSON env var to path\n"
                "3. Or share spreadsheet with service account email\n"
            )

        return self._service

    def _get_worksheet(self) -> Any:
        """Get or create the worksheet for today's date."""
        if self._worksheet is None:
            service = self._get_service()
            spreadsheet = service.open_by_key(self._spreadsheet_id)

            try:
                self._worksheet = spreadsheet.worksheet(self._current_date)
            except Exception:
                # Sheet doesn't exist, create it
                self._worksheet = spreadsheet.add_worksheet(
                    title=self._current_date,
                    rows=1000,
                    cols=len(self.COLUMN_HEADERS),
                )

        return self._worksheet

    def get_or_create_worksheet(self, date: str) -> Any:
        """Get or create worksheet for given date."""
        service = self._get_service()
        spreadsheet = service.open_by_key(self._spreadsheet_id)

        try:
            return spreadsheet.worksheet(date)
        except Exception:
            return spreadsheet.add_worksheet(
                title=date,
                rows=1000,
                cols=len(self.COLUMN_HEADERS),
            )

    def write(self, incidents: list[dict[str, Any]]) -> None:
        """Write incidents to Google Sheets.

        Appends to next empty row without overwriting existing data.
        """
        if not incidents:
            return

        worksheet = self._get_worksheet()

        # Check if header exists, if not write it
        first_row = worksheet.row_values(1)
        if not first_row or first_row == [""]:
            worksheet.append_row(self.COLUMN_HEADERS, value_input_option="USER_ENTERED")

        # Find next empty row by checking column A
        all_values = worksheet.get_all_values()
        next_row = len(all_values) + 1

        # Convert incidents to rows
        for incident in incidents:
            row_data = self._incident_to_row(incident)
            worksheet.append_row(row_data, value_input_option="USER_ENTERED")
            next_row += 1

    def _incident_to_row(self, incident: dict[str, Any]) -> list[str]:
        """Convert incident dict to row values."""
        row = []

        for header in self.COLUMN_HEADERS:
            value = incident.get(header)

            # Handle list/dict fields - convert to JSON string
            if isinstance(value, (list, dict)):
                row.append(json.dumps(value))
            elif value is None:
                row.append("")
            else:
                row.append(str(value))

        return row

    def read(self) -> list[dict[str, Any]]:
        """Read all incidents from Google Sheets."""
        worksheet = self._get_worksheet()
        all_values = worksheet.get_all_values()

        if not all_values:
            return []

        # First row is header
        headers = all_values[0]
        incidents = []

        for row in all_values[1:]:
            if not row or row == [""]:
                continue

            incident = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    value = row[i]
                    # Parse JSON for list/dict fields
                    if value.startswith("[") or value.startswith("{"):
                        try:
                            incident[header] = json.loads(value)
                        except json.JSONDecodeError:
                            incident[header] = value
                    else:
                        incident[header] = value
                else:
                    incident[header] = None

            incidents.append(incident)

        return incidents

    def append(self, incidents: list[dict[str, Any]]) -> None:
        """Append incidents (alias for write)."""
        self.write(incidents)


def create_google_sheets_backend(url: str | None = None) -> GoogleSheetsBackend:
    """Factory function to create GoogleSheetsBackend."""
    return GoogleSheetsBackend(url)
