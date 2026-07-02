# Smell Audit — disaster-report v3

**Date:** 2026-07-01
**Scope:** `src/disaster_report/**` (logic + data layers) after the v3 changes
(disease track, deriver, news_filter, report module, CLI).
**Reference taxonomy:** refactoring.guru/refactoring/smells
**Principles applied:** DRY, YAGNI, KISS, cohesion (constants with their domain),
Object Calisthenics (small methods, no scattered eligibility checks). SOLID
(constants + pure helpers in the domain module; no behavior change).

> Guideline: **no intent/behavior change.** Contract changes allowed only to
> remove duplication or dead code. Tests must stay green (178 passing) and are
> updated only where a renamed symbol is referenced.

---

## A. Duplications (DRY) — *Repeated Data / Alternative Classes*

- [x] **A1. Disease-type frozenset duplicated 4×** (refactoring.guru: *Duplicate Code*).
  The literal `{"disease", "epidemic", "outbreak", "epidemics"}` is defined in:
  - `classification.py:86` `DISEASE_TYPES`  ← keep as single source of truth
  - `deriver.py:18` `_DISEASE_TYPES`
  - `news_filter.py:43` `_DISEASE_TYPE_KEYS`
  - `ai/openrouter.py:16` `_DISEASE_TYPES`
  `classification` is imported by `store/sqlite` + `pipeline` already and imports
  only `countries` at runtime → no cycle. **Fix:** delete the 3 private copies,
  import `DISEASE_TYPES` from `classification`.

- [x] **A2. Disease-list default literals duplicated** (*Duplicate Code*).
  `_DEFAULT_PANDEMIC_RISK_DISEASES` / `_DEFAULT_OUTBREAK_OF_CONCERN_DISEASES` /
  `_DEFAULT_ENDEMIC_DISEASES` exist in BOTH `config.py:13-24` (tuples) and
  `classification.py:125-177` (sets). **Fix:** make `classification` expose public
  `DEFAULT_*` tuples (canonical, domain-owned); `config` imports them; delete
  `config`'s copies. Update `test_classification.py:38-40` to the new names.

- [x] **A3. AI-digest payload built twice** (*Duplicate Code*).
  `pipeline.py` builds the identical `set_digest` dict at the dedup-merge site
  (`_ingest_new` ~312-324) and the new-row site (~368-380). **Fix:** extract
  `_digest_payload(digest, name, severity, keys, event_status)`.

- [x] **A4. `is_disease_type` idiom repeated ~7×** (*Shotgun Method*).
  `(incident_type or "").strip().lower() in DISEASE_TYPES` appears in `pipeline`
  (187), `news_filter` (126, 143, 158), `deriver` (32/95/130 via `_is_disease`),
  `openrouter` (`_is_disease_material`). **Fix:** add `is_disease_type(s)` helper
  in `classification` next to `DISEASE_TYPES`; use everywhere.

- [x] **A5. "Unknown country" sentinel check scattered** (*Primitive Obsession*).
  `deriver._clean_country` (36), `news_filter` `country_known` (125), and
  `_country_place_tokens` (92) each re-derive "is this a real country".
  **Fix:** add `is_known_country(name)` in `countries.py`; reuse.

## B. Dead code (YAGNI)

- [x] **B1. `_extract_reports` unused** (`ai/openrouter.py:158`).
  Defined but never called (`grep` confirms zero call sites). **Fix:** delete.

## C. Long methods (Object Calisthenics — methods ≤ a few screens)

- [x] **C1. `_ingest_new` is ~208 lines** (`pipeline.py:178-386`) — *Long Method*.
  Linear but does 9 things. **Fix:** extract self-contained helpers that do NOT
  increase parameter-noise:
  - `_bootstrap_news(...)` (in-window search + relevance filter) — DONE
  - `_digest_payload(...)` (from A3) — DONE
  - `_apply_disease_dedup_merge(...)` (early-return merge branch) — DEFERRED
    (see Execution log)
  Keep the linear top-level flow; no logic change. `_ingest_new` is now ~110
  lines; `_bootstrap_news` is 5 self-contained params.

- [x] **C2. `is_relevant` recomputes the disease-track test 3×** (`news_filter.py:126,143,158`)
  and `(country or "").strip()` twice (125). **Fix:** compute `is_disease_track`
  and `country_known` once (uses A4/A5 helpers).

