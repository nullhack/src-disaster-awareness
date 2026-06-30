from __future__ import annotations

from disaster_report.countries import country_iso2

COUNTRY_GROUPS: dict[str, frozenset[str]] = {
    "A": frozenset(
        {
            "AF", "BD", "BT", "BN", "KH", "CN", "IN", "ID", "JP", "LA",
            "MY", "MV", "MM", "NP", "KP", "PK", "PH", "SG", "KR", "LK",
            "TW", "TH", "TL", "VN",
        }
    ),
    "B": frozenset(
        {
            "AU", "FJ", "PF", "GU", "KZ", "KI", "KG", "MP", "MH", "FM",
            "MN", "NR", "NC", "NZ", "NU", "PW", "PG", "WS", "SB", "TJ",
            "TO", "TM", "TV", "UZ", "VU", "WF", "BH", "CY", "IR", "IQ",
            "JO", "KW", "LB", "OM", "PS", "IL", "QA", "SA", "SY", "TR",
            "AE", "YE", "DZ", "EG", "MA", "TN",
        }
    ),
    "C": frozenset(),
}

PRIORITY_MATRIX: dict[tuple[int, str], tuple[str, bool]] = {
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


def country_group(country_name_or_iso2: str) -> str:
    iso2 = country_iso2(country_name_or_iso2)
    for group, members in COUNTRY_GROUPS.items():
        if iso2 in members:
            return group
    return "C"


def classify(level: int, country_name_or_iso2: str) -> tuple[str, bool]:
    group = country_group(country_name_or_iso2)
    return PRIORITY_MATRIX.get((level, group), ("LOW", False))
