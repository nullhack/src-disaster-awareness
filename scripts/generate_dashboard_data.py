#!/usr/bin/env python3
"""Generate dashboard JSON data from the v4 disaster_report DB.

Outputs daily digest files (YYYY-MM-DD.json), index.json, and aggregation
files (agg/{1,3,7,30,90,365}.json + agg/index.json) under dashboard/data/.
"""

from __future__ import annotations

import argparse
import json
import tomllib
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from disaster_report._country_names import country_name
from disaster_report.store.content import ContentStore

SCHEMA_VERSION = "1.4"
TRACKING_WINDOW_DAYS = 7
DEFAULT_TRACKING_WINDOW_DAYS = 7
MIN_SEVERITY = "LOW"

SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
SEVERITY_NAMES = {v: k for k, v in SEVERITY_RANK.items()}

COUNTRY_GROUPS_A = frozenset({
    "AF", "BD", "BT", "BN", "KH", "CN", "IN", "ID", "JP", "LA",
    "MY", "MV", "MM", "NP", "KP", "PK", "PH", "SG", "KR", "LK",
    "TW", "TH", "TL", "VN",
})
COUNTRY_GROUPS_B = frozenset({
    "AU", "FJ", "PF", "GU", "KZ", "KI", "KG", "MP", "MH", "FM",
    "MN", "NR", "NC", "NZ", "NU", "PW", "PG", "WS", "SB", "TJ",
    "TO", "TM", "TV", "UZ", "VU", "WF", "BH", "CY", "IR", "IQ",
    "JO", "KW", "LB", "OM", "PS", "IL", "QA", "SA", "SY", "TR",
    "AE", "YE", "DZ", "EG", "MA", "TN",
})

PRIORITY_MATRIX = {
    (4, "A"): ("HIGH", True), (4, "B"): ("HIGH", True), (4, "C"): ("HIGH", True),
    (3, "A"): ("HIGH", True), (3, "B"): ("MEDIUM", True), (3, "C"): ("MEDIUM", True),
    (2, "A"): ("MEDIUM", True), (2, "B"): ("MEDIUM", True), (2, "C"): ("LOW", False),
    (1, "A"): ("LOW", False), (1, "B"): ("LOW", False), (1, "C"): ("LOW", False),
}

PANDEMIC_RISK_DISEASES = frozenset({
    "ebola", "marburg", "mpox", "monkeypox", "nipah", "h5n1", "sars", "mers",
    "lassa", "crimean-congo", "rift valley", "hantavirus",
})
OUTBREAK_OF_CONCERN_DISEASES = frozenset({
    "cholera", "measles", "polio", "poliomyelitis", "yellow fever", "plague",
    "anthrax", "diphtheria", "avian influenza", "avian flu",
})
ENDEMIC_DISEASES = frozenset({
    "covid-19", "covid", "coronavirus", "influenza", "flu", "fever",
    "undiagnosed",
})

DISEASE_TYPES = frozenset({"disease", "epidemic", "outbreak", "epidemics"})
HIGH_IMPACT_TYPES = frozenset({"tsunami", "volcano", "volcanic eruption"})

REGION_MAP = {
    "Africa": frozenset({"DZ","AO","BJ","BW","BF","BI","CM","CV","CF","TD","KM","CD","DJ","EG","GQ","ER","SZ","ET","GA","GM","GH","GN","GW","CI","KE","LS","LR","LY","MG","MW","ML","MR","MU","MA","MZ","NA","NE","NG","RW","ST","SN","SC","SL","SO","ZA","SS","SD","TZ","TG","TN","UG","EH","ZM","ZW"}),
    "Americas": frozenset({"AI","AG","AR","AW","BS","BB","BZ","BM","BO","BQ","BR","CA","KY","CL","CO","CR","CU","CW","DM","DO","EC","SV","FK","GF","GL","GD","GP","GT","GY","HT","HN","JM","MQ","MX","MS","NI","PA","PY","PE","PR","BL","KN","LC","MF","PM","VC","SX","GS","TT","TC","US","UY","VE","VG","VI"}),
    "Asia": frozenset({"AF","AM","AZ","BH","BD","BT","BN","KH","CN","CY","GE","IN","ID","IR","IQ","IL","JP","JO","KZ","KP","KR","KW","KG","LA","LB","MO","MY","MV","MN","MM","NP","OM","PK","PS","PH","QA","SA","SG","LK","SY","TW","TJ","TH","TL","TR","TM","AE","UZ","VN","YE"}),
    "Europe": frozenset({"AL","AD","AT","BY","BE","BA","BG","HR","CZ","DK","EE","FO","FI","FR","DE","GI","GR","GG","HU","IS","IE","IM","IT","JE","LV","LI","LT","LU","MK","MT","MD","MC","ME","NL","NO","PL","PT","RO","RU","SM","RS","SK","SI","ES","SJ","SE","CH","UA","GB","VA"}),
    "Oceania": frozenset({"AS","AU","CK","FJ","PF","GU","KI","MH","FM","NR","NC","NZ","NU","NF","MP","PW","PG","PN","WS","SB","TK","TO","TV","VU","WF"}),
    "Antarctica": frozenset({"AQ","BV","HM","GS","IO","TF","CC","CX","NF"}),
}

ISO2_TO_REGION: dict[str, str] = {}
for region, codes in REGION_MAP.items():
    for code in codes:
        ISO2_TO_REGION[code] = region