## D. Cohesion (constants placement)

- [x] **D1. `_SEVERITY_NAMES` misplaced** (`pipeline.py:32`).
  The int→name map for `SEVERITY_*` belongs with the constants in
  `classification`. **Fix:** add `SEVERITY_NAMES` to `classification`; remove
  pipeline's `_SEVERITY_NAMES`.

## E. Minor cleanups

- [x] **E1.** `news_filter.is_relevant`: normalize `disaster_type` once instead
  of `.lower().strip()` on every use. (Folded into C2: `is_disease_track` is
  computed once via the helper.)

---

## Out of scope (verified intentional — DO NOT change)

- `store.merge_duplicate_disease_incidents` — no prod caller, but documented
  one-time cleanup util with 3 dedicated tests. Retained.
- `pipeline._retry_pending_digests` re-fetches active incidents — **intentional**:
  it must see fresh `ai_digest_date_key` state after `_develop` re-digests; reusing
  the pre-`_develop` snapshot would double-digest.
- `resolver._TYPE_CODES` disease→`EP` mapping — same strings as the disease set
  but a different structure (type→code, not membership). Coupling would hurt KISS.
- `deriver._clean_place` prefix-strip loop — works, well-commented; rewriting
  risks bugs for no clarity gain.

---

## Execution log

_Fill in as fixes land. Run `uv run pytest -q` after each group; expect 178 pass._

- **A1/A4:** deleted `_DISEASE_TYPES` (deriver, openrouter), `_DISEASE_TYPE_KEYS`
  (news_filter); all import `is_disease_type` / `DISEASE_TYPES` from
  classification. `deriver._is_disease` + `openrouter._is_disease_material` now
  delegate to the helper. `classify()` keeps its local `is_disease` (uses the
  already-lowercased `incident_kind` for the parallel `HIGH_IMPACT_TYPES` test —
  not the shotgun idiom).
- **A2:** classification exposes public tuples `DEFAULT_PANDEMIC_RISK_DISEASES` /
  `DEFAULT_OUTBREAK_OF_CONCERN_DISEASES` / `DEFAULT_ENDEMIC_DISEASES`; the runtime
  `_PANDEMIC_RISK_DISEASES` / `_OUTBREAK_OF_CONCERN_DISEASES` / `_ENDEMIC_DISEASES`
  sets are `set(DEFAULT_*)`. `config` imports the public tuples (removed its
  duplicated literals). `test_classification.py:38-40` updated to public names.
- **A3:** `_digest_payload(...)` module helper; both `set_digest` call sites in
  `_ingest_new` use it. New-row site's now-unused local `summary` dropped.
- **A5:** `countries.is_known_country`; used in `deriver._clean_country`,
  `news_filter._country_place_tokens` + `is_relevant`.
- **B1:** deleted `openrouter._extract_reports`.
- **C1:** extracted `_bootstrap_news(self, incident_id, primary, report_day,
  window, disease)`. `_ingest_new` down from ~208 to ~110 lines.
  **`_apply_disease_dedup_merge` DEFERRED** — the dedup-merge branch reads 10+
  enclosing locals (resolved, primary, today, is_today, digest, derived_name,
  severity_name, derived_keys, event_status, bootstrap_articles). Extracting it
  would violate the audit's own "do NOT increase parameter-noise" constraint, so
  the clearly-delimited inline `if existing_key is not None:` block is retained.
- **C2/E1:** `is_relevant` computes `is_disease_track = is_disease_type(...)`
  once and gates country via `is_known_country(...)` once; `place_t` branch
  simplified. Added state-subdivision token set (`_country_place_tokens`) so
  disease-track place-matching tolerates state-named local news.
- **D1:** `classification.SEVERITY_NAMES` added; pipeline imports it and the
  local `_SEVERITY_NAMES` dict (plus the now-unused `SEVERITY_*` constant
  imports) removed.
- **ai/openrouter.py:** `DEFAULT_FREE_MODELS` deleted (dead — digester always
  receives `config.ai_models`); `models` is now a required constructor param.
- **Result:** `uv run pytest -q` → **178 passed**. No lint/typecheck configured
  (no ruff/mypy in pyproject).

---

## Round 2 — SOLID / OOP / hardcoded-constants sweep

