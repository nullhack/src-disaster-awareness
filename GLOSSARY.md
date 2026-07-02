# Ubiquitous Language — disaster-report v3

This is the **single source of truth** for the words used throughout the
codebase. Every term below has one canonical spelling; the "Aliases to avoid"
column lists spellings that previously appeared and have been (or are being)
removed. When you write new code, use the canonical term.

**Reference taxonomy:** Evans, *Domain-Driven Design* (ubiquitous language per
bounded context); Fowler, *PoEAA* (Transaction Script vs Domain Model, ACL
boundary DTOs); refactoring.guru.

> **How we resolved cross-context variation:** the team chose to **flatten to
> one term everywhere** rather than keep per-context spellings. So where Evans
> would tolerate `disaster_type` (Source) ≠ `incident_type` (Incident), this
> project collapses them to `incident_type`. Surrogate keys (`*_key`) and
> genuinely-distinct concepts are preserved, not flattened.

---

## The five bounded contexts

| Context | Owns | Modules |
|---|---|---|
| **Source Ingestion** | translating external feeds → internal records | `sources/*` |
| **Identity / Resolution** | dedup; canonical id / name / search keys | `resolver`, `deriver` |
| **Classification** | severity / priority / reporting verdict | `classification` |
| **Persistence** | star-schema warehouse (Data Mapper) | `store/*`, `models` |
| **Reporting** | read-side rendering | `report`, `cli` |

---

## Incident (the central aggregate)

One **incident** is one real-world event, deduplicated across all sources. It
is the unit of tracking, classification, and reporting.

| Term | Definition | Aliases to avoid |
|---|---|---|
| **incident** | the real-world event aggregate | event (ambiguous), disaster (physical-biased) |
| **incident_id** | cross-source business key, format `YYYYMMDD-<TYPE>-<ISO2>` | — |
| **incident_key** | integer DB surrogate (Persistence only) | — |
| **incident_type** | the type label: `Earthquake`, `Flood`, `Disease`, `Epidemic`, … | **disaster_type**, type_name |
| **incident_category** | the type's family: `Natural` / `Biological` / `Unknown` | bare `category` (ambiguous with disease category) |
| **incident_name** | the **raw source title** of a source record (Source Ingestion only) | (do NOT reuse this name for the derived title) |
| **canonical_name** | the **derived** incident display title (Identity context) | — |
| **search_keys** | derived DDG query phrases for the incident | keys (ambiguous) |
| **summary** | 2–3 sentence prose description (AI-authored) | — |
| **event_date** | when the underlying event happened (the incident anchor) | — |

### Identity layers

| Term | Definition | Aliases to avoid |
|---|---|---|
| **incident_id** | cross-source business id (see above) | — |
| **incident_key** | DB surrogate int | — |
| **source natural key** | per-source dedup id (`don_id`, `usgs_id`, `gdacs_eventid`, `alert_id`); abstracted as `natural` in the store | event_id (raw, pre-mapping) |
| **url** | natural key for a news article | — |

---

## Disease (Biological incidents)

| Term | Definition | Aliases to avoid |
|---|---|---|
| **disease_name** | the pathogen label (`Ebola`, `Measles`, …) | **disease** (attr), `potential_name` |
| **disease_key** | DB surrogate | — |
| **disease_category** | always `Biological` | bare `category` (ambiguous) |

---

## Country / place

| Term | Definition | Aliases to avoid |
|---|---|---|
| **country** | primary domain attribute (name or ISO-2) | — |
| **country_name** | display form | bare `name` (on DimCountry) |
| **country_iso2** | ISO-3166 alpha-2 code (view attr) | — |
| **iso2** | ISO-3166 alpha-2 code (dim column) | — |
| **country_group** | reporting tier `A` / `B` / `C` | — |
| **region** | continent-normalized region | — |
| **normalize_country_name()** | country-name normalizer helper | **canonical_name()** (clashed with incident canonical_name) |
| **UNKNOWN_ISO2** | `"XX"` sentinel for unknown country | literal `"XX"` |
| **place** | free-text USGS-style locality (`near X, Country`) | — |

---

## Severity

The 1–4 impact scale. Ascending: 1=LOW, 4=CRITICAL.

