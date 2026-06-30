from __future__ import annotations

import html
import re
from datetime import UTC, datetime

import httpx
import pycountry

from disaster_report.sources.base import RawIncident

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
        idx: dict[str, str] = {}
        for sub in pycountry.subdivisions:
            idx[sub.name.lower()] = f"{sub.country_code}-{sub.code.split('-')[1]}"
        _SUBDIVISION_NAMES = idx
    return _SUBDIVISION_NAMES


def _scan_subdivision(text: str) -> str | None:
    if not text:
        return None
    idx = _subdivision_index()
    seen: set[str] = set()
    for token in _WORD.findall(text):
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        code = idx.get(key)
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
        resp = httpx.get(
            self.url,
            params=params or None,
            timeout=self.timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
        rows = resp.json().get("listview", [])
        out: list[RawIncident] = []
        for r in rows:
            if not isinstance(r, list) or len(r) < 5:
                continue
            summary_html = r[2] or ""
            location_html = r[4] or ""
            date_s = r[1] or ""
            report_date = ""
            if date_s:
                try:
                    report_date = datetime.strptime(
                        date_s, "%d %b %Y"
                    ).replace(tzinfo=UTC).isoformat()
                except ValueError:
                    report_date = date_s
            m = _ALERTID.search(summary_html)
            alert_id = m.group(1) if m else ""
            source_url = ("https://www.healthmap.org/ai.php?" + alert_id) if alert_id else ""
            country = _strip(location_html)
            sub_code = _scan_subdivision(_strip(summary_html))
            out.append(
                RawIncident(
                    source_name=self.source_name,
                    incident_name=_strip(summary_html),
                    country=country,
                    disaster_type="Disease",
                    report_date=report_date,
                    source_url=source_url,
                    raw_fields={
                        "summary": r[2],
                        "date": r[1],
                        "disease": r[3],
                        "location": r[4],
                        "event_id": m.group(1) if m else "",
                        "subdivision": sub_code or "",
                    },
                )
            )
        return out
