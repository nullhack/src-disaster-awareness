"""ReliefWeb humanitarian data adapter."""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from disaster_surveillance_reporter.adapters._types import (
    RawIncidentData,
    SourceAdapter,
)


class ReliefWebAdapter(SourceAdapter):
    """ReliefWeb adapter for humanitarian disaster data.

    Uses ReliefWeb API to fetch disaster and crisis reports.
    API: https://api.reliefweb.int/v2/
    """

    def __init__(
        self, appname: str = "disaster-surveillance-reporter", mock_mode: bool = True
    ):
        self._source_name = "ReliefWeb"
        self._appname = appname
        self._mock_mode = mock_mode
        self._base_url = "https://api.reliefweb.int/v2"

    @property
    def source_name(self) -> str:
        return self._source_name

    def fetch(self) -> list[RawIncidentData]:
        """Fetch humanitarian incidents from ReliefWeb."""
        if self._mock_mode:
            return self._mock_fetch()
        return self._real_fetch()

    def _mock_fetch(self) -> list[RawIncidentData]:
        """Return sample ReliefWeb-style humanitarian incidents."""
        now = datetime.now(timezone.utc)
        return [
            RawIncidentData(
                source_name="ReliefWeb",
                incident_name="Floods - Myanmar: Emergency Response Needed",
                country="Myanmar",
                disaster_type="Flood",
                report_date=(now - timedelta(hours=3)).isoformat(),
                source_url="https://reliefweb.int/report/myanmar/floods-myanmar-2026",
                raw_fields={
                    "title": "Floods - Myanmar",
                    "affected": 150000,
                    "displaced": 45000,
                    "casualties": 12,
                    "glide": "FL-2026-000123-MMR",
                },
            ),
            RawIncidentData(
                source_name="ReliefWeb",
                incident_name="Earthquake Response - Turkey and Syria",
                country="Turkey",
                disaster_type="Earthquake",
                report_date=(now - timedelta(days=1)).isoformat(),
                source_url="https://reliefweb.int/report/turkey/earthquake-turkey-syria-2026",
                raw_fields={
                    "title": "Earthquake Response - Turkey and Syria",
                    "affected": 2000000,
                    "displaced": 500000,
                    "casualties": 4500,
                    "glide": "EQ-2026-000045-TUR",
                },
            ),
            RawIncidentData(
                source_name="ReliefWeb",
                incident_name="Drought Crisis - Horn of Africa",
                country="Ethiopia",
                disaster_type="Drought",
                report_date=(now - timedelta(days=3)).isoformat(),
                source_url="https://reliefweb.int/report/ethiopia/drought-horn-africa-2026",
                raw_fields={
                    "title": "Drought Crisis - Horn of Africa",
                    "affected": 8000000,
                    "displaced": 0,
                    "casualties": 150,
                    "glide": "DR-2026-000067-ETH",
                },
            ),
            RawIncidentData(
                source_name="ReliefWeb",
                incident_name="Cyclone Response - Mozambique",
                country="Mozambique",
                disaster_type="Cyclone",
                report_date=(now - timedelta(days=5)).isoformat(),
                source_url="https://reliefweb.int/report/mozambique/cyclone-mozambique-2026",
                raw_fields={
                    "title": "Cyclone Response - Mozambique",
                    "affected": 500000,
                    "displaced": 125000,
                    "casualties": 85,
                    "glide": "CY-2026-000089-MOZ",
                },
            ),
            RawIncidentData(
                source_name="ReliefWeb",
                incident_name="Conflict Displacement - Ukraine",
                country="Ukraine",
                disaster_type="Conflict",
                report_date=(now - timedelta(days=7)).isoformat(),
                source_url="https://reliefweb.int/report/ukraine/conflict-ukraine-2026",
                raw_fields={
                    "title": "Conflict Displacement - Ukraine",
                    "affected": 6000000,
                    "displaced": 3500000,
                    "casualties": 8000,
                    "glide": "CE-2026-000100-UKR",
                },
            ),
        ]

    def _real_fetch(self) -> list[RawIncidentData]:
        """Fetch from ReliefWeb API."""
        incidents = []
        try:
            params = {
                "appname": self._appname,
                "limit": 10,
                "preset": "latest",
            }
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self._base_url}/reports",
                    params=params,
                )
                if response.status_code == 200:
                    data = response.json()
                    incidents.extend(self._parse_api_response(data))
        except Exception:
            pass
        return incidents

    def _parse_api_response(self, data: dict[str, Any]) -> list[RawIncidentData]:
        """Parse ReliefWeb API response into RawIncidentData."""
        incidents = []
        for item in data.get("data", []):
            fields = item.get("fields", {})
            primary_country = fields.get("primary_country", {})
            country = primary_country.get("name", "Unknown")
            title = fields.get("title", "Untitled")
            disaster_type = (
                fields.get("disaster_type", [{}])[0].get("name", "Disaster")
                if fields.get("disaster_type")
                else "Disaster"
            )
            date_created = fields.get("date", {}).get("created", "")
            url = fields.get("url", "")

            affected = fields.get("body", "")
            casualties = fields.get("summary", "")

            incidents.append(
                RawIncidentData(
                    source_name="ReliefWeb",
                    incident_name=title,
                    country=country,
                    disaster_type=disaster_type,
                    report_date=date_created,
                    source_url=url,
                    raw_fields={
                        "title": title,
                        "affected": affected,
                        "displaced": fields.get("idpc"),
                        "casualties": casualties,
                    },
                )
            )
        return incidents
