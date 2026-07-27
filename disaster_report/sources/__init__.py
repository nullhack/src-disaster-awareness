
from __future__ import annotations

from typing import Any


def adapter_registry() -> dict[str, Any]:

    from disaster_report.sources.ercc import ERCCAdapter
    from disaster_report.sources.gdacs import GDACSAdapter
    from disaster_report.sources.usgs import USGSAdapter
    from disaster_report.sources.who import WHODiseaseOutbreakAdapter

    return {
        "USGS": USGSAdapter(),
        "GDACS": GDACSAdapter(),
        "WHO": WHODiseaseOutbreakAdapter(),
        "ERCC": ERCCAdapter(),
    }
