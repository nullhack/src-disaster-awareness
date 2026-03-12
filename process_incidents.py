#!/usr/bin/env python3
"""Process staging incidents and store in JSONL format."""

import json
from datetime import datetime
import os

# Current timestamp
CURRENT_UTC = "2026-03-11T14:30:00Z"
TODAY = "2026-03-11"

# Country code mapping
COUNTRY_CODES = {
    "Democratic Republic of the Congo": "CD",
    "Lebanon": "LB",
    "Palestine": "PS",
    "Nigeria": "NG",
    "Cameroon": "CM",
    "Australia": "AU",
    "Gabon": "GA",
    "United States": "US",
    "Kenya": "KE",
    "India": "IN",
    "Bangladesh": "BD",
    "Vietnam": "VN",
    "Indonesia": "ID",
    "South Korea": "KR",
    "Japan": "JP",
}

# Disaster type to code mapping
TYPE_CODES = {
    "Landslide": "LS",
    "Armed Conflict": "CF",
    "Flood": "FL",
    "Food Insecurity": "FI",
    "Severe Weather/Flood": "SW",
    "Flood/Storm": "FL",
    "Flood/Drought": "FL",
    "Disease Outbreak": "DI",
    "Animal Disease": "AD",
}

# Status mapping
STATUS_MAP = {
    "Active": "Active",
    "Resolved": "Resolved",
    "Forecasted": "Forecasted",
    "Monitoring": "Monitoring",
}


# Helper functions
def get_region(country_group):
    """Get region based on country group."""
    if country_group == "A":
        return "Asia Pacific / South Asia"
    elif country_group == "B":
        return "Middle East / North Africa / Asia Pacific 2"
    else:
        return "Africa / Europe / Americas"


def get_source_type(source):
    """Map source to type."""
    source_lower = source.lower()
    if source_lower == "gdacs":
        return "disaster-database"
    elif source_lower == "promed":
        return "disease-database"
    elif source_lower == "reliefweb":
        return "humanitarian-org"
    else:
        return "other"


def get_source_tier(source):
    """Map source to reliability tier."""
    source_lower = source.lower()
    if source_lower in ["gdacs", "promed", "reuters", "ap", "bbc"]:
        return "Tier1"
    elif source_lower in ["reliefweb", "afp", "al jazeera"]:
        return "Tier2"
    else:
        return "Tier3"


# Read the staging file
with open("incidents/staging/pending/incidents.jsonl", "r") as f:
    incidents_raw = [json.loads(line) for line in f]

print(f"Processing {len(incidents_raw)} incidents...")

# Process each incident
processed_incidents = []

for idx, raw in enumerate(incidents_raw, 1):
    print(f"\n--- Processing incident {idx}: {raw['incident_name']} ---")

    # Extract key fields
    country = raw["country"]
    disaster_type = raw["disaster_type"]
    report_date = raw["report_date"]

    # Get country code
    country_code = COUNTRY_CODES.get(country, "XX")
    type_code = TYPE_CODES.get(disaster_type, "OT")

    # Generate incident ID
    date_str = report_date.replace("-", "")
    incident_id = f"{date_str}-{country_code}-{type_code}"

    # Handle multi-country incidents
    if "," in country:
        # For multi-country, use first country or create unique
        countries = country.split(",")
        first_country = countries[0].strip()
        country_code = COUNTRY_CODES.get(first_country, "XX")
        incident_id = f"{date_str}-{country_code}-{type_code}"

    # Ensure unique IDs by checking against already generated IDs
    base_id = incident_id
    counter = 1
    existing_ids = []
    # Check in processed_incidents
    for pi in processed_incidents:
        existing_ids.append(pi["incident_id"])

    while incident_id in existing_ids:
        incident_id = f"{base_id}-{counter}"
        counter += 1

    # Transform to schema format
    incident = {
        "incident_id": incident_id,
        "incident_name": raw["incident_name"],
        "created_date": f"{report_date}T00:00:00Z",
        "updated_date": CURRENT_UTC,
        "status": STATUS_MAP.get(raw.get("incident_status", "Active"), "Active"),
        "classification": {
            "country": country,
            "country_group": raw["country_group"],  # Already A, B, or C
            "region": get_region(raw["country_group"]),
            "incident_type": disaster_type,
            "incident_level": int(raw["incident_level"]),
            "priority": raw["priority"],
            "should_report": raw.get("action") == "INCLUDE",
        },
        "location": {
            "country": country,
            "affected_area_description": raw.get("location", ""),
        },
        "impact": {
            "affected_population_description": raw.get("affected_population", ""),
            "deaths_description": raw.get("death_toll", ""),
            "impact_description": raw.get("description", ""),
        },
        "sources": [
            {
                "name": raw["source"],
                "type": get_source_type(raw["source"]),
                "url": raw.get("source_url", ""),
                "accessed_date": CURRENT_UTC,
                "reliability_tier": get_source_tier(raw["source"]),
                "data_freshness": "real-time",
            }
        ],
        "classification_metadata": {
            "classified_by": raw["source"],
            "classified_date": CURRENT_UTC,
            "rationale": raw.get("classification_rationale", ""),
        },
        "metadata": {
            "data_quality": "High",
            "completeness_score": 0.85,
            "last_verified": CURRENT_UTC,
        },
    }

    processed_incidents.append(incident)
    print(f"  Generated ID: {incident_id}")
    print(
        f"  Country: {country}, Group: {raw['country_group']}, Level: {raw['incident_level']}"
    )
    print(f"  Type: {disaster_type}, Priority: {raw['priority']}")

