from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx

from disaster_report.sources.base import RawIncident

_DEFAULT_URL = "https://www.gdacs.org/xml/rss_24h.xml"
_NS = {"g": "http://www.gdacs.org"}
_TYPES = {
    "FL": "Flood",
    "EQ": "Earthquake",
    "TC": "Tropical Cyclone",
    "VO": "Volcano",
    "DR": "Drought",
    "WF": "Wildfire",
}
_EVENTID_RE = re.compile(r"[?&]eventid=(\d+)", re.IGNORECASE)


def _iso(s: str) -> str:
    if not s:
        return ""
    try:
        return parsedate_to_datetime(s).isoformat()
    except (TypeError, ValueError):
        return s


class GDACSAdapter:
    source_name = "GDACS"

    def __init__(self, url: str = _DEFAULT_URL, timeout: float = 30.0) -> None:
        self.url = url
        self.timeout = timeout

    def fetch(self) -> list[RawIncident]:
        resp = httpx.get(self.url, timeout=self.timeout, follow_redirects=True)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        out: list[RawIncident] = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            et = (item.findtext("g:eventtype", default="", namespaces=_NS) or "").strip()
            country = (
                item.findtext("g:country", default="", namespaces=_NS) or ""
            ).strip()
            fromdate = (
                item.findtext("g:fromdate", default="", namespaces=_NS) or ""
            ).strip()
            eventid_match = _EVENTID_RE.search(link)
            event_id = eventid_match.group(1) if eventid_match else ""
            pop_elt = item.find("g:population", namespaces=_NS)
            population_value = pop_elt.get("value", "0") if pop_elt is not None else "0"
            raw_fields = {
                "eventtype": et,
                "country": country,
                "fromdate": fromdate,
                "event_id": event_id,
                "episodeid": item.findtext("g:episodeid", default="", namespaces=_NS) or "",
                "alertlevel": item.findtext("g:alertlevel", default="", namespaces=_NS) or "",
                "alertscore": item.findtext("g:alertscore", default="0", namespaces=_NS) or "0",
                "severity": item.findtext("g:severity", default="", namespaces=_NS) or "",
                "population": population_value,
            }
            out.append(
                RawIncident(
                    source_name=self.source_name,
                    incident_name=title,
                    country=country,
                    disaster_type=_TYPES.get(et, et),
                    report_date=_iso(fromdate),
                    source_url=link,
                    raw_fields=raw_fields,
                )
            )
        return out
