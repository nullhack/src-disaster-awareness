"""ProMED disease outbreak adapter."""

from datetime import datetime, timedelta, timezone

from disaster_surveillance_reporter.adapters._types import (
    RawIncidentData,
    SourceAdapter,
)


class ProMEDAdapter(SourceAdapter):
    """ProMED-mail (Program for Monitoring Emerging Diseases) adapter.

    Fetches disease outbreak alerts from ProMED-mail.
    Note: ProMED doesn't have a public API. This adapter provides mock data
    for demonstration. Real implementation would require API access or
    RSS feed parsing from their website.
    """

    def __init__(self, mock_mode: bool = True):
        self._source_name = "ProMED"
        self._mock_mode = mock_mode

    @property
    def source_name(self) -> str:
        return self._source_name

    def fetch(self) -> list[RawIncidentData]:
        """Fetch disease outbreak incidents from ProMED."""
        if self._mock_mode:
            return self._mock_fetch()
        return self._real_fetch()

    def _mock_fetch(self) -> list[RawIncidentData]:
        """Return sample ProMED-style disease alerts."""
        now = datetime.now(timezone.utc)
        return [
            RawIncidentData(
                source_name="ProMED",
                incident_name="MEASLES - PERU (TUMBES): OUTBREAK, RAPIDLY INCREASING CASES",
                country="Peru",
                disaster_type="Measles",
                report_date=(now - timedelta(hours=2)).isoformat(),
                source_url="https://promedmail.org/post/12345678",
                raw_fields={
                    "title": "MEASLES - PERU (TUMBES): OUTBREAK",
                    "disease": "Measles",
                    "cases": 150,
                    "deaths": 2,
                },
            ),
            RawIncidentData(
                source_name="ProMED",
                incident_name="LASSA FEVER - NIGERIA: PHYSICIANS AFFECTED",
                country="Nigeria",
                disaster_type="Lassa Fever",
                report_date=(now - timedelta(hours=6)).isoformat(),
                source_url="https://promedmail.org/post/12345679",
                raw_fields={
                    "title": "LASSA FEVER - NIGERIA",
                    "disease": "Lassa Fever",
                    "cases": 45,
                    "deaths": 12,
                },
            ),
            RawIncidentData(
                source_name="ProMED",
                incident_name="AVIAN INFLUENZA - INDIA (KERALA): H5N1, BIRD CULLING",
                country="India",
                disaster_type="Avian Influenza",
                report_date=(now - timedelta(hours=12)).isoformat(),
                source_url="https://promedmail.org/post/12345680",
                raw_fields={
                    "title": "AVIAN INFLUENZA - INDIA",
                    "disease": "H5N1",
                    "affected": 50000,
                    "culled": 35000,
                },
            ),
            RawIncidentData(
                source_name="ProMED",
                incident_name="DENGUE - BRAZIL (RIO DE JANEIRO): INCREASING CASES",
                country="Brazil",
                disaster_type="Dengue",
                report_date=(now - timedelta(days=1)).isoformat(),
                source_url="https://promedmail.org/post/12345681",
                raw_fields={
                    "title": "DENGUE - BRAZIL",
                    "disease": "Dengue",
                    "cases": 25000,
                    "deaths": 8,
                },
            ),
            RawIncidentData(
                source_name="ProMED",
                incident_name="CHOLERA - MALAWI: ONGOING OUTBREAK",
                country="Malawi",
                disaster_type="Cholera",
                report_date=(now - timedelta(days=2)).isoformat(),
                source_url="https://promedmail.org/post/12345682",
                raw_fields={
                    "title": "CHOLERA - MALAWI",
                    "disease": "Cholera",
                    "cases": 1200,
                    "deaths": 45,
                },
            ),
        ]

    def _real_fetch(self) -> list[RawIncidentData]:
        """Real fetch - requires API or RSS scraping implementation."""
        return []