ISO2_CENTROIDS: dict[str, tuple[float, float]] = {
    "AF": (33.9, 67.7), "AL": (41.2, 20.2), "DZ": (28.0, 1.7), "AD": (42.5, 1.5),
    "AO": (-11.2, 17.9), "AG": (17.1, -61.8), "AR": (-38.4, -63.6), "AM": (40.1, 45.0),
    "AU": (-25.3, 133.8), "AT": (47.5, 14.6), "AZ": (40.1, 47.6), "BS": (25.0, -78.0),
    "BH": (26.1, 50.6), "BD": (23.7, 90.4), "BB": (13.2, -59.5), "BY": (53.7, 27.9),
    "BE": (50.5, 4.5), "BZ": (17.2, -88.5), "BJ": (9.3, 2.3), "BT": (27.5, 90.4),
    "BO": (-16.3, -63.6), "BA": (43.9, 17.7), "BW": (-22.3, 24.7), "BR": (-14.2, -51.9),
    "BN": (4.5, 114.7), "BG": (42.7, 25.5), "BF": (12.2, -1.6), "BI": (-3.4, 29.9),
    "KH": (12.6, 104.9), "CM": (7.4, 12.4), "CA": (56.1, -106.3), "CV": (16.0, -24.0),
    "CF": (6.6, 20.9), "TD": (15.5, 18.7), "CL": (-35.7, -71.5), "CN": (35.9, 104.2),
    "CO": (4.6, -74.3), "KM": (-11.6, 43.3), "CD": (-4.0, 21.8), "CG": (-0.7, 23.7),
    "CR": (9.7, -83.8), "CI": (7.5, -5.5), "HR": (45.1, 15.2), "CU": (21.5, -77.8),
    "CY": (35.1, 33.4), "CZ": (49.8, 15.5), "DK": (56.3, 9.5), "DJ": (11.8, 42.6),
    "DO": (18.7, -70.7), "EC": (-1.8, -78.2), "EG": (26.8, 30.8), "SV": (13.8, -88.9),
    "GQ": (1.7, 10.3), "ER": (15.2, 39.8), "EE": (58.6, 25.0), "SZ": (-26.5, 31.5),
    "ET": (9.1, 40.5), "FJ": (-16.6, 179.4), "FI": (61.9, 25.7), "FR": (46.2, 2.2),
    "GA": (-0.8, 11.6), "GM": (13.4, -16.6), "GE": (42.3, 43.4), "DE": (51.2, 10.5),
    "GH": (7.9, -1.0), "GR": (39.1, 21.8), "GD": (12.3, -61.7), "GT": (15.8, -90.2),
    "GN": (9.9, -9.7), "GW": (11.8, -15.2), "GY": (4.9, -58.9), "HT": (18.9, -72.3),
    "HN": (15.2, -86.2), "HK": (22.4, 114.2), "HU": (47.2, 19.5), "IS": (64.9, -19.0),
    "IN": (20.6, 78.9), "ID": (-0.8, 113.9), "IR": (32.4, 53.7), "IQ": (33.2, 43.7),
    "IE": (53.4, -8.2), "IL": (31.0, 34.9), "IT": (41.9, 12.6), "JM": (18.1, -77.3),
    "JP": (36.2, 138.3), "JO": (30.6, 36.2), "KZ": (48.0, 66.9), "KE": (-0.0, 37.9),
    "KI": (-3.4, 173.0), "KP": (40.3, 127.5), "KR": (35.9, 127.8), "KW": (29.3, 47.5),
    "KG": (41.2, 74.8), "LA": (19.9, 102.5), "LV": (56.9, 24.6), "LB": (33.9, 35.9),
    "LS": (-29.6, 28.2), "LR": (6.4, -9.4), "LY": (26.3, 17.2), "LT": (55.2, 23.9),
    "LU": (49.8, 6.1), "MO": (22.2, 113.5), "MK": (41.6, 21.7), "MG": (-18.8, 47.1),
    "MW": (-13.2, 34.3), "MY": (4.2, 109.7), "MV": (3.2, 73.2), "ML": (17.6, -4.0),
    "MT": (35.9, 14.4), "MR": (21.0, -10.9), "MU": (-20.3, 57.6), "MX": (23.6, -102.6),
    "MD": (47.4, 28.4), "MN": (46.9, 103.8), "ME": (42.7, 19.4), "MA": (31.8, -7.1),
    "MZ": (-18.7, 35.5), "MM": (21.9, 95.9), "NA": (-22.9, 18.5), "NP": (28.4, 84.1),
    "NL": (52.1, 5.3), "NZ": (-40.9, 174.9), "NI": (12.9, -85.2), "NE": (17.6, 8.1),
    "NG": (9.1, 8.7), "NO": (60.5, 8.5), "OM": (21.5, 55.9), "PK": (30.4, 69.3),
    "PS": (31.9, 35.2), "PA": (8.5, -80.8), "PG": (-6.3, 143.9), "PY": (-23.4, -58.4),
    "PE": (-9.2, -75.0), "PH": (12.9, 121.8), "PL": (51.9, 19.1), "PT": (39.4, -8.2),
    "PR": (18.2, -66.6), "QA": (25.4, 51.2), "RO": (45.9, 24.97), "RU": (61.5, 105.3),
    "RW": (-1.9, 29.9), "SA": (23.9, 45.1), "SN": (14.5, -14.5), "RS": (44.0, 21.7),
    "SC": (-4.7, 55.5), "SL": (8.5, -11.8), "SG": (1.4, 103.8), "SK": (48.7, 19.7),
    "SI": (46.2, 14.99), "SO": (5.2, 46.2), "ZA": (-30.6, 22.9), "SS": (6.9, 31.3),
    "LK": (7.9, 80.8), "SD": (12.9, 30.2), "SR": (3.9, -56.0), "SE": (60.1, 18.6),
    "CH": (46.8, 8.2), "SY": (34.8, 38.9), "TW": (23.7, 121.0), "TJ": (38.9, 71.3),
    "TZ": (-6.4, 34.9), "TH": (15.9, 100.99), "TL": (-8.9, 125.7), "TG": (8.6, 0.8),
    "TO": (-21.2, -175.2), "TT": (10.7, -61.2), "TN": (33.9, 9.5), "TR": (38.9, 35.2),
    "TM": (38.97, 59.6), "UG": (1.4, 32.3), "UA": (48.9, 31.2), "AE": (23.4, 53.8),
    "GB": (55.4, -3.4), "US": (37.1, -95.7), "UY": (-32.5, -55.8), "UZ": (41.4, 64.6),
    "VU": (-16.4, 167.3), "VE": (6.4, -66.6), "VN": (14.1, 108.3), "YE": (15.6, 48.5),
    "ZM": (-13.1, 27.8), "ZW": (-19.0, 29.2), "WS": (-13.6, -172.4),
    "FK": (-51.8, -59.2), "GL": (-71.7, -42.6), "PF": (-17.7, -149.4), "NC": (-21.3, 165.5),
    "SB": (-9.4, 160.2), "TV": (-7.5, 178.7), "FM": (7.4, 150.5), "PW": (7.5, 134.5), "MH": (7.1, 171.2),
    "NR": (-0.5, 166.9), "NU": (-19.0, -169.6), "CK": (-21.2, -159.8), "NF": (-29.0, 167.9),
    "WF": (-13.3, -176.2), "PN": (-24.7, -127.4), "AS": (-14.3, -170.7), "GU": (13.4, 144.8),
    "MP": (15.2, 145.3), "CX": (-10.4, 105.7),
    "CC": (-12.2, 96.8), "IO": (-6.3, 71.8), "TF": (-49.3, 69.3), "GS": (-54.4, -36.6),
    "AQ": (-82.9, 135.0), "BV": (-54.4, 3.4), "HM": (-53.1, 72.5), "EH": (24.2, -12.9),
    "ST": (0.2, 6.6),
    "KY": (19.3, -81.2), "BM": (32.3, -64.8), "AW": (12.5, -69.9), "BQ": (12.2, -68.3),
    "CW": (12.1, -68.9), "SX": (18.0, -63.1), "TC": (21.7, -71.6), "DM": (15.4, -61.4),
    "BL": (17.9, -62.8), "MF": (18.1, -63.1), "PM": (46.8, -56.3), "KN": (17.4, -62.7),
    "LC": (13.9, -61.0), "VC": (13.2, -61.2), "MS": (16.7, -62.2),
    "AI": (18.2, -63.1), "VG": (18.4, -64.6), "VI": (18.3, -64.9),
    "JE": (49.2, -2.1), "GG": (49.5, -2.6), "IM": (54.2, -4.5),
    "LI": (47.2, 9.6), "MC": (43.7, 7.4), "SM": (43.9, 12.5), "VA": (41.9, 12.4),
    "SJ": (77.5, 23.0), "FO": (62.0, -7.0), "GI": (36.1, -5.3), "RE": (-21.1, 55.5),
    "MQ": (14.6, -61.0), "GP": (16.3, -61.6), "GF": (3.9, -53.1),
}


