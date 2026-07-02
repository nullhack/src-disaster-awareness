from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import TYPE_CHECKING, Callable

from disaster_report.countries import country_iso2

if TYPE_CHECKING:
    from disaster_report.sources.base import RawIncident

# --------------------------------------------------------------------------- #
# Country grouping
#
# Single source of truth for `dim_country.country_group` lives in the database;
# this helper is retained only to *seed* that dimension (store._seed_dimensions
# / _country_key). Classification no longer calls it — callers resolve the
# group from dim_country and pass it via ClassifyContext.
# --------------------------------------------------------------------------- #


class CountryGroup(str, Enum):
    """Reporting tier. Members ARE their string values (``"A"``/``"B"``/``"C"``),
    so they interop with existing string literals and DB columns without any
    conversion (``CountryGroup.A == "A"``)."""

    A = "A"
    B = "B"
    C = "C"


COUNTRY_GROUPS: dict[CountryGroup, frozenset[str]] = {
    CountryGroup.A: frozenset(
        {
            "AF", "BD", "BT", "BN", "KH", "CN", "IN", "ID", "JP", "LA",
            "MY", "MV", "MM", "NP", "KP", "PK", "PH", "SG", "KR", "LK",
            "TW", "TH", "TL", "VN",
        }
    ),
    CountryGroup.B: frozenset(
        {
            "AU", "FJ", "PF", "GU", "KZ", "KI", "KG", "MP", "MH", "FM",
            "MN", "NR", "NC", "NZ", "NU", "PW", "PG", "WS", "SB", "TJ",
            "TO", "TM", "TV", "UZ", "VU", "WF", "BH", "CY", "IR", "IQ",
            "JO", "KW", "LB", "OM", "PS", "IL", "QA", "SA", "SY", "TR",
            "AE", "YE", "DZ", "EG", "MA", "TN",
        }
    ),
    CountryGroup.C: frozenset(),
}


def country_group(country_name_or_iso2: str) -> CountryGroup:
    iso2 = country_iso2(country_name_or_iso2)
    for group, members in COUNTRY_GROUPS.items():
        if iso2 in members:
            return group
    return CountryGroup.C


# --------------------------------------------------------------------------- #
# Severity / priority model
# --------------------------------------------------------------------------- #


