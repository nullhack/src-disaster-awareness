from disaster_report.models import ReportPlace, SourceReport
import logging

logger: logging.Logger

class USGSAdapter:
    source: str
    def __init__(
        self,
        slug: str = ...,
    ) -> None: ...
    def fetch(self) -> list[SourceReport]: ...
    def should_monitor(self, report: SourceReport) -> bool: ...
    def derive_keys(self, report: SourceReport) -> tuple[str, str]: ...
    def derive_repoll_keys(self, report: SourceReport) -> list[str]: ...

def _extract_canonical_name(
    raw_fields: dict[str, object],
    places: list[ReportPlace],
    report_date: str,
    incident_type: str,
) -> str: ...