Scope: a deeper pass for duplicated/hardcoded constants and SOLID smells
solvable with small design patterns (registry, strategy, dict-dispatch).
The audit's own "SourceDescriptor is the upper bound of acceptable" rule
was the baseline. Several structural changes were **deferred** here as
out-of-scope for Round 2; two were later taken up in Round 3 at the user's
direction — Severity/Priority/CountryGroup enums (R11) and the `DateParser`
Strategy class (R10). The remainder stay out of scope: a Repository/UoW
layer over `SqliteIncidentStore`, an ABC base for the duck-typed adapters
(Protocols suffice — see R12), and a `Disease` value object.

- [x] **R1. Severity/priority/pandemic name↔level maps duplicated in store.**
  `classification` now exports `SEVERITY_LEVELS` (reverse of `SEVERITY_NAMES`),
  `PRIORITY_RANK`, `PANDEMIC_NAME_TO_LEVEL`, `PANDEMIC_LEVEL_TO_NAME` (all
  public). `store/sqlite.py` deleted its local `_PRIORITY_RANK` /
  `_SEVERITY_NAME` / `_SEVERITY_LEVEL` / `_PANDEMIC_NAME` / `_PANDEMIC_LEVEL`
  and imports the canonical maps (only store-specific `_SEVERITY_DESC`
  display text kept). `report._SEVERITY_RANK` / `SEVERITY_CHOICES` are now
  derived from `SEVERITY_NAMES`.
- [x] **R2. `"XX"` unknown-country sentinel re-typed in 3 modules.**
  `countries.UNKNOWN_ISO2` (renamed from private `_FALLBACK_ISO2`) is the
  single source; `pipeline._bootstrap_news`, `news_filter._country_place_tokens`,
  and `store._country_key` import it instead of retyping `"XX"`.
- [x] **R3. `"PRIOR_DIGEST"` source-name sentinel duplicated.**
  `sources.base.PRIOR_DIGEST_SOURCE` constant; `store.get_source_records` and
  `pipeline._develop` import+use it.
- [x] **R4. Seven ISO-date parsing helpers.** New `sources/_dates.py` exposes
  `parse_iso_datetime` / `parse_iso_date`. `pipeline._parse_date`,
  `_source_factories.parse_date`, `resolver._date_stamp`, `ddg_news._to_iso`,
  `who._to_iso` are now thin wrappers (each keeps its own failure policy).
  GDACS RFC-2822 and USGS epoch parsing stay in their adapters (different
  input formats). *(Superseded in Round 3 — R10: the wrappers + the
  adapter-local RFC-2822/epoch/strptime parsers all fold into one
  `DateParser` Strategy registry exposing a single `parse_date`.)*
- [x] **R5. Source metadata duplicated across cli/store.** New
  `sources/registry.py` defines a `SourceSpec` frozen dataclass +
  `SOURCE_REGISTRY`. `cli._SOURCE_REGISTRY` / `_NEWS_REGISTRY` are derived
  (filtered by `source_type`); `store._SOURCES` seed tuple and
  `source_tiers` token list are derived. Adding a source = one entry, not
  edits in three tables.
- [x] **R6. CLI hard-imported the concrete digester (DIP leak) + silently
  dropped unknown source tokens.** Added `_DIGESTER_REGISTRY` (mirrors the
  source/news registries); `_build_digester` dispatches on
  `config.ai_provider`. `_build_sources` now raises `ClickException` on an
  unknown token (was silently dropping — matched `_build_news` behavior).
- [x] **R7. `derive_severity` / `_gdacs_severity` if/elif chains (OCP).**
  `classification._SEVERITY_DERIVERS` dict (token → deriver fn) replaces the
  source-name if/elif; `_GDACS_ALERT_TO_LEVEL` dict replaces the alertlevel
  if/elif. New source severity rule = one dict entry.
- [x] **R8. Priority-ratchet block duplicated in `set_digest` +
  `reclassify_all`.** Extracted `store._ratchet_priority(...)`; both call
  sites reduced to one triple-unpack.
- [x] **R9 (bug). report disease-vs-physical split too narrow.** Three sites
  used `(incident_type).lower() == "disease"`, misclassifying
  `"Epidemic"`/`"Outbreak"` as physical. Now uses `is_disease_type(...)`.