def country_group(iso2: str) -> str:
    if iso2 in COUNTRY_GROUPS_A:
        return "A"
    if iso2 in COUNTRY_GROUPS_B:
        return "B"
    return "C"


def parse_disease_name(name: str) -> str | None:
    lowered = name.lower()
    for keyword in sorted(PANDEMIC_RISK_DISEASES | OUTBREAK_OF_CONCERN_DISEASES | {"covid-19", "covid", "influenza", "flu", "chikungunya", "oropouche", "hantavirus", "antimicrobial", "respiratory", "food safety", "hepatitis", "meningitis", "pneumonia", "cancer"}, key=len, reverse=True):
        if keyword in lowered:
            return keyword.title()
    return None


def parse_pandemic_potential(disease_name: str | None) -> str | None:
    if not disease_name:
        return None
    lowered = disease_name.lower()
    if any(k in lowered for k in PANDEMIC_RISK_DISEASES):
        return "HIGH"
    if any(k in lowered for k in OUTBREAK_OF_CONCERN_DISEASES):
        return "MEDIUM"
    if any(k in lowered for k in ENDEMIC_DISEASES):
        return "LOW"
    return "MEDIUM"


def derive_geophysical_severity(mag: float | None, sig: int, tsunami: bool, gdacs_alert: str | None, news_count: int) -> int:
    candidates = [1]
    if mag is not None:
        if mag >= 7.0:
            candidates.append(3)
        elif mag >= 5.0:
            candidates.append(2)
    if sig >= 600:
        candidates.append(3)
    if tsunami:
        candidates.append(3)
    alert = (gdacs_alert or "").lower()
    if alert == "red":
        candidates.append(3)
    elif alert == "orange":
        candidates.append(2)
    if news_count >= 50:
        candidates.append(4)
    elif news_count >= 15:
        candidates.append(3)
    elif news_count >= 5:
        candidates.append(2)
    return max(candidates)