class Severity(IntEnum):
    """Incident severity. Members ARE their int values, so DB ``severity_level``
    columns (ints) interop directly: ``Severity.HIGH == 3``."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# Backwards-compatible int aliases. ``Severity.LOW`` is already ``1``; these
# keep the historical ``SEVERITY_*`` import names working across the codebase
# and the test suite.
SEVERITY_LOW = Severity.LOW
SEVERITY_MEDIUM = Severity.MEDIUM
SEVERITY_HIGH = Severity.HIGH
SEVERITY_CRITICAL = Severity.CRITICAL

# Level -> name and name -> level, derived from the enum (single source of
# truth). The store and report modules import these instead of re-deriving.
SEVERITY_NAMES: dict[int, str] = {level: level.name for level in Severity}
SEVERITY_LEVELS: dict[str, int] = {level.name: level for level in Severity}


class Pandemic(IntEnum):
    """Pandemic-potential scale. ``NONE`` means "not applicable" (physical
    incident) or "not yet digested" (disease incident pre-first-AI-pass)."""

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


PANDEMIC_NONE = Pandemic.NONE
PANDEMIC_LOW = Pandemic.LOW
PANDEMIC_MEDIUM = Pandemic.MEDIUM
PANDEMIC_HIGH = Pandemic.HIGH
PANDEMIC_CRITICAL = Pandemic.CRITICAL

PANDEMIC_NAME_TO_LEVEL: dict[str, int] = {p.name: p for p in Pandemic}
PANDEMIC_LEVEL_TO_NAME: dict[int, str] = {p: p.name for p in Pandemic}


def pandemic_potential_level(name: str | None) -> int | None:
    """Map an AI-returned pandemic-potential label to its scale int.

    Returns ``None`` for an empty/unknown label so callers can distinguish
    "not yet digested" (``None``) from an explicit AI ``NONE`` (``0``).
    """
    key = (name or "").strip().upper()
    return PANDEMIC_NAME_TO_LEVEL.get(key)


# Incident types that route to the disease prompt track and the disease
# classification logic. Single source of truth — deriver, news_filter, and
# ai.openrouter import this constant instead of re-declaring it.
DISEASE_TYPES: frozenset[str] = frozenset(
    {"disease", "epidemic", "outbreak", "epidemics"}
)


def is_disease_type(incident_type: str) -> bool:
    """True when an incident type routes through the disease track."""
    return (incident_type or "").strip().lower() in DISEASE_TYPES


# AI event-status values that suppress reporting (disease incidents only).
NON_EVENT_STATUSES: frozenset[str] = frozenset(
    {"non_event", "elimination_declared"}
)


class Priority(IntEnum):
    """Reporting priority. ``HIGH`` is most urgent (rank 1). Members ARE ints."""

    HIGH = 1
    MEDIUM = 2
    LOW = 3


PRIORITY_RANK: dict[str, int] = {p.name: p for p in Priority}

# Baseline reporting matrix: (severity_level, country_group) -> (priority, should_report).
# Keys use enum members; because Severity/CountryGroup interop with int/str,
# lookups with raw ``(4, "C")`` tuples resolve correctly too.
PRIORITY_MATRIX: dict[tuple[int, str], tuple[str, bool]] = {
    (Severity.CRITICAL, CountryGroup.A): (Priority.HIGH.name, True),
    (Severity.CRITICAL, CountryGroup.B): (Priority.HIGH.name, True),
    (Severity.CRITICAL, CountryGroup.C): (Priority.HIGH.name, True),
    (Severity.HIGH, CountryGroup.A): (Priority.HIGH.name, True),
    (Severity.HIGH, CountryGroup.B): (Priority.MEDIUM.name, True),
    (Severity.HIGH, CountryGroup.C): (Priority.MEDIUM.name, True),
    (Severity.MEDIUM, CountryGroup.A): (Priority.MEDIUM.name, True),
    (Severity.MEDIUM, CountryGroup.B): (Priority.MEDIUM.name, True),
    (Severity.MEDIUM, CountryGroup.C): (Priority.LOW.name, False),
    (Severity.LOW, CountryGroup.A): (Priority.LOW.name, False),
    (Severity.LOW, CountryGroup.B): (Priority.LOW.name, False),
    (Severity.LOW, CountryGroup.C): (Priority.LOW.name, False),
}


def escalate_priority(a: str, b: str) -> str:
    """Return the higher-priority (lower rank) of two priority names."""
    return a if PRIORITY_RANK.get(a, 9) <= PRIORITY_RANK.get(b, 9) else b


# --------------------------------------------------------------------------- #
# Reporting factors (monotonic overrides — they can only escalate, never demote)
# --------------------------------------------------------------------------- #

# Disease tiers are config-driven (see [classification] in config.toml). These
# tuples are the canonical factory defaults; ``config`` imports them instead of
# re-declaring the literals. The module-level sets below are mutated by
# :func:`configure_disease_tiers` at startup.
DEFAULT_PANDEMIC_RISK_DISEASES: tuple[str, ...] = (
    "ebola", "marburg", "mpox", "monkeypox", "nipah", "h5n1", "sars", "mers",
    "lassa", "crimean-congo", "rift valley", "hantavirus",
)
DEFAULT_OUTBREAK_OF_CONCERN_DISEASES: tuple[str, ...] = (
    "cholera", "measles", "polio", "poliomyelitis", "yellow fever", "plague",
    "anthrax", "diphtheria", "avian influenza", "avian flu",
)

_PANDEMIC_RISK_DISEASES: set[str] = set(DEFAULT_PANDEMIC_RISK_DISEASES)
_OUTBREAK_OF_CONCERN_DISEASES: set[str] = set(DEFAULT_OUTBREAK_OF_CONCERN_DISEASES)


def configure_disease_tiers(
    pandemic_risk: "tuple[str, ...] | list[str] | None" = None,
    outbreak_of_concern: "tuple[str, ...] | list[str] | None" = None,
) -> None:
    """Override the disease keyword tiers at runtime (called from CLI _load
    after parsing the optional ``[classification]`` config section). Pass an
    empty container to disable a tier."""
    if pandemic_risk is not None:
        _PANDEMIC_RISK_DISEASES.clear()
        _PANDEMIC_RISK_DISEASES.update(pandemic_risk)
    if outbreak_of_concern is not None:
        _OUTBREAK_OF_CONCERN_DISEASES.clear()
        _OUTBREAK_OF_CONCERN_DISEASES.update(outbreak_of_concern)


def _is_pandemic_risk(name: str | None) -> bool:
    if not name:
        return False
    lowered = name.strip().lower()
    return any(keyword in lowered for keyword in _PANDEMIC_RISK_DISEASES)


def _is_outbreak_of_concern(name: str | None) -> bool:
    if not name:
        return False
    lowered = name.strip().lower()
    return any(keyword in lowered for keyword in _OUTBREAK_OF_CONCERN_DISEASES)


# Endemic / background pathogens whose pandemic_potential the AI routinely
# over-rates (seasonal influenza, COVID-19 as a global background state,
# undifferentiated "fever"). For these, pandemic_potential is clamped to LOW
# unless the AI cites a concrete novel/escalating signal — they should not
# force-report on pp alone. Config-driven via [classification] endemics.
DEFAULT_ENDEMIC_DISEASES: tuple[str, ...] = (
    "covid-19", "covid", "coronavirus", "influenza", "flu", "fever",
    "undiagnosed",
)

_ENDEMIC_DISEASES: set[str] = set(DEFAULT_ENDEMIC_DISEASES)


def configure_endemics(
    endemics: "tuple[str, ...] | list[str] | None" = None,
) -> None:
    """Override the endemic-pathogen set at runtime (called from CLI _load)."""
    if endemics is not None:
        _ENDEMIC_DISEASES.clear()
        _ENDEMIC_DISEASES.update(endemics)


def _is_endemic(name: str | None) -> bool:
    if not name:
        return False
    lowered = name.strip().lower()
    return any(keyword in lowered for keyword in _ENDEMIC_DISEASES)


def de_escalate_pandemic_potential(
    disease: str | None, pandemic_potential: int | None
) -> int | None:
    """Clamp pandemic_potential for endemic/background pathogens to LOW.

    Used when persisting AI digests so that an AI ``CRITICAL`` on seasonal flu
    is stored as ``LOW``. Returns the (possibly clamped) level, or ``None`` when
    the input is ``None``.
    """
    if pandemic_potential is None:
        return None
    if _is_endemic(disease) and pandemic_potential > Pandemic.LOW:
        return Pandemic.LOW
    return pandemic_potential


# Incident types whose mere occurrence at MEDIUM+ warrants reporting.
HIGH_IMPACT_TYPES: frozenset[str] = frozenset(
    {"tsunami", "volcano", "volcanic eruption"}
)

# GDACS population exposure thresholds.
POPULATION_REPORT_THRESHOLD: int = 100_000
POPULATION_MEDIUM_FLOOR: int = 10_000


@dataclass(frozen=True)
class ClassifyContext:
    """Pre-resolved inputs to :func:`classify`. ``country_group`` is the
    authoritative value from ``dim_country`` (single-sourced), not recomputed.

    ``pandemic_potential`` is the AI-assessed pandemic potential on the
    ``PANDEMIC_*`` scale (``None`` = not applicable / not yet digested).
    ``event_status`` is the AI-assessed event lifecycle status string.
    """

    level: int
    country_group: str
    region: str = ""
    disease: str | None = None
    incident_type: str = ""
    population: int = 0
    source_tiers: tuple[str, ...] = ()
    pandemic_potential: int | None = None
    event_status: str = ""


def classify(context: ClassifyContext) -> tuple[str, bool]:
    """Multi-factor reporting verdict (V3).

    Starts from the baseline ``(level, country_group)`` matrix, then:

    * **Disease incidents** (``incident_type`` in :data:`DISEASE_TYPES`):
      the AI-assessed ``pandemic_potential`` is the PRIMARY signal. When it is
      set, it overrides keyword tiers. When it is ``None`` (not yet digested),
      the keyword tiers act as a bootstrap fallback.
    * **All incidents**: monotonic physical factors (high-impact type,
      population exposure, tier-A source corroboration) may escalate.
    * **Disease incidents** with ``event_status`` in :data:`NON_EVENT_STATUSES`
      are suppressed at the end (final word).

    Returns ``(priority_name, should_report)``.
    """
    priority, should_report = PRIORITY_MATRIX.get(
        (context.level, context.country_group), ("LOW", False)
    )

    incident_kind = context.incident_type.strip().lower()
    is_disease = incident_kind in DISEASE_TYPES

    # Factor: disease-led reporting (disease incidents only).
    if is_disease:
        # Endemic / background pathogens (seasonal flu, COVID-19, undiagnosed
        # fever) never escalate reporting on pandemic_potential alone — clamp
        # the AI's level to LOW before deciding.
        effective_pp = context.pandemic_potential
        if _is_endemic(context.disease) and effective_pp is not None:
            effective_pp = min(effective_pp, Pandemic.LOW)
        if effective_pp is not None:
            # AI signal is authoritative.
            if effective_pp >= Pandemic.HIGH:
                should_report = True
                priority = escalate_priority(priority, "HIGH")
            elif effective_pp == Pandemic.MEDIUM:
                should_report = True
                priority = escalate_priority(priority, "MEDIUM")
            # Pandemic.LOW / Pandemic.NONE: no escalation (baseline stands).
        else:
            # Bootstrap fallback before first AI digest.
            if _is_pandemic_risk(context.disease):
                should_report = True
                priority = escalate_priority(priority, "HIGH")
            elif _is_outbreak_of_concern(context.disease) and context.level >= Severity.MEDIUM:
                should_report = True
                priority = escalate_priority(priority, "MEDIUM")

    # Factor: high-impact physical events (tsunami, volcano) at MEDIUM+.
    if (
        incident_kind in HIGH_IMPACT_TYPES
        and context.level >= Severity.MEDIUM
    ):
        should_report = True
        priority = escalate_priority(priority, "MEDIUM")

    # Factor: GDACS population exposure.
    if context.population >= POPULATION_REPORT_THRESHOLD:
        should_report = True
        priority = escalate_priority(priority, "MEDIUM")
    elif context.population >= POPULATION_MEDIUM_FLOOR and context.level >= Severity.MEDIUM:
        should_report = True

    # Factor: tier-A source corroboration (>=2 authoritative feeds).
    tier_a_count = sum(1 for tier in context.source_tiers if tier == "A")
    if tier_a_count >= 2 and context.level >= Severity.MEDIUM:
        should_report = True
        priority = escalate_priority(priority, "MEDIUM")

    # Suppression: AI-flagged non-events / declared-eliminations have the final
    # word on disease incidents (e.g. polio-free milestones, computer-virus
    # noise misrouted into the disease track).
    if is_disease and context.event_status.strip().lower() in NON_EVENT_STATUSES:
        should_report = False

    return priority, should_report


# --------------------------------------------------------------------------- #
# Event-based severity derivation (applied at incident creation)
# --------------------------------------------------------------------------- #

def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _usgs_severity(raw_fields: dict) -> int:
    magnitude = _as_float(raw_fields.get("mag", raw_fields.get("magnitude")))
    significance = _as_int(raw_fields.get("sig"))
    tsunami = bool(raw_fields.get("tsunami"))
    if tsunami or significance >= 600 or magnitude >= 7.0:
        return Severity.CRITICAL
    if significance >= 400 or magnitude >= 6.0:
        return Severity.HIGH
    if significance >= 150 or magnitude >= 5.0:
        return Severity.MEDIUM
    return Severity.LOW


_GDACS_ALERT_TO_LEVEL: dict[str, int] = {
    "red": Severity.HIGH,
    "orange": Severity.MEDIUM,
}


def _gdacs_severity(raw_fields: dict) -> int:
    alertlevel = str(raw_fields.get("alertlevel", "")).strip().lower()
    return _GDACS_ALERT_TO_LEVEL.get(alertlevel, Severity.LOW)


# Per-source initial-severity derivers, keyed by the source token (matched as a
# substring of ``source_name`` so "USGS Earthquakes" / "WHO Disease Outbreak
# News" resolve correctly). Adding a new source's severity rule is one entry
# here, not a new branch in derive_severity (open/closed).
_SEVERITY_DERIVERS: dict[str, Callable[[dict], int]] = {
    "usgs": _usgs_severity,
    "gdacs": _gdacs_severity,
    "who": lambda _fields: Severity.MEDIUM,
}


def derive_severity(raw: RawIncident) -> int:
    """Derive an initial severity for a single source record.

    WHO Disease Outbreak News are authoritative outbreak notices -> MEDIUM;
    HealthMap is a broad feed (low baseline) -> LOW; AI digest may escalate
    both later via the ratchet.
    """
    name = (raw.source_name or "").lower()
    raw_fields = raw.raw_fields or {}
    for token, deriver in _SEVERITY_DERIVERS.items():
        if token in name:
            return deriver(raw_fields)
    return Severity.LOW


def derive_initial_severity(records: tuple[RawIncident, ...] | list[RawIncident]) -> int:
    """Max severity across the composing records of an incident."""
    if not records:
        return Severity.LOW
    return max(derive_severity(record) for record in records)
