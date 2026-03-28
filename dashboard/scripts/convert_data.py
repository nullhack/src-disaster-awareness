#!/usr/bin/env python3
"""Convert JSONL incident data to dashboard JSON format."""

import json
from pathlib import Path

INCIDENTS_DIR = Path(__file__).parent.parent / "incidents"
OUTPUT_DIR = Path(__file__).parent.parent / "data"


def normalize_incident(record: dict) -> dict:
    """Normalize incident data to dashboard format."""

    # Extract location coordinates
    loc = record.get("location", {})
    coords = loc.get("coordinates", {})

    # Normalize impact fields
    impact = record.get("impact", {})

    # Normalize sources
    sources = []
    for src in record.get("sources", []):
        sources.append({"name": src.get("name", "Unknown"), "url": src.get("url", "")})

    # Determine incident type for display
    incident_type = record.get("incident_type", "Unknown")
    disaster_details = record.get("disaster_details", {})
    disease_details = record.get("disease_details", {})

    # Map to simpler types (check partial matches)
    type_mapping = {
        "Cyclone": "Cyclone",
        "Tropical Cyclone": "Cyclone",
        "Typhoon": "Cyclone",
        "Hurricane": "Cyclone",
        "Earthquake": "Earthquake",
        "Flood": "Flood",
        "Flash Flood": "Flood",
        "Wildfire": "Fire",
        "Forest Fire": "Fire",
        "Fire": "Fire",
        "Volcanic": "Fire",
        "Volcano": "Fire",
        "Drought": "Drought",
        "Landslide": "Landslide",
        "Disease": "Disease",
        "Outbreak": "Disease",
        "Epidemic": "Disease",
        "Virus": "Disease",
    }

    display_type = None
    for key, value in type_mapping.items():
        if key.lower() in incident_type.lower():
            display_type = value
            break

    if not display_type:
        display_type = incident_type

    # Check for disease
    if disease_details or "disease" in incident_type.lower():
        disease_type = disease_details.get(
            "disease_type", disease_details.get("disease", "Unknown")
        )
    else:
        disease_type = None

    # Get priority level
    level = record.get("incident_level", 1)

    # Get country
    country = record.get("country", "Unknown")
    provinces = loc.get("provinces", [])
    province = provinces[0].get("name", "") if provinces else ""

    return {
        "incident_id": record.get("incident_id", ""),
        "incident_name": record.get("incident_name", "Unnamed Incident"),
        "country": country,
        "country_group": record.get("country_group", "C"),
        "incident_type": display_type,
        "disease_type": disease_type,
        "incident_level": level,
        "priority": record.get("priority", "LOW"),
        "status": record.get("status", "Active"),
        "created_date": record.get("created_date", ""),
        "updated_date": record.get("updated_date", ""),
        "location": {
            "country": country,
            "province": province,
            "districts": [p.get("name", "") for p in provinces if p.get("affected")],
            "coordinates": {
                "lat": coords.get("latitude", 0) or coords.get("lat", 0) or 0,
                "lon": coords.get("longitude", 0) or coords.get("lon", 0) or 0,
            },
        },
        "impact": {
            "deaths": impact.get("deaths", 0),
            "missing": impact.get("missing", 0),
            "injured": impact.get("injuries", 0),
            "affected": impact.get("affected_population", 0),
            "displaced": impact.get("displaced_persons", 0),
        },
        "sources": sources,
        "description": impact.get("impact_description", "")
        or disaster_details.get("description", ""),
    }


def convert_incidents():
    """Convert all incidents to dashboard format."""
    incidents = []
    diseases = []

    # Find all JSONL files
    for date_dir in sorted(INCIDENTS_DIR.glob("by-date/*/")):
        incidents_file = date_dir / "incidents.jsonl"

        if incidents_file.exists():
            print(f"Reading: {incidents_file}")
            with open(incidents_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            record = json.loads(line)
                            normalized = normalize_incident(record)

                            # Separate diseases from natural disasters
                            if normalized["incident_type"] == "Disease":
                                diseases.append(normalized)
                            else:
                                incidents.append(normalized)
                        except json.JSONDecodeError as e:
                            print(f"Error: {e}")
                            continue

    # Sort by date (newest first)
    incidents.sort(key=lambda x: x.get("updated_date", ""), reverse=True)
    diseases.sort(key=lambda x: x.get("updated_date", ""), reverse=True)

    # Write to dashboard data directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR / "incidents.json", "w") as f:
        json.dump(incidents, f, indent=2)

    with open(OUTPUT_DIR / "disease-incidents.json", "w") as f:
        json.dump(diseases, f, indent=2)

    print(
        f"\nConverted {len(incidents)} incidents and {len(diseases)} disease outbreaks"
    )
    print(f"Output: {OUTPUT_DIR}")

    # Also copy to static
    static_dir = OUTPUT_DIR.parent / "static" / "data"
    static_dir.mkdir(parents=True, exist_ok=True)

    import shutil

    shutil.copy(OUTPUT_DIR / "incidents.json", static_dir / "incidents.json")
    shutil.copy(
        OUTPUT_DIR / "disease-incidents.json", static_dir / "disease-incidents.json"
    )

    print(f"Also copied to: {static_dir}")


if __name__ == "__main__":
    convert_incidents()