def derive_disease_severity(disease_name: str | None, pandemic_potential: str | None) -> int:
    pp_rank = SEVERITY_RANK.get(pandemic_potential, 0) if pandemic_potential else 0
    if pp_rank >= 3:
        return 3
    if disease_name:
        lowered = disease_name.lower()
        if any(k in lowered for k in PANDEMIC_RISK_DISEASES):
            return 3
        if any(k in lowered for k in OUTBREAK_OF_CONCERN_DISEASES):
            return 2
    return 2


def classify(severity_level: int, group: str, disease_name: str | None, incident_type: str, pandemic_pot: str | None, population: int, source_count: int) -> tuple[str, bool]:
    priority, should_report = PRIORITY_MATRIX.get((severity_level, group), ("LOW", False))
    kind = incident_type.lower()
    is_disease = kind in DISEASE_TYPES or (disease_name is not None)
    if is_disease:
        effective_pp = pandemic_pot
        if disease_name and any(k in disease_name.lower() for k in ENDEMIC_DISEASES) and effective_pp:
            pp_rank = SEVERITY_RANK.get(effective_pp, 1)
            effective_pp = SEVERITY_NAMES.get(min(pp_rank, 1))
        if effective_pp:
            pp_rank = SEVERITY_RANK.get(effective_pp, 0)
            if pp_rank >= 3:
                should_report = True
                priority = "HIGH" if SEVERITY_RANK.get(priority, 9) > 1 else priority
            elif pp_rank == 2:
                should_report = True
                priority = "MEDIUM" if SEVERITY_RANK.get(priority, 9) > 2 else priority
        else:
            if disease_name and any(k in disease_name.lower() for k in PANDEMIC_RISK_DISEASES):
                should_report = True
                priority = "HIGH" if SEVERITY_RANK.get(priority, 9) > 1 else priority
            elif disease_name and any(k in disease_name.lower() for k in OUTBREAK_OF_CONCERN_DISEASES) and severity_level >= 2:
                should_report = True
                priority = "MEDIUM" if SEVERITY_RANK.get(priority, 9) > 2 else priority
    if kind in HIGH_IMPACT_TYPES and severity_level >= 2:
        should_report = True
        priority = "MEDIUM" if SEVERITY_RANK.get(priority, 9) > 2 else priority
    if population >= 100000:
        should_report = True
        priority = "MEDIUM" if SEVERITY_RANK.get(priority, 9) > 2 else priority
    elif population >= 10000 and severity_level >= 2:
        should_report = True
    if source_count >= 2 and severity_level >= 2:
        should_report = True
        priority = "MEDIUM" if SEVERITY_RANK.get(priority, 9) > 2 else priority
    return priority, should_report


def short_type(incident_type: str, is_disease: bool) -> str:
    if is_disease:
        return "Disease"
    return incident_type


def load_incidents(store: ContentStore) -> list[dict]:
    return [
        {
            "incident_id": inc.incident_id,
            "incident_category": inc.incident_category,
            "incident_type": inc.incident_type,
            "name": inc.name,
            "first_seen_at": inc.first_seen_at,
            "genesis_report_id": inc.genesis_report_id,
        }
        for inc in store.read_incidents()
    ]


def load_reports_for_incident(store: ContentStore, incident_id: str) -> list[dict]:
    reports = []
    for rid in store.read_report_ids_for_incident(incident_id):
        r = store.read_source_report_by_id(rid)
        if r is None:
            continue
        reports.append({
            "report_id": rid,
            "source": r.source,
            "source_id": r.source_id,
            "incident_type": r.incident_type,
            "name": r.name,
            "report_date": r.report_date,
            "raw_fields": dict(r.raw_fields) if r.raw_fields else {},
        })
    reports.sort(key=lambda x: x["report_date"])
    return reports


def load_places_for_report(store: ContentStore, report_id: str) -> list[dict]:
    return [
        {"country_code": p.country_code, "subdivision": p.subdivision, "locality": p.locality}
        for p in store.read_report_places(report_id)
    ]


def _news_to_dict(n: object) -> dict:
    return {
        "news_id": getattr(n, "news_id", ""),
        "url": getattr(n, "url", ""),
        "headline": getattr(n, "title", ""),
        "body": getattr(n, "body", ""),
        "published_date": getattr(n, "published_date", ""),
        "outlet": getattr(n, "source", "") or getattr(n, "domain", "") or "",
        "image": getattr(n, "image", ""),
    }


def load_news_for_incident(store: ContentStore, incident_id: str) -> list[dict]:
    news = [_news_to_dict(n) for n in store.read_news(incident_id)]
    news.sort(key=lambda x: x["published_date"])
    return news


def load_latest_log(store: ContentStore, incident_id: str) -> str | None:
    timeline = store.read_timeline(incident_id)
    if not timeline:
        return None
    return timeline[-1].summary


def load_log_count(store: ContentStore, incident_id: str) -> int:
    return len(store.read_timeline(incident_id))


def load_logs_for_incident(store: ContentStore, incident_id: str) -> list[dict]:
    logs: list[dict] = []
    for log, linked_news in store.read_logs_with_news(incident_id):
        logs.append({
            "log_date": log.log_date,
            "summary": log.summary or "",
            "news": [_news_to_dict(n) for n in linked_news],
        })
    return logs