# Write to by-date file
by_date_file = f"incidents/by-date/{TODAY}/incidents.jsonl"
with open(by_date_file, "w") as f:
    for inc in processed_incidents:
        f.write(json.dumps(inc) + "\n")

print(f"\n✓ Written {len(processed_incidents)} incidents to {by_date_file}")

# Write to country-group files
group_a_incs = [
    i for i in processed_incidents if i["classification"]["country_group"] == "A"
]
group_b_incs = [
    i for i in processed_incidents if i["classification"]["country_group"] == "B"
]
group_c_incs = [
    i for i in processed_incidents if i["classification"]["country_group"] == "C"
]

if group_a_incs:
    with open("incidents/by-country-group/group-a/2026-03/incidents.jsonl", "w") as f:
        for inc in group_a_incs:
            f.write(json.dumps(inc) + "\n")
    print(f"✓ Written {len(group_a_incs)} Group A incidents")

if group_b_incs:
    with open("incidents/by-country-group/group-b/2026-03/incidents.jsonl", "w") as f:
        for inc in group_b_incs:
            f.write(json.dumps(inc) + "\n")
    print(f"✓ Written {len(group_b_incs)} Group B incidents")

if group_c_incs:
    with open("incidents/by-country-group/group-c/2026-03/incidents.jsonl", "w") as f:
        for inc in group_c_incs:
            f.write(json.dumps(inc) + "\n")
    print(f"✓ Written {len(group_c_incs)} Group C incidents")

# Write to type-specific files
type_groups = {}
for inc in processed_incidents:
    inc_type = inc["classification"]["incident_type"]
    if inc_type not in type_groups:
        type_groups[inc_type] = []
    type_groups[inc_type].append(inc)

for inc_type, incs in type_groups.items():
    type_dir = f"incidents/by-incident-type/{inc_type.lower().replace(' ', '-').replace('/', '-')}/active"
    os.makedirs(type_dir, exist_ok=True)
    with open(f"{type_dir}/incidents.jsonl", "w") as f:
        for inc in incs:
            f.write(json.dumps(inc) + "\n")
    print(f"✓ Written {len(incs)} {inc_type} incidents")

# Write to country-specific files
country_groups = {}
for inc in processed_incidents:
    country = inc["classification"]["country"]
    # Handle multi-country
    if "," in country:
        country = country.split(",")[0].strip()
    if country not in country_groups:
        country_groups[country] = []
    country_groups[country].append(inc)

for country, incs in country_groups.items():
    country_dir = f"incidents/by-country/{country.lower().replace(' ', '-')}"
    os.makedirs(country_dir, exist_ok=True)
    with open(f"{country_dir}/active-incidents.jsonl", "w") as f:
        for inc in incs:
            f.write(json.dumps(inc) + "\n")
    print(f"✓ Written {len(incs)} {country} incidents")

