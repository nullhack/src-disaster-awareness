from disaster_report.models import ReportPlace, SourceReport
import logging

logger: logging.Logger

class GDACSAdapter:
    def __init__(
        self,
        path: str = ...,
    ) -> None: ...
    def fetch(self) -> list[SourceReport]: ...
    def should_monitor(self, report: SourceReport) -> bool: ...
    def derive_keys(self, report: SourceReport) -> tuple[str, str]: ...

def _item_to_report(item: object) -> SourceReport: ...
def _extract_canonical_name(
    raw_fields: dict[str, object],
    places: list[ReportPlace],
    report_date: str,
    incident_type: str,
) -> str: ...
def _extract_places(
    iso3: str, country_text: str, lat: object, lon: object
) -> list[ReportPlace]: ...