def build_incident_object(store: ContentStore, inc: dict, as_of_date: datetime) -> dict | None:
    incident_id = inc["incident_id"]
    reports = load_reports_for_incident(store, incident_id)
    if not reports:
        return None

    news = load_news_for_incident(store, incident_id)
    news_count = len(news)
    latest_summary = load_latest_log(store, incident_id)
    logs = load_logs_for_incident(store, incident_id)

    genesis = None
    for r in reports:
        if r["report_id"] == inc["genesis_report_id"]:
            genesis = r
            break
    if genesis is None:
        genesis = reports[0]

    all_places = []
    for r in reports:
        places = load_places_for_report(store, r["report_id"])
        all_places.extend(places)

    iso2 = ""
    for p in all_places:
        if p["country_code"] and len(p["country_code"]) == 2:
            iso2 = p["country_code"]
            break

    country = country_name(iso2) if iso2 else ""
    group = country_group(iso2) if iso2 else "C"
    region = ISO2_TO_REGION.get(iso2, "Unknown") if iso2 else "Unknown"

    is_disease = inc["incident_category"] == "disease"
    inc_type = inc["incident_type"] or ""
    disease_name = parse_disease_name(inc["name"]) if is_disease else None
    pandemic_pot = parse_pandemic_potential(disease_name) if is_disease else None

    max_mag = None
    max_sig = 0
    tsunami = False
    gdacs_alert = None
    lat = None
    lon = None
    gdacs_pop = 0
    max_depth = None
    felt = None
    place_str = ""

    for r in reports:
        rf = r["raw_fields"]
        if r["source"] == "USGS":
            mag = rf.get("mag")
            if mag is not None:
                max_mag = max(max_mag or 0, float(mag))
            sig = rf.get("sig") or 0
            max_sig = max(max_sig, int(sig))
            if rf.get("tsunami"):
                tsunami = True
            coords = rf.get("geometry", {}).get("coordinates")
            if coords and len(coords) >= 2:
                lon = lon or coords[0]
                lat = lat or coords[1]
            if rf.get("depth") is not None:
                d = float(rf["depth"])
                max_depth = min(max_depth or d, d) if max_depth else d
            if rf.get("felt") is not None:
                felt = felt or int(rf["felt"])
            if rf.get("place"):
                place_str = place_str or rf["place"]
        elif r["source"] == "GDACS":
            alert = rf.get("alertlevel", "")
            if alert:
                if not gdacs_alert or SEVERITY_RANK.get(alert.capitalize(), 0) > SEVERITY_RANK.get(gdacs_alert.capitalize(), 0):
                    gdacs_alert = alert.capitalize()
            if rf.get("geo_lat") and lat is None:
                lat = float(rf["geo_lat"])
            if rf.get("geo_long") and lon is None:
                lon = float(rf["geo_long"])
            if rf.get("severity") and max_mag is None:
                try:
                    max_mag = float(rf["severity"])
                except (ValueError, TypeError):
                    pass
            if rf.get("place") and not place_str:
                place_str = rf.get("country", "") or rf.get("title", "")

    if is_disease:
        severity_level = derive_disease_severity(disease_name, pandemic_pot)
    else:
        severity_level = derive_geophysical_severity(max_mag, max_sig, tsunami, gdacs_alert, news_count)

    priority, should_report = classify(
        severity_level, group, disease_name,
        "disease" if is_disease else inc_type.lower(),
        pandemic_pot, gdacs_pop, len(reports)
    )

    severity_name = SEVERITY_NAMES.get(severity_level, "LOW")
    priority_rank = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(priority, 3)

    event_date = inc["first_seen_at"] or genesis["report_date"] or ""
    event_date_short = event_date[:10] if event_date else ""

    last_updated = ""
    if news:
        last_updated = max(n["published_date"][:10] for n in news)
    elif reports:
        last_updated = max(r["report_date"] for r in reports if r["report_date"])

    days_since = (as_of_date.date() - datetime.fromisoformat(event_date_short).date()).days if event_date_short else 0

    source_counts = {"who_don": 0, "usgs": 0, "gdacs": 0, "healthmap": 0, "news": news_count}
    for r in reports:
        if r["source"] == "WHO":
            source_counts["who_don"] += 1
        elif r["source"] == "USGS":
            source_counts["usgs"] += 1
        elif r["source"] == "GDACS":
            source_counts["gdacs"] += 1

    source_links = []
    for r in reports:
        rf = r["raw_fields"]
        if r["source"] == "USGS":
            source_links.append({
                "type": "USGS",
                "label": rf.get("title", r["name"]),
                "url": rf.get("url", ""),
                "meta": f"{rf.get('depth', '?')} km depth" if rf.get("depth") else "",
            })
        elif r["source"] == "GDACS":
            alert_label = f"{rf.get('alertlevel', '')} alert" if rf.get("alertlevel") else ""
            meta_parts = []
            if rf.get("severitytext"):
                meta_parts.append(rf["severitytext"])
            source_links.append({
                "type": "GDACS",
                "label": f"{alert_label} · {rf.get('severitytext', r['name'])}" if alert_label else r["name"],
                "url": rf.get("link", ""),
                "meta": " · ".join(meta_parts) if meta_parts else "",
            })
        elif r["source"] == "WHO":
            who_url = rf.get("ItemDefaultUrl", "")
            if who_url and not who_url.startswith("http"):
                who_url = "https://www.who.int/emergencies/disease-outbreak-news/item/" + who_url.lstrip("/")
            source_links.append({
                "type": "WHO",
                "label": r["name"],
                "url": who_url,
                "meta": "",
            })

    type_code = "EQ" if inc_type == "Earthquake" else \
                "FL" if inc_type == "Flood" else \
                "WF" if inc_type in ("Forest Fire", "Wildfire") else \
                "TC" if inc_type == "Tropical Cyclone" else \
                "VO" if inc_type == "Volcano" else \
                "DR" if inc_type == "Drought" else \
                "TS" if inc_type == "Tsunami" else \
                "DI" if is_disease else "OT"

    date_part = event_date_short.replace("-", "") if event_date_short else "00000000"
    dashboard_id = f"{date_part}-{iso2 or 'XX'}-{type_code}"

    canonical_name = inc["name"]
    if not is_disease and max_mag is not None:
        canonical_name = f"{inc_type} {place_str or country} {event_date_short[:7] if event_date_short else ''}".strip()

    physical = {
        "max_magnitude": max_mag,
        "max_depth_km": max_depth,
        "place": place_str,
        "felt": felt,
        "sig": max_sig if max_sig else None,
        "tsunami": bool(tsunami),
        "gdacs_alertlevel": gdacs_alert,
        "gdacs_population": gdacs_pop if gdacs_pop else None,
    }

    news_items = [
        {
            "headline": n["headline"] or "",
            "url": n["url"],
            "outlet": n["outlet"] or "",
            "published_date": n["published_date"],
        }
        for n in news
    ]

    if lat is None and iso2 and iso2 in ISO2_CENTROIDS:
        lat, lon = ISO2_CENTROIDS[iso2]

    return {
        "incident_id": dashboard_id,
        "canonical_name": canonical_name,
        "summary": latest_summary or "",
        "country": country,
        "iso2": iso2,
        "lat": lat,
        "lon": lon,
        "country_group": group,
        "region": region,
        "incident_type": short_type(inc_type, is_disease),
        "incident_category": "Biological" if is_disease else "Natural",
        "is_disease": is_disease,
        "severity": severity_name,
        "priority": priority,
        "priority_rank": priority_rank,
        "pandemic_potential": pandemic_pot,
        "event_status": None,
        "disease_name": disease_name,
        "event_date": event_date_short,
        "first_reported_date": event_date_short,
        "last_updated_date": last_updated,
        "days_since_event": days_since,
        "source_count": len(reports),
        "should_report": should_report,
        "search_keys": [],
        "sources": source_counts,
        "source_links": source_links,
        "physical": physical,
        "news": news_items,
        "news_total": news_count,
        "logs": logs,
    }


