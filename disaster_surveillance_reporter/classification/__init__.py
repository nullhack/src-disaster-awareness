"""Classification rules for incident prioritization.

This module provides the rules loader for categorizing incidents by country groups,
priority levels, and reporting criteria.
"""

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


class RulesLoader:
    """Classification rules loader."""

    def __init__(
        self, country_groups: dict | None = None, priority_matrix: dict | None = None
    ):
        self._country_groups = country_groups or COUNTRY_GROUPS
        self._priority_matrix = priority_matrix or PRIORITY_MATRIX

    def get_country_group(self, country: str) -> str:
        """Get country group (A, B, or C) for a country."""
        for group, countries in self._country_groups.items():
            if country in countries:
                return group
        return "C"

    def get_priority(self, level: int, group: str) -> str:
        """Get priority (HIGH, MEDIUM, LOW) for level and group."""
        key = (level, group)
        return self._priority_matrix.get(key, ("LOW", False))[0]

    def should_report(self, level: int, group: str) -> bool:
        """Determine if incident should be reported."""
        key = (level, group)
        return self._priority_matrix.get(key, ("LOW", False))[1]
