"""Test fixtures for Disaster Surveillance Reporter."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RawIncidentData:
    """Test fixture for raw incident data from source adapters."""

    source_name: str
    incident_name: str
    country: str
    disaster_type: str
    report_date: str
    source_url: str
    raw_fields: dict[str, Any]


RAW_INCIDENT_TC = RawIncidentData(
    source_name="GDACS",
    incident_name="Tropical Cyclone NURI-26",
    country="Pacific Ocean",
    disaster_type="Tropical Cyclone",
    report_date="2026-03-12T00:00:00Z",
    source_url="https://www.gdacs.org/report.aspx?eventid=1001263&episodeid=5&eventtype=TC",
    raw_fields={"wind_speed": 56, "pressure": 1000},
)

RAW_INCIDENT_EQ = RawIncidentData(
    source_name="GDACS",
    incident_name="Earthquake in Sumatra, Indonesia",
    country="Indonesia",
    disaster_type="Earthquake",
    report_date="2026-03-11T10:15:00Z",
    source_url="https://www.gdacs.org/earthquake/12345",
    raw_fields={"magnitude": 6.1, "depth": 25},
)

RAW_INCIDENT_FLOOD = RawIncidentData(
    source_name="GDACS",
    incident_name="Flood in Aceh, Indonesia",
    country="Indonesia",
    disaster_type="Flood",
    report_date="2026-03-10T08:00:00Z",
    source_url="https://www.gdacs.org/flood/12346",
    raw_fields={"affected_population": 75000, "deaths": 12},
)


RAW_INCIDENTS = [RAW_INCIDENT_TC, RAW_INCIDENT_EQ, RAW_INCIDENT_FLOOD]


INCIDENT_JSON = {
    "incident_id": "20260312-PO-TC",
    "incident_name": "Tropical Cyclone NURI-26",
    "created_date": "2026-03-12T00:00:00Z",
    "updated_date": "2026-03-12T00:00:00Z",
    "status": "Active",
    "country": "Pacific Ocean",
    "country_group": "B",
    "incident_type": "Tropical Cyclone",
    "incident_level": 2,
    "priority": "MEDIUM",
    "should_report": True,
    "tags": [],
    "location": {
        "country": "Pacific Ocean",
        "provinces": [{"name": "Pacific Ocean", "affected": True}],
        "coordinates": {"latitude": 0.0, "longitude": -160.0},
        "affected_area_description": "Pacific Ocean",
    },
    "impact": {
        "affected_population": 0,
        "deaths": 0,
        "injuries": 0,
        "displaced_persons": 0,
        "affected_provinces": 1,
        "impact_description": "Tropical Cyclone NURI-26 active in Pacific Ocean",
    },
    "sources": [
        {
            "name": "GDACS",
            "type": "disaster-database",
            "url": "https://www.gdacs.org/report.aspx?eventid=1001263&episodeid=5&eventtype=TC",
            "accessed_date": "2026-03-12T00:00:00Z",
            "reliability_tier": "Tier1",
            "data_freshness": "real-time",
        }
    ],
    "disaster_details": {
        "disaster_type": "Tropical Cyclone",
        "magnitude_or_scale": 56,
        "depth_or_altitude": 0,
        "forecasted": False,
        "first_reported": "2026-03-12T00:00:00Z",
        "latest_update": "2026-03-12T00:00:00Z",
    },
    "disease_details": None,
    "media_coverage": {
        "singapore_mentioned": False,
        "src_mentioned": False,
        "donation_concerns": False,
        "misinformation_detected": False,
        "public_sentiment": "neutral",
        "coverage_articles": [],
    },
    "classification_metadata": {
        "classified_by": "opencode-minimax",
        "classified_date": "2026-03-12T00:00:00Z",
        "classification_confidence": 0.95,
        "rationale": "Active tropical cyclone in Group B country",
        "special_flags": [],
    },
    "src_involvement": {
        "involved": False,
        "involvement_type": "None",
        "donation_appeal_active": False,
        "volunteer_deployment": False,
        "estimated_response_value": 0,
        "response_notes": "",
    },
    "escalation_tracking": {
        "initial_level": 2,
        "current_level": 2,
        "escalation_potential": False,
        "level_change_history": [],
    },
    "metadata": {
        "data_quality": "High",
        "completeness_score": 0.90,
        "last_verified": "2026-03-12T00:00:00Z",
        "related_incidents": [],
        "notes": "",
    },
}

INCIDENT_JSON_LIST = [
    INCIDENT_JSON,
    {
        "incident_id": "20260311-ID-EQ",
        "incident_name": "Earthquake in Sumatra, Indonesia",
        "created_date": "2026-03-11T10:15:00Z",
        "updated_date": "2026-03-11T10:15:00Z",
        "status": "Active",
        "country": "Indonesia",
        "country_group": "A",
        "incident_type": "Earthquake",
        "incident_level": 2,
        "priority": "MEDIUM",
        "should_report": True,
        "tags": ["escalation-risk"],
        "location": {
            "country": "Indonesia",
            "provinces": [{"name": "Sumatra", "affected": True}],
            "coordinates": {"latitude": -0.89, "longitude": 100.74},
            "affected_area_description": "Sumatra region",
        },
        "impact": {
            "affected_population": 75000,
            "deaths": 12,
            "injuries": 45,
            "displaced_persons": 5000,
            "affected_provinces": 1,
            "impact_description": "Moderate earthquake",
        },
        "sources": [
            {
                "name": "GDACS",
                "type": "disaster-database",
                "url": "https://www.gdacs.org/earthquake/12345",
                "accessed_date": "2026-03-11T10:20:00Z",
                "reliability_tier": "Tier1",
                "data_freshness": "real-time",
            }
        ],
        "disaster_details": {
            "disaster_type": "Tectonic Earthquake",
            "magnitude_or_scale": 6.1,
            "depth_or_altitude": 25,
            "forecasted": False,
            "first_reported": "2026-03-11T09:45:00Z",
            "latest_update": "2026-03-11T10:15:00Z",
        },
        "disease_details": None,
        "media_coverage": {
            "singapore_mentioned": False,
            "src_mentioned": False,
            "donation_concerns": False,
            "misinformation_detected": False,
            "public_sentiment": "neutral",
            "coverage_articles": [],
        },
        "classification_metadata": {
            "classified_by": "opencode-minimax",
            "classified_date": "2026-03-11T10:15:00Z",
            "classification_confidence": 0.90,
            "rationale": "Level 2 earthquake in Group A country",
            "special_flags": ["escalation-risk"],
        },
        "src_involvement": {
            "involved": False,
            "involvement_type": "None",
            "donation_appeal_active": False,
            "volunteer_deployment": False,
            "estimated_response_value": 0,
            "response_notes": "",
        },
        "escalation_tracking": {
            "initial_level": 2,
            "current_level": 2,
            "escalation_potential": True,
            "level_change_history": [],
        },
        "metadata": {
            "data_quality": "High",
            "completeness_score": 0.92,
            "last_verified": "2026-03-11T10:15:00Z",
            "related_incidents": [],
            "notes": "Monitor for aftershocks",
        },
    },
]


COUNTRY_GROUPS = {
    "A": {
        "Afghanistan",
        "Bangladesh",
        "Bhutan",
        "Brunei",
        "Cambodia",
        "China",
        "India",
        "Indonesia",
        "Japan",
        "Laos",
        "Malaysia",
        "Maldives",
        "Myanmar",
        "Nepal",
        "North Korea",
        "Pakistan",
        "Philippines",
        "Singapore",
        "South Korea",
        "Sri Lanka",
        "Taiwan",
        "Thailand",
        "Timor Leste",
        "Vietnam",
    },
    "B": {
        "Australia",
        "Fiji",
        "French Polynesia",
        "Guam",
        "Kazakhstan",
        "Kiribati",
        "Kyrgyzstan",
        "Mariana Islands",
        "Marshall Islands",
        "Micronesia",
        "Mongolia",
        "Nauru",
        "New Caledonia",
        "New Zealand",
        "Niue",
        "Palau",
        "Papua New Guinea",
        "Samoa",
        "Solomon Islands",
        "Tajikistan",
        "Tonga",
        "Turkmenistan",
        "Tuvalu",
        "Uzbekistan",
        "Vanuatu",
        "Wallis and Futuna",
        "Bahrain",
        "Cyprus",
        "Iran",
        "Iraq",
        "Jordan",
        "Kuwait",
        "Lebanon",
        "Oman",
        "Palestine",
        "Israel",
        "Qatar",
        "Saudi Arabia",
        "Syria",
        "Turkey",
        "UAE",
        "Yemen",
        "Algeria",
        "Egypt",
        "Morocco",
        "Tunisia",
    },
    "C": set(),
}


PRIORITY_MATRIX = {
    (4, "A"): ("HIGH", True),
    (4, "B"): ("HIGH", True),
    (4, "C"): ("HIGH", True),
    (3, "A"): ("HIGH", True),
    (3, "B"): ("MEDIUM", True),
    (3, "C"): ("MEDIUM", True),
    (2, "A"): ("MEDIUM", True),
    (2, "B"): ("MEDIUM", True),
    (2, "C"): ("LOW", False),
    (1, "A"): ("MEDIUM", True),
    (1, "B"): ("LOW", False),
    (1, "C"): ("LOW", False),
}


OPENCODE_TRANSFORM_PROMPT = """Given this raw incident data:
- Source: {source_name}
- Name: {incident_name}
- Country: {country}
- Type: {disaster_type}
- Date: {report_date}

Transform to schema-compliant JSON with classification."""

OPENCODE_CLASSIFY_PROMPT = """Given this incident:
- Country: {country}
- Country Group: {country_group}
- Incident Type: {incident_type}
- Impact: {impact_description}

And classification rules:
- Level {level} ({level_description})
- Priority: {priority}

Classify and return the complete JSON."""
