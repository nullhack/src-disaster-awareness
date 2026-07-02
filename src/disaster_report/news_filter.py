from __future__ import annotations

import re
import unicodedata

import pycountry

from disaster_report.classification import is_disease_type
from disaster_report.countries import UNKNOWN_ISO2, country_iso2, is_known_country
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

# Synonyms per disaster type. For the disease track the bare tokens "virus" and
# "fever" are intentionally omitted: they are single-token false-positive magnets
# ("computer virus", "USB virus", election/sports "fever"). A specific disease
# name (passed via ``disease``) or >=2 overlapping disease tokens still match.
_TYPE_SYNONYMS = {
    "earthquake": "earthquake quake tremor seismic temblor",
    "disease": (
        "disease outbreak epidemic pandemic infection measles ebola "
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

# Collocations that signal a non-event even when a disease name appears: virus
# metaphors, eradication milestones, or receding case counts. The AI judge is
# the final arbiter; this cheap pre-filter just avoids fetching/storing these.
_JUNK_PHRASES: tuple[str, ...] = (
    "computer virus",
    "polio-free",
    "polio free",
    "disease-free",
    "disease free",
    "declared free",
    "declared end",
    "elimination declared",
    "cases fall",
    "cases fell",
    "case counts fall",
    "cases dropping",
    "receding",
)

_WORD = re.compile(r"[A-Za-z]{3,}")


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP}


def _type_tokens(incident_type: str, disease_name: str | None = None) -> set[str]:
    key = (incident_type or "").lower().strip()
    base = _TYPE_SYNONYMS.get(key, incident_type or "")
    return _tokens(f"{base} {disease_name or ''}")


# Country name + first-level subdivision (state/province) name tokens, cached
# per country. Local news of federal countries names the state rather than the
# country (e.g. "Kerala" for India, "California" for the US), so tokenizing only
# the country name drops otherwise-relevant articles on the disease track.
_SUBDIVISION_CACHE: dict[str, frozenset[str]] = {}


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _country_place_tokens(country: str) -> set[str]:
    if not is_known_country(country):
        return set()
    key = country.strip().lower()
    cached = _SUBDIVISION_CACHE.get(key)
    if cached is None:
        tokens = _tokens(country)
        iso = country_iso2(country)
        if iso and iso != UNKNOWN_ISO2:
            try:
                subs = pycountry.subdivisions.get(country_code=iso)
            except KeyError:
                subs = None
            if subs:
                for sub in subs:
                    tokens |= _tokens(_ascii(sub.name))
        cached = frozenset(tokens)
        _SUBDIVISION_CACHE[key] = cached
    return set(cached)


def _is_junk(article: RawArticle) -> bool:
    text = f"{article.headline} {article.body}".lower()
    return any(phrase in text for phrase in _JUNK_PHRASES)


def _place_tokens(country: str, is_disease_track: bool, incident_name: str, type_t: set[str]) -> set[str]:
    if not is_known_country(country):
        return set()
    if is_disease_track:
        # Disease incidents: canonical_name only repeats the country plus a
        # month/year (date noise), so place_t comes from the country and its
        # subdivisions (states). Local news names the state, not the country.
        return _country_place_tokens(country)
    return _tokens(f"{country} {incident_name}") - type_t


def _type_match(art_t: set[str], type_t: set[str], is_disease_track: bool, disease_name: str | None) -> bool:
    if not type_t:
        return True
    overlap = art_t & type_t
    if not is_disease_track:
        return bool(overlap)
    # Disease track: a specific disease-name hit always qualifies; otherwise
    # require >=2 distinct type tokens to avoid single-word false positives
    # ("fever", "virus", "poisoning").
    disease_t = _tokens(disease_name or "")
    disease_hit = bool(disease_t) and bool(art_t & disease_t)
    return disease_hit or len(overlap) >= 2


def is_relevant(
    article: RawArticle,
    *,
    incident_type: str,
    country: str,
    incident_name: str,
    disease_name: str | None = None,
) -> bool:
    is_disease_track = is_disease_type(incident_type)
    type_t = _type_tokens(incident_type, disease_name)
    art_t = _tokens(f"{article.headline} {article.body}")
    place_t = _place_tokens(country, is_disease_track, incident_name, type_t)
    place_match = bool(art_t & place_t) if place_t else True

    if not _type_match(art_t, type_t, is_disease_track, disease_name) or not place_match:
        return False
    # The junk stoplist is disease-context only (e.g. "floodwaters receding" is a
    # legitimate physical-disaster follow-up, not noise).
    if is_disease_track and _is_junk(article):
        return False
    return True
