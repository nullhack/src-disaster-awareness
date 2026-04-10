"""Data types for source adapters."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RawIncidentData:
    """Value object for raw incident data from source adapters."""

    source_name: str
    incident_name: str
    country: str
    disaster_type: str
    report_date: str
    source_url: str
    raw_fields: dict[str, Any]


class SourceAdapter:
    """Protocol for incident source adapters."""

    def fetch(self) -> list[RawIncidentData]:
        """Fetch raw incidents from source."""
        raise NotImplementedError

    @property
    def source_name(self) -> str:
        """Return the source identifier."""
        raise NotImplementedError
