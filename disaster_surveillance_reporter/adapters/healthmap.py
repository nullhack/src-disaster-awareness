"""HealthMap disease surveillance adapter."""

from datetime import datetime, timedelta, timezone

from disaster_surveillance_reporter.adapters._types import (
    RawIncidentData,
    SourceAdapter,
)


class HealthMapAdapter(SourceAdapter):
    """HealthMap adapter for disease surveillance data.

    HealthMap monitors disease outbreaks globally using news and official sources.
    """

    def __init__(self, mock_mode: bool = True):
        self._source_name = "HealthMap"
        self._mock_mode = mock_mode

    @property
    def source_name(self) -> str:
        return self._source_name

    def fetch(self) -> list[RawIncidentData]:
        """Fetch disease surveillance incidents from HealthMap."""
        if self._mock_mode:
            return self._mock_fetch()
        return self._real_fetch()

    def _mock_fetch(self) -> list[RawIncidentData]:
        """Return sample HealthMap-style disease surveillance data."""
        now = datetime.now(timezone.utc)
        return [
            RawIncidentData(
                source_name="HealthMap",
                incident_name="H1N1 Outbreak - United States",
                country="United States",
                disaster_type="H1N1",
                report_date=(now - timedelta(hours=6)).isoformat(),
                source_url="https://healthmap.org/2026/04/h1n1-us",
                raw_fields={
                    "disease": "H1N1",
                    "cases": 1250,
                    "deaths": 15,
                    "locations": ["California", "Texas", "New York"],
                },
            ),
            RawIncidentData(
                source_name="HealthMap",
                incident_name="Measles Spread - Europe",
                country="Germany",
                disaster_type="Measles",
                report_date=(now - timedelta(hours=12)).isoformat(),
                source_url="https://healthmap.org/2026/04/measles-europe",
                raw_fields={
                    "disease": "Measles",
                    "cases": 340,
                    "deaths": 2,
                    "locations": ["Berlin", "Munich"],
                },
            ),
            RawIncidentData(
                source_name="HealthMap",
                incident_name="Dengue Fever - Southeast Asia",
                country="Thailand",
                disaster_type="Dengue",
                report_date=(now - timedelta(days=1)).isoformat(),
                source_url="https://healthmap.org/2026/04/dengue-thailand",
                raw_fields={
                    "disease": "Dengue",
                    "cases": 2800,
                    "deaths": 8,
                    "locations": ["Bangkok", "Chiang Mai"],
                },
            ),
            RawIncidentData(
                source_name="HealthMap",
                incident_name="Cholera Outbreak - Africa",
                country="Kenya",
                disaster_type="Cholera",
                report_date=(now - timedelta(days=2)).isoformat(),
                source_url="https://healthmap.org/2026/04/cholera-kenya",
                raw_fields={
                    "disease": "Cholera",
                    "cases": 520,
                    "deaths": 12,
                    "locations": ["Nairobi", "Mombasa"],
                },
            ),
            RawIncidentData(
                source_name="HealthMap",
                incident_name="MERS Cases - Middle East",
                country="Saudi Arabia",
                disaster_type="MERS",
                report_date=(now - timedelta(days=3)).isoformat(),
                source_url="https://healthmap.org/2026/04/mers-saudi",
                raw_fields={
                    "disease": "MERS",
                    "cases": 45,
                    "deaths": 8,
                    "locations": ["Riyadh", "Jeddah"],
                },
            ),
        ]

    def _real_fetch(self) -> list[RawIncidentData]:
        """Fetch from HealthMap API (not implemented)."""
        return []
