from __future__ import annotations

import html
import re

import httpx
import pycountry

from disaster_report.sources._dates import parse_date
from disaster_report.sources.base import RawIncident, json_list

_DEFAULT_URL = "https://www.healthmap.org/getAlerts.php"
_TAG = re.compile(r"<[^>]+>")
_ALERTID = re.compile(r"ai\.php\?(\d+)")
_WORD = re.compile(r"[A-Za-z][A-Za-z '\-]{1,39}")


def _strip(s: str) -> str:
    return html.unescape(_TAG.sub("", s or "")).strip()


_SUBDIVISION_NAMES: dict[str, str] | None = None


def _subdivision_index() -> dict[str, str]:
    global _SUBDIVISION_NAMES
    if _SUBDIVISION_NAMES is None:
        index: dict[str, str] = {}
        for subdivision in pycountry.subdivisions:
            index[subdivision.name.lower()] = (
                f"{subdivision.country_code}-{subdivision.code.split('-')[1]}"
            )
        _SUBDIVISION_NAMES = index
    return _SUBDIVISION_NAMES


def _scan_subdivision(text: str) -> str | None:
    if not text:
        return None
    index = _subdivision_index()
    seen: set[str] = set()
    for token in _WORD.findall(text):
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        code = index.get(key)
        if code:
            return code
    return None


class HealthMapAdapter:
    source_name = "HealthMap"

    def __init__(
        self,
        url: str = _DEFAULT_URL,
        min_date: str = "",
        max_date: str = "",
        timeout: float = 60.0,
    ) -> None:
        self.url = url
        self.min_date = min_date
        self.max_date = max_date
        self.timeout = timeout

    def fetch(self) -> list[RawIncident]:
        params: dict[str, str] = {}
        if self.min_date:
            params["min_date"] = self.min_date
        if self.max_date:
            params["max_date"] = self.max_date
        response = httpx.get(
            self.url,
            params=params or None,
            timeout=self.timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        out: list[RawIncident] = []
        for row in json_list(response, "listview"):
            if not isinstance(row, list) or len(row) < 5:
                continue
            summary_html = row[2] or ""
            location_html = row[4] or ""
            date_s = row[1] or ""
            parsed_date = parse_date(date_s) if date_s else None
            report_date = parsed_date.isoformat() if parsed_date else (date_s or "")
            match = _ALERTID.search(summary_html)
            alert_id = match.group(1) if match else ""
            source_url = ("https://www.healthmap.org/ai.php?" + alert_id) if alert_id else ""
            country = _strip(location_html)
            subdivision_code = _scan_subdivision(_strip(summary_html))
            out.append(
                RawIncident(
                    source_name=self.source_name,
                    incident_name=_strip(summary_html),
                    country=country,
                    disaster_type="Disease",
                    report_date=report_date,
                    source_url=source_url,
                    raw_fields={
                        "summary": row[2],
                        "date": row[1],
                        "disease": row[3],
                        "location": row[4],
                        "event_id": match.group(1) if match else "",
                        "subdivision": subdivision_code or "",
                    },
                )
            )
        return out
