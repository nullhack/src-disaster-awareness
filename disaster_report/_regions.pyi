_SUBREGION_COUNTRIES: dict[str, tuple[str, ...]]
_SUBREGIONS_BY_ALPHA_2: dict[str, str]

def subregion_for_country(alpha_2: str) -> str: ...
