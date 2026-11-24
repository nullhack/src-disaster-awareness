
from __future__ import annotations

_SUBREGION_COUNTRIES: dict[str, tuple[str, ...]] = {
    "Eastern Africa": (
        "BI",
        "KM",
        "DJ",
        "ER",
        "ET",
        "KE",
        "MG",
        "MW",
        "MU",
        "MZ",
        "RE",
        "RW",
        "SC",
        "SO",
        "SS",
        "TZ",
        "UG",
        "YT",
        "ZM",
        "ZW",
    ),
    "Middle Africa": (
        "AO",
        "CD",
        "CF",
        "CG",
        "CM",
        "GA",
        "GQ",
        "ST",
        "TD",
    ),
    "Northern Africa": (
        "DZ",
        "EG",
        "EH",
        "LY",
        "MA",
        "SD",
        "TN",
    ),
    "Southern Africa": (
        "BW",
        "LS",
        "NA",
        "SZ",
        "ZA",
    ),
    "Western Africa": (
        "BF",
        "BJ",
        "CI",
        "CV",
        "GH",
        "GM",
        "GN",
        "GW",
        "LR",
        "ML",
        "MR",
        "NE",
        "NG",
        "SH",
        "SL",
        "SN",
        "TG",
    ),
    "Caribbean": (
        "AG",
        "AI",
        "AW",
        "BB",
        "BL",
        "BQ",
        "BS",
        "CU",
        "CW",
        "DM",
        "DO",
        "GD",
        "GP",
        "HT",
        "JM",
        "KN",
        "KY",
        "LC",
        "MF",
        "MQ",
        "MS",
        "PR",
        "SX",
        "TC",
        "TT",
        "VC",
        "VG",
        "VI",
    ),
    "Central America": (
        "BZ",
        "CR",
        "GT",
        "HN",
        "MX",
        "NI",
        "PA",
        "SV",
    ),
    "Northern America": (
        "BM",
        "CA",
        "GL",
        "PM",
        "US",
    ),
    "South America": (
        "AR",
        "BO",
        "BR",
        "CL",
        "CO",
        "EC",
        "FK",
        "GF",
        "GY",
        "PE",
        "PY",
        "SR",
        "UY",
        "VE",
    ),
    "Central Asia": (
        "KG",
        "KZ",
        "TJ",
        "TM",
        "UZ",
    ),
    "Eastern Asia": (
        "CN",
        "HK",
        "JP",
        "KP",
        "KR",
        "MO",
        "MN",
        "TW",
    ),
    "South-Eastern Asia": (
        "BN",
        "ID",
        "KH",
        "LA",
        "MM",
        "MY",
        "PH",
        "SG",
        "TH",
        "TL",
        "VN",
    ),
    "Southern Asia": (
        "AF",
        "BD",
        "BT",
        "IN",
        "IR",
        "LK",
        "MV",
        "NP",
        "PK",
    ),
    "Western Asia": (
        "AE",
        "AM",
        "AZ",
        "BH",
        "CY",
        "GE",
        "IL",
        "IQ",
        "JO",
        "KW",
        "LB",
        "OM",
        "PS",
        "QA",
        "SA",
        "SY",
        "TR",
        "YE",
    ),
    "Eastern Europe": (
        "BG",
        "BY",
        "CZ",
        "HU",
        "MD",
        "PL",
        "RO",
        "RU",
        "SK",
        "UA",
    ),
    "Northern Europe": (
        "AX",
        "DK",
        "EE",
        "FI",
        "FO",
        "GB",
        "GG",
        "IE",
        "IM",
        "IS",
        "JE",
        "LV",
        "LT",
        "NO",
        "SJ",
        "SE",
    ),
    "Southern Europe": (
        "AD",
        "AL",
        "BA",
        "ES",
        "GI",
        "GR",
        "HR",
        "IT",
        "ME",
        "MK",
        "MT",
        "PT",
        "RS",
        "SM",
        "SI",
        "VA",
    ),
    "Western Europe": (
        "AT",
        "BE",
        "CH",
        "DE",
        "FR",
        "LI",
        "LU",
        "MC",
        "NL",
    ),
    "Australia and New Zealand": (
        "AU",
        "NF",
        "NZ",
    ),
    "Melanesia": (
        "FJ",
        "NC",
        "PG",
        "SB",
        "VU",
    ),
    "Micronesia": (
        "FM",
        "GU",
        "KI",
        "MH",
        "MP",
        "NR",
        "PW",
    ),
    "Polynesia": (
        "AS",
        "CK",
        "NU",
        "PF",
        "PN",
        "TK",
        "TO",
        "TV",
        "WF",
        "WS",
    ),
}

_SUBREGIONS_BY_ALPHA_2: dict[str, str] = {
    code: subregion
    for subregion, codes in _SUBREGION_COUNTRIES.items()
    for code in codes
}


_SUBREGION_CODES: dict[str, str] = {
    "Eastern Africa": "014",
    "Middle Africa": "017",
    "Northern Africa": "015",
    "Southern Africa": "018",
    "Western Africa": "011",
    "Caribbean": "029",
    "Central America": "013",
    "Northern America": "021",
    "South America": "005",
    "Central Asia": "143",
    "Eastern Asia": "030",
    "South-Eastern Asia": "035",
    "Southern Asia": "034",
    "Western Asia": "145",
    "Eastern Europe": "151",
    "Northern Europe": "154",
    "Southern Europe": "039",
    "Western Europe": "155",
    "Australia and New Zealand": "053",
    "Melanesia": "054",
    "Micronesia": "057",
    "Polynesia": "061",
}

_SUBREGION_ALIASES: dict[str, str] = {
    "south east asia": "South-Eastern Asia",
    "southeast asia": "South-Eastern Asia",
    "south eastern asia": "South-Eastern Asia",
    "south-eastern asia": "South-Eastern Asia",
    "east asia": "Eastern Asia",
    "south asia": "Southern Asia",
    "west asia": "Western Asia",
    "central asia": "Central Asia",
    "north africa": "Northern Africa",
    "east africa": "Eastern Africa",
    "south africa": "Southern Africa",
    "west africa": "Western Africa",
    "central africa": "Middle Africa",
    "north america": "Northern America",
    "central america": "Central America",
    "south america": "South America",
    "australia and new zealand": "Australia and New Zealand",
}


def region_code_for_name(name: str) -> str:
    normalized = _normalize_region_name(name)
    return _SUBREGION_CODES.get(normalized, "")


def region_name_for_code(code: str) -> str:
    for name, region_code in _SUBREGION_CODES.items():
        if region_code == code:
            return name
    return ""


def normalize_region_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        return ""
    lowered = cleaned.lower().replace("_", " ").replace("-", " ").strip()
    direct = {key.lower(): key for key in _SUBREGION_CODES}
    if lowered in direct:
        return direct[lowered]
    return _SUBREGION_ALIASES.get(lowered, cleaned)


def region_name_from_text(text: str) -> str:
    lowered = (text or "").lower().replace("_", " ").replace("-", " ")
    for alias, name in _SUBREGION_ALIASES.items():
        if alias in lowered:
            return name
    for name in _SUBREGION_CODES:
        if name.lower().replace("-", " ") in lowered:
            return name
    return ""


def _normalize_region_name(name: str) -> str:
    return normalize_region_name(name)


def subregion_for_country(alpha_2: str) -> str:
    if not alpha_2:
        return ""
    return _SUBREGIONS_BY_ALPHA_2.get(alpha_2.upper(), "")