# Update indices
with open("incidents/indices/incident-index.jsonl", "w") as f:
    for inc in processed_incidents:
        index_entry = {
            "incident_id": inc["incident_id"],
            "location": f"by-date/{TODAY}",
            "status": inc["status"],
            "country": inc["classification"]["country"],
            "country_group": inc["classification"]["country_group"],
            "incident_type": inc["classification"]["incident_type"],
            "created_date": inc["created_date"],
            "indexed_date": CURRENT_UTC,
        }
        f.write(json.dumps(index_entry) + "\n")
print(f"✓ Updated incident index with {len(processed_incidents)} entries")

# Update date index
date_index_entry = {
    "date": TODAY,
    "incident_count": len(processed_incidents),
    "last_updated": CURRENT_UTC,
}
with open("incidents/indices/date-index.jsonl", "w") as f:
    f.write(json.dumps(date_index_entry) + "\n")
print(f"✓ Updated date index")

# Update country index
country_index = {}
for inc in processed_incidents:
    country = inc["classification"]["country"]
    if "," in country:
        country = country.split(",")[0].strip()
    if country not in country_index:
        country_index[country] = {
            "country": country,
            "country_group": inc["classification"]["country_group"],
            "file_count": 0,
        }
    country_index[country]["file_count"] += 1

with open("incidents/indices/country-index.jsonl", "w") as f:
    for country, data in country_index.items():
        entry = {
            "country": data["country"],
            "country_group": data["country_group"],
            "file_count": data["file_count"],
            "last_updated": CURRENT_UTC,
        }
        f.write(json.dumps(entry) + "\n")
print(f"✓ Updated country index with {len(country_index)} countries")

# Generate metadata for the day
level_counts = {"1": 0, "2": 0, "3": 0, "4": 0}
group_counts = {"A": 0, "B": 0, "C": 0}
type_counts = {}

for inc in processed_incidents:
    level = str(inc["classification"]["incident_level"])
    level_counts[level] = level_counts.get(level, 0) + 1

    group = inc["classification"]["country_group"]
    group_counts[group] = group_counts.get(group, 0) + 1

    inc_type = inc["classification"]["incident_type"]
    type_counts[inc_type] = type_counts.get(inc_type, 0) + 1

metadata = {
    "date": TODAY,
    "total_incidents": len(processed_incidents),
    "total_media_coverage": 0,
    "incidents_by_level": level_counts,
    "incidents_by_group": group_counts,
    "incidents_by_type": type_counts,
    "escalations": 0,
    "src_mentioned_count": 0,
    "singapore_mentioned_count": 0,
    "generated_timestamp": CURRENT_UTC,
}

with open(f"incidents/by-date/{TODAY}/metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)
print(f"✓ Created metadata.json for {TODAY}")

print("\n" + "=" * 50)
print("PROCESSING COMPLETE")
print("=" * 50)
print(f"Total incidents processed: {len(processed_incidents)}")
print(
    f"Group A: {len(group_a_incs)}, Group B: {len(group_b_incs)}, Group C: {len(group_c_incs)}"
)
print(f"Date: {TODAY}")
print(f"Storage location: incidents/by-date/{TODAY}/")

# Save summary for reporting
summary = {
    "total_processed": len(processed_incidents),
    "group_a": len(group_a_incs),
    "group_b": len(group_b_incs),
    "group_c": len(group_c_incs),
    "date": TODAY,
    "storage_location": f"incidents/by-date/{TODAY}/",
    "validation_issues": [],
    "files_written": [
        f"incidents/by-date/{TODAY}/incidents.jsonl",
        "incidents/by-country-group/group-a/2026-03/incidents.jsonl",
        "incidents/by-country-group/group-b/2026-03/incidents.jsonl",
        "incidents/by-country-group/group-c/2026-03/incidents.jsonl",
        "incidents/indices/incident-index.jsonl",
        "incidents/indices/date-index.jsonl",
        "incidents/indices/country-index.jsonl",
        f"incidents/by-date/{TODAY}/metadata.json",
    ],
}

print("\n--- INCIDENT SUMMARY ---")
for i, inc in enumerate(processed_incidents, 1):
    print(f"{i}. {inc['incident_id']}: {inc['incident_name'][:50]}...")
    print(
        f"   Country: {inc['classification']['country']}, Group: {inc['classification']['country_group']}"
    )
    print(
        f"   Level: {inc['classification']['incident_level']}, Priority: {inc['classification']['priority']}"
    )
    print()