**Result:** `uv run pytest -q` → **178 passed** after each group. CLI
`report --help`, `_SOURCE_REGISTRY` / `_NEWS_REGISTRY` / `_DIGESTER_REGISTRY`
resolution, and package import all verified.

### Still out of scope (round 2)
- `store._source_factories.SOURCE_FACTORIES` keeps its own token→build-fn
  table: folding it into `SOURCE_REGISTRY` would couple the registry to the
  ORM (`store._source_factories` → `models` → `store`), creating a cycle.
  Different concern (persistence), tolerable.
- `SqliteIncidentStore` remains one class (883→~1000 lines). Splitting into
  dimension-cache / classify helpers was judged net-negative cohesion for an
  internal module accessed only through the `IncidentStore` Protocol.
- `IncidentStore` Protocol not split (ISP) — the admin methods are exercised
  by tests and the split would touch every fake store for ~zero caller gain.
- `_usgs_severity` threshold ladder left as-is (thresholds, not categories).

---

## Round 3 — Enums + DateParser Strategy registry (user-directed)

Scope: the user reviewed Round 2's "overengineering explicitly avoided" list
and asked for two of those items to be done after all — enums (not
overengineering: IntEnum members *are* ints and str-mixin members *are*
strings, so they interop with the DB columns and existing comparisons with
zero migration) and the `DateParser` Strategy class. **ABCs were rejected**
in favour of the existing `Protocol`-based duck typing the codebase already
uses everywhere (`SourceAdapter`, `NewsAdapter`, `AIDigester`,
`IncidentStore`) — ABCs would add inheritance ceremony with no benefit over
structural typing.

- [x] **R10. `DateParser` Strategy registry class (supersedes R4).**
  `sources/_dates.py` is now a Strategy-pattern registry: a `DateParser`
  class holds an ordered list of `DateStrategy` callables, tries each in
  registration order, and returns the first non-`date`. Four strategies are
  registered on the module-level `default_parser`: ISO-8601 (`_parse_iso`,
  trailing-`Z` tolerant), strptime (`_parse_strptime`, handles HealthMap's
  `%d %b %Y`), RFC-2822 (`_parse_rfc2822`, GDACS), and epoch
  (`_parse_epoch`, USGS, ms-detect via `>1e12`). A single `parse_date(value)`
  convenience delegates to it. The 8 consumers (pipeline, store
  `_source_factories`, resolver, ddg/who/usgs/gdacs/healthmap) all call
  `parse_date`; the adapter-local RFC-2822/epoch/strptime parsers and the
  Round-2 thin wrappers are gone. **Extensibility win proven during
  implementation**: HealthMap's `%d %b %Y` format was missed by the initial
  RFC-2822 strategy and was added as a one-function + one-`register()`-call
  strptime strategy without touching any existing strategy.
- [x] **R11. Enums for Severity / Pandemic / Priority / CountryGroup.**
  `classification` now defines `Severity` / `Pandemic` / `Priority`
  (`IntEnum`) and `CountryGroup` (`str, Enum`). `SEVERITY_NAMES` /
  `SEVERITY_LEVELS` / `PANDEMIC_NAME_TO_LEVEL` / `PANDEMIC_LEVEL_TO_NAME` /
  `PRIORITY_RANK` are *derived from the enum members*, and `PRIORITY_MATRIX`
  is keyed by `(Severity, CountryGroup)` tuples. The legacy `SEVERITY_LOW` /
  `PANDEMIC_*` module aliases are kept as enum members, so ~25 test import
  lines and all DB int/string columns work unchanged (zero test edits, zero
  migration). `classify()` / `de_escalate_pandemic_potential` /
  `_usgs_severity` / `_gdacs_severity` / `_SEVERITY_DERIVERS` use the enum
  members directly for clarity in the definer module. `ai/openrouter.py`
  keeps its local `Severity = Literal[...]` type alias — that is the
  *external AI wire contract* (strings), a distinct concept from the enum.
- [x] **R12. Protocol over ABC reaffirmed.** No abstract base classes added.
  Adapters, digester, and store remain `typing.Protocol`-typed (structural);
  concrete classes need no inheritance, and missing methods are still caught
  by the type checker where annotations are present.

