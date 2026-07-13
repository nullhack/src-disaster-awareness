#!/usr/bin/env python3
"""Generate dashboard JSON data from the v4 disaster_report DB.

Outputs daily digest files (YYYY-MM-DD.json), index.json, and aggregation
files (agg/{7,30,90,365}.json + agg/index.json) under dashboard/data/.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from disaster_report._country_names import country_name

SCHEMA_VERSION = "1.4"
TRACKING_WINDOW_DAYS = 14
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
    "Antarctica": frozenset({"AQ","BV","HM","GS","IO","TF","CC","CX","HM","NF","AQ"}),
}

ISO2_TO_REGION: dict[str, str] = {}
for region, codes in REGION_MAP.items():
    for code in codes:
        ISO2_TO_REGION[code] = region


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


def load_incidents(conn: sqlite3.Connection) -> list[dict]:
    c = conn.cursor()
    c.execute("""
        SELECT i.incident_id, i.incident_category, i.incident_type, i.name,
               i.first_seen_at, i.genesis_report_id
        FROM incidents i
        ORDER BY i.incident_id
    """)
    incidents = []
    for row in c.fetchall():
        incidents.append({
            "incident_id": row[0],
            "incident_category": row[1],
            "incident_type": row[2],
            "name": row[3],
            "first_seen_at": row[4],
            "genesis_report_id": row[5],
        })
    return incidents


def load_reports_for_incident(conn: sqlite3.Connection, incident_id: int) -> list[dict]:
    c = conn.cursor()
    c.execute("""
        SELECT sr.report_id, sr.source, sr.source_id, sr.incident_type,
               sr.name, sr.report_date, sr.raw_fields
        FROM source_reports sr
        JOIN report_incidents ri ON ri.report_id = sr.report_id
        WHERE ri.incident_id = ?
        ORDER BY sr.report_date
    """, (incident_id,))
    reports = []
    for row in c.fetchall():
        reports.append({
            "report_id": row[0],
            "source": row[1],
            "source_id": row[2],
            "incident_type": row[3],
            "name": row[4],
            "report_date": row[5],
            "raw_fields": json.loads(row[6]) if row[6] else {},
        })
    return reports


def load_places_for_report(conn: sqlite3.Connection, report_id: int) -> list[dict]:
    c = conn.cursor()
    c.execute("SELECT country_code, subdivision, locality FROM report_places WHERE report_id = ?", (report_id,))
    return [{"country_code": row[0], "subdivision": row[1], "locality": row[2]} for row in c.fetchall()]


def load_news_for_incident(conn: sqlite3.Connection, incident_id: int) -> list[dict]:
    c = conn.cursor()
    c.execute("""
        SELECT ni.news_id, ni.url, ni.title, ni.body, ni.published_date,
               ni.source, ni.domain, ni.image
        FROM news_items ni
        JOIN news_incidents ni2 ON ni2.news_id = ni.news_id
        WHERE ni2.incident_id = ?
        ORDER BY ni.published_date
    """, (incident_id,))
    news = []
    for row in c.fetchall():
        news.append({
            "news_id": row[0],
            "url": row[1],
            "headline": row[2],
            "body": row[3],
            "published_date": row[4],
            "outlet": row[5] or row[6],
            "image": row[7],
        })
    return news


def load_latest_log(conn: sqlite3.Connection, incident_id: int) -> str | None:
    c = conn.cursor()
    c.execute("""
        SELECT summary FROM incident_logs
        WHERE incident_id = ?
        ORDER BY log_datetime DESC LIMIT 1
    """, (incident_id,))
    row = c.fetchone()
    return row[0] if row else None


def load_log_count(conn: sqlite3.Connection, incident_id: int) -> int:
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM incident_logs WHERE incident_id = ?", (incident_id,))
    return c.fetchone()[0]


def load_logs_for_incident(conn: sqlite3.Connection, incident_id: int) -> list[dict]:
    c = conn.cursor()
    c.execute("""
        SELECT il.log_datetime, il.summary
        FROM incident_logs il
        WHERE il.incident_id = ?
        ORDER BY il.log_datetime
    """, (incident_id,))
    logs = []
    for row in c.fetchall():
        logs.append({
            "log_datetime": row[0],
            "summary": row[1] or "",
            "news": [],
        })
    if not logs:
        return logs
    c.execute("""
        SELECT iln.log_datetime, iln.news_id, ni.url, ni.title,
               ni.published_date, ni.source, ni.domain
        FROM incident_log_news iln
        JOIN news_items ni ON ni.news_id = iln.news_id
        WHERE iln.incident_id = ?
        ORDER BY ni.published_date
    """, (incident_id,))
    log_map = {l["log_datetime"]: l for l in logs}
    for row in c.fetchall():
        ldt = row[0]
        if ldt in log_map:
            log_map[ldt]["news"].append({
                "news_id": row[1],
                "url": row[2],
                "headline": row[3] or "",
                "published_date": row[4],
                "outlet": row[5] or row[6] or "",
            })
    return logs


def build_incident_object(conn: sqlite3.Connection, inc: dict, as_of_date: datetime) -> dict | None:
    incident_id = inc["incident_id"]
    reports = load_reports_for_incident(conn, incident_id)
    if not reports:
        return None

    news = load_news_for_incident(conn, incident_id)
    news_count = len(news)
    latest_summary = load_latest_log(conn, incident_id)
    logs = load_logs_for_incident(conn, incident_id)

    genesis = None
    for r in reports:
        if r["report_id"] == inc["genesis_report_id"]:
            genesis = r
            break
    if genesis is None:
        genesis = reports[0]

    all_places = []
    for r in reports:
        places = load_places_for_report(conn, r["report_id"])
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
    event_date_str = inc_obj.get("event_date")
    last_updated = inc_obj.get("last_updated_date", "")
    if not event_date_str:
        return False
    try:
        event_date = datetime.fromisoformat(event_date_str)
    except ValueError:
        return False
    window_start = target_date - timedelta(days=window_days)
    if event_date > target_date:
        return False
    if last_updated:
        try:
            last_dt = datetime.fromisoformat(last_updated[:10])
            if last_dt > target_date:
                return False
        except ValueError:
            pass
    if event_date >= window_start:
        return True
    if inc_obj.get("news_total", 0) > 0 and last_updated:
        try:
            last_dt = datetime.fromisoformat(last_updated[:10])
            if last_dt >= window_start:
                return True
        except ValueError:
            pass
    return False


def generate_daily_digest(incidents: list[dict], target_date: datetime, as_of: datetime) -> dict:
    active = [i for i in incidents if is_active_on_date(i, target_date, TRACKING_WINDOW_DAYS)]
    reportable = [i for i in active if i["should_report"] and SEVERITY_RANK.get(i["severity"], 0) >= SEVERITY_RANK.get(MIN_SEVERITY, 0)]
    if not reportable:
        reportable = active

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
        reportable = [inc for inc in active if inc["should_report"]]

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate dashboard JSON from v4 DB")
    parser.add_argument("--db", default="disaster_report.db")
    parser.add_argument("--output", default="dashboard/data")
    parser.add_argument("--as-of", default=None, help="Override as-of date (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.as_of:
        as_of = datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc)
    else:
        as_of = datetime.now(timezone.utc)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    agg_dir = output_dir / "agg"
    agg_dir.mkdir(exist_ok=True)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    print("Loading incidents from DB...")
    raw_incidents = load_incidents(conn)
    print(f"  {len(raw_incidents)} incidents found")

    print("Building incident objects...")
    all_incidents = []
    for inc in raw_incidents:
        obj = build_incident_object(conn, inc, as_of)
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
    agg_index = {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of.strftime("%Y-%m-%d"),
        "windows": ["7", "30", "90", "365"],
        "default_window": 30,
        "files": {"7": "7.json", "30": "30.json", "90": "90.json", "365": "365.json"},
    }
    with open(agg_dir / "index.json", "w") as f:
        json.dump(agg_index, f, indent=2, ensure_ascii=False)

    for window in [7, 30, 90, 365]:
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

    conn.close()
    print("Done.")


def _fmt_dt(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return iso_str[:16] if iso_str else ""


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
            ldt = _fmt_dt(log.get("log_datetime", ""))
            n_linked = len(log.get("news", []))
            lines.append(f"**{ldt}** ({n_linked} article{'s' if n_linked != 1 else ''})")
            lines.append("")
            summary = log.get("summary", "")
            if summary:
                lines.append(f"> {summary}")
                lines.append("")
    elif inc.get("summary"):
        lines.append(f"> {inc['summary']}")
        lines.append("")
    lines.append("")


if __name__ == "__main__":
    main()
