from __future__ import annotations

import re
from datetime import datetime

import httpx

from disaster_report.sources.base import RawIncident

_DEFAULT_URL = (
    "https://www.who.int/api/news/diseaseoutbreaknews"
    "?$orderby=PublicationDateAndTime%20desc&$top=25"
)
_GUID_RE = re.compile(r"/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE)


def _to_iso(s: str) -> str:
    if not s:
        return ""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return s


class WHODiseaseOutbreakAdapter:
    source_name = "WHO Disease Outbreak News"

    def __init__(self, url: str = _DEFAULT_URL, timeout: float = 30.0) -> None:
        self.url = url
        self.timeout = timeout

    def fetch(self) -> list[RawIncident]:
        resp = httpx.get(self.url, timeout=self.timeout, follow_redirects=True)
        resp.raise_for_status()
        items = resp.json().get("value", [])
        out: list[RawIncident] = []
        for it in items:
            title = (
                (it.get("OverrideTitle") or it.get("Title") or "")
                if it.get("UseOverrideTitle")
                else (it.get("Title") or "")
            )
            parts = title.split(" - ")
            country = parts[-1].strip() if len(parts) > 1 else ""
            disease_name = parts[0].strip() if len(parts) > 1 else ""
            path = it.get("ItemDefaultUrl", "") or ""
            source_url = ("https://www.who.int" + path) if path else ""
            guid_match = _GUID_RE.search(path)
            event_id = guid_match.group(1) if guid_match else path
            raw_fields = dict(it)
            raw_fields["event_id"] = event_id
            raw_fields["disease"] = disease_name
            out.append(
                RawIncident(
                    source_name=self.source_name,
                    incident_name=title,
                    country=country,
                    disaster_type="Disease",
                    report_date=_to_iso(it.get("PublicationDateAndTime", "") or ""),
                    source_url=source_url,
                    raw_fields=raw_fields,
                )
            )
        return out