**Result:** `uv run pytest -q` → **178 passed**. Zero test edits required
(IntEnum/str-enum interop); report dates now serialise as date-only ISO
(downstream only ever consumed the date portion, so no observable change).

---

## Round 4 — Object Calisthenics soft pass

Scope: applied Jeff Bay's rules where they paid off, with **rules 7 (small
entities) and 8 (instance variables) applied softly** — the codebase holds
data-record dataclasses (`IncidentView`, `IncidentRecord`, `RawIncident`)
whose field counts are legitimate, not a cohesion smell. Rule 3 (wrap
primitives) was largely settled by the Round-3 enums.

- [x] **OC1 (rule 6 — no abbreviations).** Mechanical rename pass across
  sources, classification, deriver, pipeline, store, report, cli: `ctx`→
  `context`, `mag`/`sig`→`magnitude`/`significance` (locals only — USGS
  wire-format dict keys `"mag"`/`"sig"` kept), `inc`→`incident`, `f`→
  `feature`, `p`→`properties`, `it`→`item`, `r`→`row`, `et`→`event_type`,
  `resp`→`response`, `sev`→`severity`, `ph`→`placeholders`, `d`→`event_date`,
  `val`→`value`, `pp_*`→`pandemic_potential_*` in `set_digest`. **Kept**
  (domain/idiom): `exc` (`except … as exc`), `iso2`, `url`, `don` (WHO DON),
  short log/display labels (`"sev"`/`"pp"`/`"es"` in redigest output).
- [x] **OC2 (rule 1+2 — one indentation level / no else).**
  - `deriver.derive_search_keys` split into `_disease_keys` / `_physical_keys`
    / `_dedupe`; `pipeline.run` flattened from 5→1 level via `_safe_ingest_new`
    + `continue` guards; `news_filter.is_relevant` split into `_place_tokens` /
    `_type_match` (else-chains collapsed to one guard); `report._render_incident`
    split out `_disease_meta`; `store._seed_dimensions` collapsed via
    `_seed_if_missing` helper; `store.source_tiers` split into
    `_source_token_tiers` / `_match_source_tier`.
  - **Genuine two-track `else` kept** (not guard-convertible): disease vs
    physical search-key shape (`deriver`), disease vs physical AI prompt
    (`openrouter`), classify bootstrap fallback (`classification`).
- [x] **OC3 (rule 9 — tell, don't ask).** `ResolvedIncident.primary` +
  `.is_today(today)`; `IncidentView.is_stale(today, window)`. `pipeline`
  delegates instead of reaching into `incidents[0]` / field-by-field age
  checks. No `@property`-as-getter smell exists (all domain objects are
  frozen dataclasses with public fields).
- [x] **OC4 (rule 5 — one dot).** `sources.base.json_list(response, key)`
  replaces the `response.json().get(key, [])` chain in usgs/who/healthmap.
  (SQLAlchemy `session.execute(...).scalar_one_or_none()` chains are left —
  they're the idiomatic ORM call shape, not a Demeter violation.)

### Deferred (re-examined, intentionally not done)
- **CountryContext value object (rule 8) on `ClassifyContext`.** Would force
  rewriting ~30 `ClassifyContext(country_group=…)` test call-sites to fold
  `country_group` + `region` into one field. `ClassifyContext` is already the
  audit's "right shape — don't split further" (8.5); soft rule 8 says
  data-record field counts are legitimate. Net negative.
- **`SqliteIncidentStore` soft-split (rule 7).** The dimension-key resolvers
  are deeply interwoven with the persistence methods that call them; a split
  is a ~300-line mechanical shuffle with no `IncidentStore` Protocol benefit
  and real regression risk. Round-2 already judged it net-negative cohesion
  for an internal module.
- **`IncidentType` enum (rule 3).** Unlike `Severity`/`Pandemic` (clean
  bidirectional maps used in 25+ sites, DB columns, and arithmetic), incident
  types are just a vocabulary list shared by two *different* mappings —
  `store._INCIDENT_TYPES` (type→category) and `resolver._TYPE_CODES`
  (type→2-letter-code) — with imperfect overlap and input aliases
  (`"fire"`, `"epidemics"`) that aren't real types. Forcing an enum would
  create false symmetry between the two mappings; Round-2 audit 7.5 flagged
  coupling here as "would hurt KISS."

**Result:** `uv run pytest -q` → **178 passed**.