| Term | Definition | Aliases to avoid |
|---|---|---|
| **Severity** | `IntEnum` 1–4 | — |
| **severity_level** | the int value in domain records (1–4) | bare `level` |
| **severity** | the label (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`) | severity_name, **sev** |
| **severity_key** | DB surrogate (PK + FK) | **level_key** |
| **severity_description** | display-only prose | bare `description` (ambiguous) |

`magnitude`, `alertlevel`, `alertscore`, `sig` are **physical inputs that derive
severity**, not severity synonyms.

---

## Pandemic potential

The 0–4 scale for disease incidents. 0=NONE, 4=CRITICAL.

| Term | Definition | Aliases to avoid |
|---|---|---|
| **Pandemic** | `IntEnum` 0–4 | — |
| **pandemic_potential** | the label or int | **pp**, potential_name |
| **pandemic_potential_key** | DB surrogate (PK + FK) | **potential_key** |

---

## Priority

The reporting-urgency scale. **Descending**: 1=HIGH, 3=LOW (opposite direction
to severity — intentional).

| Term | Definition | Aliases to avoid |
|---|---|---|
| **Priority** | `IntEnum` 1–3 | — |
| **priority** | the label (`HIGH`/`MEDIUM`/`LOW`) | priority_name |
| **rank** | the ordering int (1=most urgent) — genuinely a different concept from severity_level, keep | — |
| **priority_key** | DB surrogate | — |

---

## Reporting verdict

| Term | Definition | Aliases to avoid |
|---|---|---|
| **should_report** | boolean: is this incident reportable? | — |
| **event_status** | AI lifecycle label (`new_outbreak`/`ongoing`/`escalating`/`containment`/`elimination_declared`/`non_event`) | **es** |
| **NON_EVENT_STATUSES** | the statuses that force `should_report=False` | — |

---

## Source

| Term | Definition | Aliases to avoid |
|---|---|---|
| **source_name** | the source label (`USGS Earthquakes`, `WHO Disease Outbreak News`, …) | bare `name` (on DimSource); provider, feed_source (per-table aliases) |
| **source_key** | DB surrogate | — |
| **token** | short id (`usgs`, `gdacs`, `who`, `healthmap`, `ddg`) | — |
| **source_type** | `feed` or `news` | bare `type` (on DimSource) |
| **reliability_tier** | `A` / `B` / `C` authority tier | — |
| **data_freshness** | cadence (`daily`, `near-real-time`, `on-demand`) | — |
| **source_url** | source-row URL | — |
| **PRIOR_DIGEST_SOURCE** | sentinel source_name for re-feeding a prior AI summary | literal `"PRIOR_DIGEST"` |
| **outlet** | news publisher (sub-concept of source, for articles) | — |

---

## Dates (six concepts — all genuinely different)

| Term | Concept | Definition |
|---|---|---|
| **event_date** | (A) when the event happened | the incident anchor; `event_date := primary.report_date` |
| **source_date** | (B) when the source artifact was published/filed | **flattened** from publication_date / published_date / alert_date |
| **report_date** | inbound ACL field (Source Ingestion) | the event anchor as reported by the source; set on `RawIncident` |
| **first_reported_date** | (C) when WE first tracked the incident | set to today at ingest |
| **last_updated_date** | (D) last time WE got new signal | bumped on merge / develop |
| **ai_digest_date_key** | (E) when AI last digested | — |

Per-source native event-date columns (`FactGdacsEvent.fromdate_key`,
`FactUsgsEarthquake.time_key`) are source-native spellings of **event_date**
and are aliased as such in the `v_incident` view; the column names are kept as
the source-native terms.

---

## News

| Term | Definition | Aliases to avoid |
|---|---|---|
| **headline** | news article title (genuinely different from incident name) | title (ambiguous with source title) |
| **news article** | one `FactNewsArticle` row, linked to an incident by nullable FK | — |

---

## Cross-context translation table

Because we flatten, most translations are now identity (`→`). The remaining
bridges:

| Source Ingestion term | → Identity / Classification term |
|---|---|
| `RawIncident.incident_type` | `IncidentRecord.incident_type` (was the `disaster_type → incident_type` bridge) |
| `RawIncident.disease_name` (raw_fields) | `IncidentRecord.disease_name` (was `disease`) |
| `RawIncident.report_date` | `IncidentRecord.event_date` |
| `RawArticle.source_date` | `FactNewsArticle.source_date_key` |

| Persistence term | → Domain term |
|---|---|
| `*_key` surrogate | the corresponding business attribute (e.g. `country_key` → `country`) |
| ORM `FactIncident` | `IncidentRecord` (write) / `IncidentView` (read) |

---

## Flagged ambiguities (resolved)

These names previously meant two things; the resolution:

| Name | Was ambiguous between | Resolution |
|---|---|---|
| `name` | DimCountry.name / DimSource.name | renamed to `country_name` / `source_name` |
| `category` | incident category / disease category | both kept as `category` (different tables, disambiguated by table); exposed as `incident_category` in views |
| `type` | incident type / source type | incident type → `incident_type`; source type → `source_type` |
| `description` | severity prose / pandemic prose | both kept as `description` (per-dim, disambiguated by table) |
| `canonical_name` | incident title / country normalizer | country helper renamed → `normalize_country_name()` |
| `incident_name` | raw title / reassigned to canonical_name in dicts | `incident_name` = raw title only; dicts use `canonical_name` |
| `keys` / `key` | search_keys / incident_key ints / column names | qualified everywhere |

---

## Example dialogue

> **Analyst:** "What's the **incident_type** on the new **Ebola** record?"
> **Dev:** "It's `Disease`. The **disease_name** parsed from the WHO DON title
> is `Ebola`. **country** is `DR Congo`, **country_group** `A`. The
> **incident_id** is `20260619-CD-EP`."
> **Analyst:** "**Severity**?"
> **Dev:** "**Severity.CRITICAL** — AI set **pandemic_potential** `HIGH`. The
> verdict is **should_report**=true, **priority**=`HIGH`, **event_status**=
> `new_outbreak`."
> **Analyst:** "Any **news**?"
> **Dev:** "**source_date** in the last week: 11 articles, all matching the
> **search_keys**. **incident_key** 30."

---

## Rich-model convention (DDD)

* Domain logic lives **on the object that owns the data**: `ClassifyContext.verdict()`,
  `DeriveInput.canonical_name()` / `.search_keys()`, `Severity.from_name()`,
  `IncidentView.is_stale()` / `.is_reportable()`, `IncidentRecord.with_ratcheted_priority()`.
* **DTOs at ACL boundaries stay anemic** (correct DDD, not a smell):
  `RawIncident`, `RawArticle` (inbound from external feeds).
* **ORM persistence models stay anemic** (Data Mapper, **not** ActiveRecord):
  no `.save()` on entities; `FactIncident`/dims hold state only.
* Services keep orchestration / persistence / I/O: `Pipeline`, `IncidentStore`,
  `AIDigester`, source adapters.
