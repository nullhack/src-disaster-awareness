"""WHO health emergencies adapter."""

from datetime import datetime, timedelta, timezone

from disaster_surveillance_reporter.adapters._types import (
    RawIncidentData,
    SourceAdapter,
)


class WHOAdapter(SourceAdapter):
    """World Health Organization (WHO) adapter for health emergencies.

    Monitors WHO disease outbreak alerts and health emergencies.
    """

    def __init__(self, mock_mode: bool = True):
        self._source_name = "WHO"
        self._mock_mode = mock_mode

    @property
    def source_name(self) -> str:
        return self._source_name

    def fetch(self) -> list[RawIncidentData]:
        """Fetch health emergencies from WHO."""
        if self._mock_mode:
            return self._mock_fetch()
        return self._real_fetch()

    def _mock_fetch(self) -> list[RawIncidentData]:
        """Return sample WHO-style health emergency data."""
        now = datetime.now(timezone.utc)
        return [
            RawIncidentData(
                source_name="WHO",
                incident_name="Novel Coronavirus Alert - Global",
                country="Global",
                disaster_type="Disease",
                report_date=(now - timedelta(hours=4)).isoformat(),
                source_url="https://who.int/emergencies/disease-outbreaks/2026/novel-coronavirus",
                raw_fields={
                    "disease": "COVID-19 Variant X",
                    "cases": 5000,
                    "deaths": 25,
                    "hospitalizations": 150,
                    "countries_affected": 12,
                },
            ),
            RawIncidentData(
                source_name="WHO",
                incident_name="Ebola Outbreak - DRC",
                country="Democratic Republic of Congo",
                disaster_type="Ebola",
                report_date=(now - timedelta(hours=8)).isoformat(),
                source_url="https://who.int/emergencies/disease-outbreaks/2026/ebola-drc",
                raw_fields={
                    "disease": "Ebola",
                    "cases": 89,
                    "deaths": 45,
                    "hospitalizations": 32,
                    "countries_affected": 1,
                },
            ),
            RawIncidentData(
                source_name="WHO",
                incident_name="Avian Influenza - Multiple Countries",
                country="Multiple",
                disaster_type="Influenza",
                report_date=(now - timedelta(days=1)).isoformat(),
                source_url="https://who.int/emergencies/disease-outbreaks/2026/avian-influenza",
                raw_fields={
                    "disease": "H5N1 Avian Influenza",
                    "cases": 156,
                    "deaths": 8,
                    "hospitalizations": 45,
                    "countries_affected": 5,
                },
            ),
            RawIncidentData(
                source_name="WHO",
                incident_name="Monkeypox - Africa Region",
                country="Nigeria",
                disaster_type="Monkeypox",
                report_date=(now - timedelta(days=2)).isoformat(),
                source_url="https://who.int/emergencies/disease-outbreaks/2026/monkeypox-africa",
                raw_fields={
                    "disease": "Monkeypox Clade II",
                    "cases": 1200,
                    "deaths": 18,
                    "hospitalizations": 89,
                    "countries_affected": 3,
                },
            ),
            RawIncidentData(
                source_name="WHO",
                incident_name="Marburg Virus - Tanzania",
                country="Tanzania",
                disaster_type="Marburg",
                report_date=(now - timedelta(days=3)).isoformat(),
                source_url="https://who.int/emergencies/disease-outbreaks/2026/marburg-tanzania",
                raw_fields={
                    "disease": "Marburg Virus",
                    "cases": 34,
                    "deaths": 11,
                    "hospitalizations": 28,
                    "countries_affected": 1,
                },
            ),
        ]

    def _real_fetch(self) -> list[RawIncidentData]:
        """Fetch from WHO API (not implemented)."""
        return []