def is_active_on_date(inc_obj: dict, target_date: datetime, window_days: int) -> bool:
    if target_date.tzinfo is not None:
        target_date = target_date.replace(tzinfo=None)
    last_updated = inc_obj.get("last_updated_date", "")
    if inc_obj.get("news_total", 0) <= 0 or not last_updated:
        return False
    try:
        last_dt = datetime.fromisoformat(last_updated[:10])
    except ValueError:
        return False
    if last_dt > target_date:
        return False
    window_start = target_date - timedelta(days=window_days)
    return last_dt >= window_start


def generate_daily_digest(incidents: list[dict], target_date: datetime, as_of: datetime) -> dict:
    active = [i for i in incidents if is_active_on_date(i, target_date, TRACKING_WINDOW_DAYS)]
    reportable = list(active)

    sev_counts = Counter(i["severity"] for i in reportable)
    type_counts = Counter(i["incident_type"] for i in reportable)
    region_counts = Counter(i["region"] for i in reportable)

    by_country_map: dict[str, dict] = {}
    for i in reportable:
        iso2 = i.get("iso2", "")
        if not iso2:
            continue
        if iso2 not in by_country_map:
            by_country_map[iso2] = {
                "country": i["country"], "count": 0, "max_sev_rank": 4,
                "iso2": iso2, "region": i["region"], "country_group": i["country_group"],
                "max_severity": "LOW",
            }
        c = by_country_map[iso2]
        c["count"] += 1
        rank = SEVERITY_RANK.get(i["severity"], 1)
        if rank < c["max_sev_rank"]:
            c["max_sev_rank"] = rank
            c["max_severity"] = i["severity"]

    by_country = sorted(by_country_map.values(), key=lambda x: (x["max_sev_rank"], -x["count"]))

    news_total = sum(i["news_total"] for i in reportable)
    max_mag = max((i["physical"]["max_magnitude"] for i in reportable if i["physical"]["max_magnitude"] is not None), default=None)
    disease_count = sum(1 for i in reportable if i["is_disease"])
    countries_affected = len(set(i["iso2"] for i in reportable if i["iso2"]))

    yesterday = target_date - timedelta(days=1)
    prev_active_ids = {i["incident_id"] for i in incidents if is_active_on_date(i, yesterday, TRACKING_WINDOW_DAYS)}
    new_today = sum(1 for i in reportable if i["incident_id"] not in prev_active_ids)

    return {
        "schema_version": SCHEMA_VERSION,
        "report_date": target_date.strftime("%Y-%m-%d"),
        "generated_at": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": target_date.strftime("%Y-%m-%d"),
        "tracking_window_days": TRACKING_WINDOW_DAYS,
        "min_severity": MIN_SEVERITY,
        "summary": {
            "reportable_total": len(reportable),
            "new_today": new_today,
            "critical": sev_counts.get("CRITICAL", 0),
            "high": sev_counts.get("HIGH", 0),
            "medium": sev_counts.get("MEDIUM", 0),
            "low": sev_counts.get("LOW", 0),
            "disease_outbreaks": disease_count,
            "countries_affected": countries_affected,
            "news_total": news_total,
            "max_magnitude": max_mag,
            "by_severity": {s: sev_counts.get(s, 0) for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
            "by_type": dict(type_counts),
            "by_region": dict(region_counts),
        },
        "by_country": by_country,
        "incidents": reportable,
    }


def generate_agg_series(incidents: list[dict], window: int, as_of: datetime) -> list[dict]:
    series = []
    for i in range(window - 1, -1, -1):
        d = as_of - timedelta(days=i)
        active = [inc for inc in incidents if is_active_on_date(inc, d, TRACKING_WINDOW_DAYS)]
        reportable = list(active)

        sev_data = {}
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            matching = [inc for inc in reportable if inc["severity"] == sev]
            e_count = len(matching)
            n_count = sum(inc["news_total"] for inc in matching)
            sev_data[sev] = {"e": e_count, "n": n_count}

        type_data = {}
        for inc in reportable:
            t = inc["incident_type"]
            if t not in type_data:
                type_data[t] = {"e": 0, "n": 0}
            type_data[t]["e"] += 1
            type_data[t]["n"] += inc["news_total"]

        disease_data = {}
        for inc in reportable:
            if inc["is_disease"] and inc["disease_name"]:
                d_name = inc["disease_name"]
                if d_name not in disease_data:
                    disease_data[d_name] = {"e": 0, "n": 0}
                disease_data[d_name]["e"] += 1
                disease_data[d_name]["n"] += inc["news_total"]

        region_data = {}
        for inc in reportable:
            r = inc["region"] or "Unknown"
            if r not in region_data:
                region_data[r] = {"e": 0, "n": 0}
            region_data[r]["e"] += 1
            region_data[r]["n"] += inc["news_total"]

        series.append({
            "date": d.strftime("%Y-%m-%d"),
            "sev": sev_data,
            "type": type_data,
            "disease": disease_data,
            "region": region_data,
        })
    return series


def _resolve_tracking_window(config_path: str = "config.toml") -> int:
    try:
        with open(config_path, "rb") as fp:
            data = tomllib.load(fp)
        return int(data.get("ingest", {}).get("active_window_days", DEFAULT_TRACKING_WINDOW_DAYS))
    except (FileNotFoundError, ValueError, TypeError, KeyError):
        return DEFAULT_TRACKING_WINDOW_DAYS


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate dashboard JSON from v5 content tree")
    parser.add_argument("--tree-root", default="data")
    parser.add_argument("--output", default="dashboard/data")
    parser.add_argument("--as-of", default=None, help="Override as-of date (YYYY-MM-DD)")
    parser.add_argument("--tracking-window", type=int, default=None,
                        help="Override tracking window in days (default: ingest.active_window_days from config.toml)")
    args = parser.parse_args()

    global TRACKING_WINDOW_DAYS
    TRACKING_WINDOW_DAYS = args.tracking_window if args.tracking_window is not None else _resolve_tracking_window()
    print(f"  tracking window: {TRACKING_WINDOW_DAYS} days")

    if args.as_of:
        as_of = datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc)
    else:
        as_of = datetime.now(timezone.utc)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    agg_dir = output_dir / "agg"
    agg_dir.mkdir(exist_ok=True)

    store = ContentStore(args.tree_root)

    print("Loading incidents from content tree...")
    raw_incidents = load_incidents(store)
    print(f"  {len(raw_incidents)} incidents found")

    print("Building incident objects...")
    all_incidents = []
    for inc in raw_incidents:
        obj = build_incident_object(store, inc, as_of)
        if obj:
            all_incidents.append(obj)
    print(f"  {len(all_incidents)} incident objects built")

    earliest_event = None
    for inc in all_incidents:
        ed = inc.get("event_date")
        if ed:
            try:
                dt = datetime.fromisoformat(ed)
                if earliest_event is None or dt < earliest_event:
                    earliest_event = dt
            except ValueError:
                pass

    if earliest_event is None:
        earliest_event = as_of.replace(tzinfo=None) - timedelta(days=30)

    earliest_digest = earliest_event - timedelta(days=TRACKING_WINDOW_DAYS)
    as_of_naive = as_of.replace(tzinfo=None)
    total_days = (as_of_naive - earliest_digest).days + 1
    print(f"  Generating {total_days} daily digests from {earliest_digest.strftime('%Y-%m-%d')} to {as_of_naive.strftime('%Y-%m-%d')}")

    print("Generating daily digests...")
    digests_manifest = []
    for i in range(total_days):
        d = earliest_digest + timedelta(days=i)
        if d > as_of_naive:
            break
        digest = generate_daily_digest(all_incidents, d, as_of)
        if digest["summary"]["reportable_total"] > 0:
            filename = f"{d.strftime('%Y-%m-%d')}.json"
            with open(output_dir / filename, "w") as f:
                json.dump(digest, f, indent=2, ensure_ascii=False)
            digests_manifest.append({
                "date": digest["report_date"],
                "reportable_total": digest["summary"]["reportable_total"],
                "critical": digest["summary"]["critical"],
                "high": digest["summary"]["high"],
                "disease_outbreaks": digest["summary"]["disease_outbreaks"],
                "countries_affected": digest["summary"]["countries_affected"],
                "file": filename,
            })

    print(f"  {len(digests_manifest)} digest files written")

    index = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "digests": digests_manifest,
    }
    with open(output_dir / "index.json", "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print("  index.json written")

    print("Generating aggregation files...")
    agg_windows = [1, 3, 7, 30, 90, 365]
    agg_index = {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of.strftime("%Y-%m-%d"),
        "windows": [str(w) for w in agg_windows],
        "default_window": 30,
        "files": {str(w): f"{w}.json" for w in agg_windows},
    }
    with open(agg_dir / "index.json", "w") as f:
        json.dump(agg_index, f, indent=2, ensure_ascii=False)

    for window in agg_windows:
        series = generate_agg_series(all_incidents, window, as_of)
        agg = {
            "schema_version": SCHEMA_VERSION,
            "window": window,
            "bucket": "day",
            "as_of": as_of.strftime("%Y-%m-%d"),
            "series": series,
        }
        with open(agg_dir / f"{window}.json", "w") as f:
            json.dump(agg, f, indent=2, ensure_ascii=False)
        print(f"  agg/{window}.json ({len(series)} days)")

    print("Generating MD reports...")
    md_root = output_dir.parent / "reports"
    md_root.mkdir(parents=True, exist_ok=True)
    md_count = 0
    for i in range(total_days):
        d = earliest_digest + timedelta(days=i)
        if d > as_of_naive:
            break
        digest = generate_daily_digest(all_incidents, d, as_of)
        if digest["summary"]["reportable_total"] > 0:
            md = generate_md_report(digest, d)
            year = d.strftime("%Y")
            month = d.strftime("%m")
            fname = f"{d.strftime('%Y%m%d')}.md"
            md_dir = md_root / year / month
            md_dir.mkdir(parents=True, exist_ok=True)
            with open(md_dir / fname, "w") as f:
                f.write(md)
            md_count += 1
    print(f"  {md_count} MD reports written")

    print("Done.")


def _fmt_dt(iso_str: str) -> str:
    if not iso_str:
        return ""
    if len(iso_str) == 10:
        return iso_str
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return iso_str[:16]


def _join_summary_paragraphs(text: str) -> str:
    pieces = [p.strip() for p in text.split("\n") if p.strip()]
    out = []
    for p in pieces:
        if p[-1] not in ".!?":
            p += "."
        out.append(p)
    return " ".join(out)


def generate_md_report(digest: dict, target_date: datetime) -> str:
    s = digest["summary"]
    lines: list[str] = []
    lines.append(f"# Daily Disaster Digest — {target_date.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(
        f"**{s['reportable_total']} active incidents** · "
        f"{s['disease_outbreaks']} disease outbreaks · "
        f"{s['countries_affected']} countries · "
        f"{s['news_total']} news items"
    )
    if s["critical"] or s["high"]:
        lines.append(
            f"**{s['critical']} CRITICAL** · **{s['high']} HIGH** · "
            f"{s['medium']} MEDIUM · {s['low']} LOW"
        )
    lines.append("")

    high_plus = [
        i for i in digest["incidents"]
        if SEVERITY_RANK.get(i["severity"], 0) >= SEVERITY_RANK["HIGH"]
    ]
    high_plus.sort(key=lambda i: (-SEVERITY_RANK.get(i["severity"], 0), i.get("news_total", 0)), reverse=False)
    high_plus.sort(key=lambda i: -SEVERITY_RANK.get(i["severity"], 0))

    diseases = [i for i in high_plus if i["is_disease"]]
    geos = [i for i in high_plus if not i["is_disease"]]

    if geos:
        lines.append("## Geophysical")
        lines.append("")
        for inc in geos:
            _md_incident(lines, inc)
    if diseases:
        lines.append("## Disease Outbreaks")
        lines.append("")
        for inc in diseases:
            _md_incident(lines, inc)

    medium = [
        i for i in digest["incidents"]
        if SEVERITY_RANK.get(i["severity"], 0) == SEVERITY_RANK["MEDIUM"]
    ]
    if medium:
        lines.append("## Medium Severity")
        lines.append("")
        for inc in sorted(medium, key=lambda i: -i.get("news_total", 0)):
            name = inc["canonical_name"] or inc.get("incident_id", "")
            itype = inc["incident_type"] or "Unknown"
            news_n = inc.get("news_total", 0)
            lines.append(f"- **{name}** ({itype}) — {news_n} news · {inc.get('country', '')}")
        lines.append("")

    return "\n".join(lines) + "\n"


def _md_incident(lines: list[str], inc: dict) -> None:
    name = inc["canonical_name"] or inc.get("incident_id", "")
    itype = inc["incident_type"] or "Unknown"
    sev = inc["severity"]
    news_n = inc.get("news_total", 0)
    logs = inc.get("logs", [])
    country = inc.get("country", "")
    lines.append(f"### {name} — {itype}")
    meta_parts = [f"{sev}", f"{news_n} news", f"{len(logs)} logs"]
    if country:
        meta_parts.append(country)
    lines.append(f"*{' · '.join(meta_parts)}*")
    lines.append("")
    if logs:
        for log in logs:
            ldt = _fmt_dt(log.get("log_date", ""))
            n_linked = len(log.get("news", []))
            lines.append(f"**{ldt}** ({n_linked} article{'s' if n_linked != 1 else ''})")
            lines.append("")
            summary = _join_summary_paragraphs(log.get("summary", ""))
            if summary:
                lines.append(f"> {summary}")
                lines.append("")
    elif inc.get("summary"):
        lines.append(f"> {_join_summary_paragraphs(inc['summary'])}")
        lines.append("")
    lines.append("")


if __name__ == "__main__":
    main()
