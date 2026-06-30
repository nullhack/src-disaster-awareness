from __future__ import annotations

import re

from disaster_report.sources.base import RawArticle

_STOP = frozenset(
    (
        "the of off a an is are was were to in on at for and or by with from "
        "this that these those it its as be been being have has had do does did "
        "not no but if then than which who whom whose what when where why how "
        "into over under between among about against through during before after "
        "above below up down out near miles km magnitude"
    ).split()
)

_TYPE_SYNONYMS = {
    "earthquake": "earthquake quake tremor seismic temblor",
    "disease": (
        "disease outbreak epidemic pandemic virus infection fever measles ebola "
        "dengue malaria cholera poisoning hepatitis flu influenza covid "
        "coronavirus marburg smallpox anthrax rabies tetanus typhoid"
    ),
    "flood": "flood flooding inundation deluge",
    "storm": "storm cyclone typhoon hurricane tempest tornado",
    "wildfire": "wildfire fire blaze bushfire forest",
    "volcano": "volcano volcanic eruption lava ash",
    "landslide": "landslide mudslide avalanche rockslide",
    "tsunami": "tsunami tidal",
    "drought": "drought",
}

_WORD = re.compile(r"[A-Za-z]{3,}")


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP}


def _type_tokens(disaster_type: str, disease: str | None = None) -> set[str]:
    key = (disaster_type or "").lower().strip()
    base = _TYPE_SYNONYMS.get(key, disaster_type or "")
    return _tokens(f"{base} {disease or ''}")


def is_relevant(
    article: RawArticle,
    *,
    disaster_type: str,
    country: str,
    incident_name: str,
    disease: str | None = None,
) -> bool:
    type_t = _type_tokens(disaster_type, disease)
    place_t = _tokens(f"{country} {incident_name}") - type_t
    art_t = _tokens(f"{article.headline} {article.body}")
    type_match = bool(art_t & type_t) if type_t else True
    place_match = bool(art_t & place_t) if place_t else True
    return type_match and place_match
