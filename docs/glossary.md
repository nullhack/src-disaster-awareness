# Glossary: src-disaster-report-v4

> The ubiquitous language for this project — terms shared across conversation,
> code, and documentation (Evans, 2003). Curated from the interview for the
> IMPORTANT domain concepts, not every code symbol. Grouped by bounded context,
> where each term has one meaning. The tests are the source of truth for
> behaviour; this glossary is the source of truth for names. Extend or revise
> entries as understanding shifts.

## Context: Source records

### source record
A raw entry that one adapter fetches from one feed, kept in that source's own schema and keyed by `(source, source_id)` where `source_id` is the adapter's internal id (USGS eventid / GDACS eventid / WHO DonId), with no common box and no cross-source dedup at intake.
*Aliases: SourceReport · Source: discovery interview 2026-07-04*

### adapter
A source's own fetch + parse + `should_monitor` rule + `derive_keys`, such that adding a source is one adapter rather than a central source-type branch.
*Aliases: SourceAdapter · Source: discovery interview 2026-07-04*

### should_monitor
A per-adapter relevance filter that decides whether a source record is kept or dropped (over-reporters like GDACS filter hard; under-reporters stay permissive), and that absorbs v3's smeared disease-vs-physical branching (WHO owns disease semantics; USGS/GDACS do not).
*Aliases: none · Source: discovery interview 2026-07-04*

### derive_keys
A per-adapter derivation that produces exactly two search phrases from a source record — a strict key and a loose key — type-first, with WHO deriving the disease name heuristically first. **Single place with a country name:** strict = `{Type} {place_token}, {country} {Mon YYYY}`[+` {disease}` for WHO], loose = `{Type} {country} {YYYY}`[+` {disease}` for WHO]. **Multi-country (2+ places) or global (0 places):** strict = `""` (skip — no single country to anchor), loose = `{Type} {continent_token} {disease} {YYYY}` (continent word from the most-frequent region token; ties return all tied sorted; order-independent). **Global (0 places):** loose = `{Type} {disease} {YYYY}` (no region token). The place_token is the town stripped from `locality`'s distance prefix (`"65 km SSW of Sarangani, Philippines"` → `"Sarangani"`); when `locality` is empty the token is empty and strict degrades to country-only (subdivision is NOT substituted). DDG: strict first; empty results ⇒ loose fallback. 1 call per kept SourceReport (+1 if loose fallback). Examples — USGS single: `Earthquake Sarangani, Philippines July 2026` / `Earthquake Philippines 2026`; GDACS single: `Tropical Cyclone China July 2026` / `Tropical Cyclone China 2026`; WHO single: `Disease India June 2026 Nipah` / `Disease India 2026 Nipah`; WHO multi (DRC+Uganda): `""` / `Disease africa Ebola 2026`; WHO global: `""` / `Disease Yellow fever 2026`.
*Aliases: none · Source: discovery interview 2026-07-04 · revised 2026-07-07*

### deterministic country scan
A place-extraction strategy that scans DON prose sections for country names via an alias table over pycountry (longest-first word-boundary regex), replacing the prior LLM path. No fuzzy search, no API call, no hallucination. The scan's failure mode (over-inclusion of endemic/background countries) is less harmful than the LLM's failure mode (omission) for search.
*Aliases: none · Source: discovery interview 2026-07-07*

### alias table
A mapping of country-name strings (pycountry canonical names plus manual overrides: DRC both "Democratic Republic of the Congo" and "Democratic Republic of Congo" without "the", South Korea, Iran, Russia, Taiwan, Hong Kong, etc.) to ISO alpha_2 codes, compiled into a longest-first regex so multi-word aliases win over substrings. Replaces `pycountry.search_fuzzy`, which silently mis-resolves "Congo" to CG and rejects "Democratic Republic of the Congo".
*Aliases: none · Source: discovery interview 2026-07-07*

### per-country exact subdivision match
A subdivision resolution strategy that matches admin1 names from iso3166-2 against body text, scoped to one country's alpha_2, case-insensitive word-boundary. No cross-country fuzzy likeness. Fixes "Rwampara"→UG-435 (Uganda, not LK-52 "Ampara" Sri Lanka) and "Tristan da Cunha"→no-GB (it belongs to SH-TA, Saint Helena).
*Aliases: none · Source: discovery interview 2026-07-07*

### Global short-circuit
A rule that a DON title containing "global" (case-insensitive) yields places=[]; global situation reports defer country extraction to downstream summarization. Multi-country / Multi-locations titles are NOT short-circuited (body names specific affected countries).
*Aliases: none · Source: discovery interview 2026-07-07*

### continent token
A search-key token derived from UN M49 subregions by taking the most-frequent continent word (africa/asia/europe/america/oceania) across all place regions; ties return all tied tokens sorted. Order-independent — replaces the prior `places[0].region` design. e.g. DRC (Middle Africa) + Uganda (Eastern Africa) → "africa".
*Aliases: none · Source: discovery interview 2026-07-07*

### USGS
An earthquakes source that serves GeoJSON summary feed(s) (`4.5_day` M≥4.5 24h, and `significant_day` for curated notable events), whose bad-slug soft-404 returns HTTP 200 with a `"404 File Not Found"` body so detection cannot rely on status alone.
*Aliases: none · Source: discovery interview 2026-07-04*

### GDACS
A geo/hydro/weather source that serves a multi-type XML 24h feed typed by `<gdacs:eventtype>` (never `Unknown`), whose bad-path soft-200 returns HTTP 200 with an HTML shell so detection must check the root tag.
*Aliases: none · Source: discovery interview 2026-07-04*

### WHO DON
A disease-outbreaks source that serves a JSON OData feed with no structured disease field (the disease name lives in the DON Title free-text, extracted by Title-parse first, AI fallback) and a real HTTP 400 on a bad query. Country/place extraction is now deterministic (alias table + per-country iso3166-2 subdivision match over the 5 DON prose sections: Summary, Overview, Epidemiology, Assessment, Response); the LLM stays for the digester (summaries) only.
*Aliases: none · Source: discovery interview 2026-07-04 · revised 2026-07-07*

## Context: News

### news item
A deduped news fact that DDG returns with fields `date, title, body, url, image, source` (and domain), whose `published_date` is sticky on re-ingest and which dedups on ingest by the deferred canonical key.
*Aliases: NewsItem · Source: discovery interview 2026-07-04*

### DDG news search
A library boundary (`ddgs.DDGS.news`, region pinned `wt-wt`) that searches candidate news strict-first with loose fallback, which vcrpy cannot intercept so tests monkeypatch `ddgs.DDGS.news`.
*Aliases: none · Source: discovery interview 2026-07-04*

### candidate news
A set of DDG search results for a kept source record that drives the run's next step: empty ⇒ bare store and stop; non-empty ⇒ one AI digest.
*Aliases: none · Source: discovery interview 2026-07-04*

### bare store
A write of a source record that yielded no candidate news, with no AI call, no links, and no timeline row.
*Aliases: none · Source: discovery interview 2026-07-04*

### news dedup key
A canonical key by which news items dedup on idempotent ingest (the one deferred empirical decision), chosen from raw url / normalised url (strip scheme + tracking params such as `ocid`) / url+domain / content-hash of title+body, and which must be syndication-aware.
*Aliases: none · Source: discovery interview 2026-07-04*

### syndication
A republish pattern (MSN, seen in the Sudan cholera coverage) where the same article appears under a different url and source, which a url-only dedup key misses and the chosen key must still recognise as already-ingested.
*Aliases: none · Source: discovery interview 2026-07-04*

### report↔news link
A unique M:N edge `(source_report_id, news_item_id, incident_id, relevance_score, linked_at)` that ties a source record and a news item into a cluster and whose relevance score is frozen once written. `linked_at` stores the linked `NewsItem.published_date` (the date DDG returns) — not ingest processing time — so the active-window test and any timeline view reflect when the news actually broke.
*Aliases: ReportNewsLink · Source: discovery interview 2026-07-04 · revised 2026-07-09*

### relevance score
A per-news-item relevance measure that the AI assigns and that is frozen once the link is written (no weight updates).
*Aliases: none · Source: discovery interview 2026-07-04*

## Context: Incidents

### incident
A reconciled real-world event that is the connected component (the "cluster") in the source-record↔news graph, carrying no mutable derived recency field (recency and the active set are derived from the timeline at read time).
*Aliases: cluster · Source: discovery interview 2026-07-04*

### incident id
A deterministic label assigned to a cluster from the graph (never by AI), where news mapping to an existing incident takes that incident's id, news with no cluster mapping gets a new id, and news shared between two source records merges them into one incident. The id is `source:source_id` of the genesis (earliest-by-date) report — human-readable, stable across replays of the same batch. Stored as the PK of the `incidents` table.
*Aliases: none · Source: discovery interview 2026-07-04 · revised 2026-07-08*

### incidents table
A warehouse table `(incident_id PK, incident_category, incident_type, name, first_seen_at, genesis_report_id)` that makes incident identity explicit (was: derived from `DISTINCT incident_logs.incident_id`). `incident_category` and `incident_type` are copied from the genesis source report at birth; `genesis_report_id` is the denormalized `source:source_id` (no FK — `source_reports` PK is composite). Birthed by `_commit_pending` after the clusterer assigns ids; upserted idempotently on `incident_id`.
*Aliases: none · Source: discovery interview 2026-07-08*

### incident_category
A 2-value taxonomy field `{disease, geophysical}` on the `incidents` table, derived from the genesis report's source (WHO→disease, USGS/GDACS→geophysical) via `_category_for_source(source)` at incident birth. NOT stored on `source_reports` — derived at birth. A taxonomy boundary sourced from the adapter, not a hardcoded token list. Drives the top-level `##` section of the markdown report.
*Aliases: none · Source: discovery interview 2026-07-08*

### incident_type
A specific-type field on the `incidents` table (e.g. Ebola, Earthquake, Tropical Cyclone, Flood). WHO: `disease_from_title(name) or "Disease"` (specific disease name like "Ebola", "Nipah"); USGS: "Earthquake"; GDACS: one of {Tropical Cyclone, Earthquake, Flood, Forest Fire, Drought, Tsunami, Volcano}. Copied from the genesis report's `incident_type` at birth. Drives the `###` sub-section of the markdown report.
*Aliases: none · Source: discovery interview 2026-07-08*

### cluster
A connected component of source records and news items joined by links, such that shared news yields one cluster and no overlap yields a new cluster — the system's only grouping step (cluster emergence). The history-aware clusterer (Tier 2) applies the 0/1/2+ rule: 0 touched incidents → birth, 1 → join, 2+ → bridge.
*Aliases: none · Source: discovery interview 2026-07-04 · revised 2026-07-08*

### incident_connections
A warehouse table `(incident_a, incident_b, bridge_report_id, connected_at)` with PK `(incident_a, incident_b, bridge_report_id)` that records bridge edges — when a source report's news touches 2+ existing incidents, a new bridge incident is birthed and edges connect it to each touched incident. `incident_a < incident_b` lexicographically (normalized on insert). The hypergraph of incidents + connections is the cluster graph; rendering of connected components is deferred.
*Aliases: none · Source: discovery interview 2026-07-08*

### 0/1/2+ rule
The history-aware clusterer's incident-assignment rule, computed per connected component: count how many EXISTING incidents the component's news items already touch (via `report_news_links`). 0 → BIRTH (new incident, earliest-by-date canonical). 1 → JOIN (component takes the existing incident's id — immutable after birth). 2+ → BRIDGE (new incident + `incident_connections` edges to each touched incident). Dissolves the cross-batch merge problem.
*Aliases: birth/join/bridge · Source: discovery interview 2026-07-08*

### timeline
An append-only story of an incident made of dated summary rows keyed by `(iso_datetime, incident_id)`, where a row is added only when genuinely new news lands and an all-already-ingested AI selection drops the summary and writes no row.
*Aliases: IncidentLog · Source: discovery interview 2026-07-04*

### active incident
An incident whose most recent `report_news_links.linked_at` (news publication date) is within `active_window_days` of the injected clock's now, derived at read time, and that is therefore a re-poll candidate each run. (The signal moved off `incident_logs.iso_datetime`, which now carries report/event date; reading the publication date from the link is the only signal that tracks whether news about the incident is still flowing.)
*Aliases: none · Source: discovery interview 2026-07-04 · revised 2026-07-09*

### re-poll
A second phase of `run_ingest`, run after the new-SourceReport one-shot pass, that re-searches each active incident for news once per incident (not per source record) using the genesis SourceReport's strict-then-loose keys, with the existing `(news_item_id, incident_id)` dedup as the backstop. Addresses the freshness CIT: an incident searched once with weak keys must not be frozen at first-hour facts.
*Aliases: re-polling · Source: discovery interview 2026-07-09*

### no-churn
A rule that an ingest adding no genuinely new news mutates no incident row, because there is no stored mutable recency field and recency is derived from the timeline at read time. On re-poll, an all-already-linked selection writes zero rows — no new link, no timeline row, no LLM call.
*Aliases: none · Source: discovery interview 2026-07-04 · revised 2026-07-09*

## Context: AI digest

### AI digest
A single OpenRouter call (`dspy.ChainOfThought(FilterDigest)`, model id from `config.toml` `[openrouter] model`) for a kept source record that has candidate news, taking candidate news plus incident context (type, name, places, report date) plus prior timeline summaries as input and returning a per-news RELEVANT/NOT_RELEVANT judgement, the relevant subset as `selected_news`, a per-url relevance score (1.0 kept / 0.0 rejected), and a 2-3 sentence summary grounded ONLY in relevant articles (or "no relevant articles found" when the gate rejects all). LOW tolerance for false positives — defaults to REJECT, requires clear evidence of THIS incident to KEEP. The LLM is used ONLY for the digester; country/place extraction is deterministic.
*Aliases: AiDigester · Source: discovery interview 2026-07-04 · revised 2026-07-07*

### FilterDigest
The typed `dspy.Signature` behind the digester's relevance gate. Input fields: `incident_type`, `incident_name`, `incident_places`, `incident_date`, `candidate_news` (list of {url,title,body_excerpt,domain}). Output fields: `summary` (2-3 sentences, "if none relevant, say so"), `judgements` (list of {url, relevant, reason}). Docstring carries the "LOW tolerance for false positives" instruction. The `dspy.ChainOfThought(FilterDigest)` module is constructed once per digester; each digest call passes incident context + candidate news and reads the typed judgements. **Superseded by the digester split (pipeline-phases Decision 1):** this fused one-call signature (returning BOTH `summary` and `judgements`) is split into the digester filter (Phase 2) and the digester summary (Phase 3) — two call modes / two signatures. Named here so later states recognise the pre-split form; the split terms live in [[Pipeline phases]].
*Aliases: none · Source: discovery interview 2026-07-07 · revised 2026-07-10 (pipeline-phases D1 split)*

### OpenRouter
An AI provider behind the digest (called via `dspy.LM`→litellm→httpx) that is flaky (400s retry before raising `litellm.exceptions.BadRequestError`) and whose structured output is client-side (dspy TypeAdapter on the `FilterDigest` signature), so the summary is unconstrained model text that renderers must escape. The model id comes from `config.toml` `[openrouter] model` (currently `openrouter/deepseek/deepseek-v4-flash`), not hardcoded in code. `dspy.LM(model=, api_key=)` + `dspy.configure(lm=lm)` once; `dspy.ChainOfThought(FilterDigest)(...)` per digest.
*Aliases: none · Source: discovery interview 2026-07-04 · revised 2026-07-07*

## Context: Reporting

### JSON report protocol
A common JSON output materialised from the read model (incident + timeline + news) that is the report protocol every renderer is defined-on.
*Aliases: none · Source: discovery interview 2026-07-04*

### Markdown brief
A two-level report rendered from the read model (incidents + timeline + news), with no AI on the read path. Top level: `## Geophysical` / `## Disease` (fixed, 2 categories, stable order). Sub-sections: `### <incident_type>` (dynamic, alphabetical — e.g. `### Earthquake`, `### Ebola`). Routing by `incident.incident_category` (from the `incidents` table), NOT by token-scanning the `incident_id` string (the prior `_is_disease` was broken — `incident_id` is `source:source_id`, no disease tokens).
*Aliases: MarkdownRenderer · Source: discovery interview 2026-07-04 · revised 2026-07-08*

### renderer
A consumer of the JSON report protocol; the Markdown brief is built, while the Dashboard feed, Telegram, and Email renderers are defined-on-protocol but not built in v4.
*Aliases: none · Source: discovery interview 2026-07-04*

## Context: Configuration & CLI

### settings
A frozen configuration loaded from `config.toml` (non-secret configurable things: db_url, openrouter_model, active_window_days) and `~/.secrets/<project>.env` (the AI key, via `dotenv_values()`), whose key and model are never logged or committed. `Settings.__init__` raises `ValueError` on empty `openrouter_api_key` or `openrouter_model` — fail-loud, no silent empty-string default.
*Aliases: Settings · Source: discovery interview 2026-07-04 · revised 2026-07-07 · revised 2026-07-09*

### active_window_days
A frozen `Settings` field read from `config.toml [ingest]` (default 7) that sets the re-poll active window: an incident is a re-poll candidate iff its most recent `report_news_links.linked_at` (news publication date) is within this many days of the injected clock's now. Changing the window is a config edit, not a code change.
*Aliases: none · Source: discovery interview 2026-07-09*

### config discipline
The rule that the OpenRouter model id is read ONLY from `config.toml` `[openrouter] model`, with no hardcoded fallback constant or fallback model list in code. The model id (currently `openrouter/deepseek/deepseek-v4-flash`) lives in config.toml and nowhere else; changing models is a config edit, not a code change.
*Aliases: none · Source: discovery interview 2026-07-07 · revised 2026-07-08*

### clock
An injected "today"/now source that makes time-dependent behaviour deterministic under test and that supplies a datetime (the timeline keys on `iso_datetime`, not date alone).
*Aliases: none · Source: discovery interview 2026-07-04*

### ingest
A CLI command that runs the per-cycle fetch + cluster + write pipeline, defaulting to all sources with an optional `--source` filter, fail-isolated per source.
*Aliases: none · Source: discovery interview 2026-07-04*

### report
A CLI command that renders the brief from the read model with no AI on the read path.
*Aliases: none · Source: discovery interview 2026-07-04*

## Context: Pipeline phases

> Structural terms introduced by the `pipeline-phases` refactor — splitting
> the monolithic `run_ingest` into three independently-callable phases plus
> one orchestrator (Decisions 1–5, `.cache/pipeline-phases/interview-notes.md`).

### phase
A stand-alone, independently-callable pipeline stage that commits its own work and is independently resumable and no-churn idempotent on re-run, such that a mid-phase failure leaves committed rows surviving and the next phase runs on the partial commits. The refactor produces exactly three: the ingest phase, the news-search phase, and the log-generation phase.
*Aliases: none · Source: discovery interview 2026-07-10 (pipeline-phases D5)*

### ingest phase
The first pipeline phase (`ingest_source_reports`) that fetches from each adapter and idempotently stores ALL fetched `source_reports` + `report_places` — unconditionally, with no `should_monitor` gate, no DDG call, no LLM call. The gate/skip filters that today gate store-then-search together inside `run_ingest`'s `_process_report` (`pipeline.py:47-55,189-194`) move to the news-search phase's search decision.
*Aliases: Phase 1 · Source: discovery interview 2026-07-10 (pipeline-phases D2, D4)*

### news-search phase
The second pipeline phase (`search_news`) that, for each unsearched-or-active report, applies the `should_monitor`/`source_id` gate + `searched_keys` skip, derives keys, runs DDG strict-then-loose, calls the digester filter, and stores `news_items` + births/joins incidents — and which carries the active re-poll as a sub-behaviour (not a separate phase). Writes `news_items`, `report_incidents`, `news_incidents`; writes NO `incident_logs`.
*Aliases: Phase 2 · Source: discovery interview 2026-07-10 (pipeline-phases D1, D4)*

### log-generation phase
The third pipeline phase (`generate_logs`) that, for each incident with fresh linked news, reads the prior timeline, calls the digester summary (selected_news + prior_summaries), batches per-incident across reports, and appends `incident_logs`. Governs the delta summary + per-incident batching; writes only `incident_logs`.
*Aliases: Phase 3 · Source: discovery interview 2026-07-10 (pipeline-phases D1, D2, D4)*

### orchestrator
A pipeline function (`run_pipeline`) that calls the three phases in order 1 → 2 → 3, non-atomically — each phase commits its own work and the next picks up from committed state — owning no domain logic, only the sequence and collaborator threading. Replaces `run_ingest`'s top-level flow; what the CLI orchestrator command calls.
*Aliases: run_pipeline · Source: discovery interview 2026-07-10 (pipeline-phases D5)*

### digester filter
The Phase-2 AI call mode that takes candidate news + incident context and returns relevance judgements + the selected_news subset (the relevant articles), with NO summary — the relevance gate alone. One half of the split of the fused `FilterDigest` signature; doubles LLM call count (with the digester summary) in trade for cleaner per-incident deltas.
*Aliases: none · Source: discovery interview 2026-07-10 (pipeline-phases D1, Option A)*

### digester summary
The Phase-3 AI call mode that takes the selected_news + the prior_summaries chain + incident context and returns the delta summary (what is NEW since the latest prior summary date). The other half of the split of `FilterDigest`; consumed by `generate_logs` to append `incident_logs`. Enables per-incident batching across multiple reports for the same incident.
*Aliases: none · Source: discovery interview 2026-07-10 (pipeline-phases D1, Option A)*

### resumability stamp
The single canonical "this report was searched" record that the news-search phase writes on completion and skips on re-run, making the phase no-churn idempotent and independently resumable. The refactor collapses two divergent stamps into one: the warehouse `mark_report_searched` (the canonical, surfaced via `read_searched_report_keys`) survives; the `_news_searched_at` JSON-blob stamp written by `scripts/process_news.py` is dropped as drift.
*Aliases: none · Source: discovery interview 2026-07-10 (pipeline-phases D4, D5)*

## Context: Log-news provenance

> Structural terms introduced by the `log-news-provenance` change — a junction
> table giving each `incident_logs` row auditable provenance to the `news_items`
> that fed it, and a P3 fetch that summarizes only the unsummarized delta
> (`.cache/log-news-provenance/interview-notes.md`).

### incident_log_news
A junction table `(incident_id, log_datetime, news_id)` linking each `incident_logs` row to the `news_items` that fed it, with PK `(incident_id, log_datetime, news_id)`, composite FK to `incident_logs(incident_id, log_datetime)` ON DELETE CASCADE, FK to `news_items(news_id)` ON DELETE CASCADE, and an index on `news_id` for the reverse audit query. Mirrors the existing `news_incidents` / `report_incidents` junction shape. The minimum surface satisfying both per-log provenance and late-news correctness; the two lighter shapes (a `last_summarized_news_at` timestamp; a `summarized` flag on `news_incidents`) each fail one of those requirements.
*Aliases: none · Source: discovery interview 2026-07-11 (log-news-provenance)*

### log provenance
The auditable reference from an `incident_logs` row to the `news_items` that fed it, materialised as the `incident_log_news` junction edges. Closes the gap that today a log row carries no path back to its source news; the junction edge IS the provenance, not a flag or timestamp.
*Aliases: none · Source: discovery interview 2026-07-11 (log-news-provenance)*

### delta summarization
The P3 (`generate_logs`) behaviour of summarizing only the news for an incident whose `news_id` is NOT IN the already-linked set (`read_summarized_news_ids`), rather than re-summarizing the whole corpus every run. Binds AI cost per run to the new-news delta, not the corpus size. The anti-join is on `news_id` (not a timestamp) so late-arriving news is fetched and summarized on the next run.
*Aliases: none · Source: discovery interview 2026-07-11 (log-news-provenance)*

### late-arriving news
A news item ingested after a log already exists for its incident but whose `published_date` predates that log's `log_datetime`. Handled correctly because provenance is per-`news_id`, not timestamp-based: the anti-join fetches it on the next P3 run, summarizes it into a NEW log row, and links it there — never retroactively grafted onto the old log. A `published_date` equal to an existing `log_datetime` (PK collision) is resolved by a `clock_fn().isoformat()` fallback so the timeline stays monotonic with no silent loss.
*Aliases: none · Source: discovery interview 2026-07-11 (log-news-provenance)*

### read_summarized_news_ids
A Warehouse method `read_summarized_news_ids(incident_id) -> set[int]` returning the `news_id`s already linked to any log for the incident via `incident_log_news` — the anti-join source for delta summarization. A news item is "summarized" for an incident iff its `news_id` is in this set; there is no separate flag or timestamp.
*Aliases: none · Source: discovery interview 2026-07-11 (log-news-provenance)*

### append_timeline_with_provenance
A Warehouse method `append_timeline_with_provenance(log, news_ids)` that writes the `incident_logs` row and the `incident_log_news` rows in ONE transaction (the FK requires the log row present first, so the junction insert follows the log insert in the same `begin()` block; a failure rolls back both). `append_timeline` is preserved for other callers/tests.
*Aliases: none · Source: discovery interview 2026-07-11 (log-news-provenance)*

## Context: Dropped from v3

### HealthMap
A v3 feed source that is dropped because the funnel surfaced no HealthMap-specific need and three feeds (USGS, GDACS, WHO DON) + DDG cover v4's scope.
*Aliases: none · Source: discovery interview 2026-07-04*

### reclassify / redigest
A pair of v3 CLI commands that is dropped because the new model has no separate reclassification or redigest cycle.
*Aliases: none · Source: discovery interview 2026-07-04*

### store/_migrations.py + self-seeding
A v3 dual migration path that is dropped behind a single Alembic migration path.
*Aliases: none · Source: discovery interview 2026-07-04*

### configure_disease_tiers / configure_endemics
A pair of v3 global mutable config entry points that is dropped behind injected frozen config.
*Aliases: none · Source: discovery interview 2026-07-04*

### usgs_max_magnitude / gdacs_alert
A pair of v3 source fact names that leaked through the read interface and is dropped behind a read model over incident + timeline + news with no per-source fact-name leakage.
*Aliases: none · Source: discovery interview 2026-07-04*

### SEVERITY_LOW aliases / classify() / derive_* wrappers
A set of v3 compatibility shims that is dropped outright.

### LLM country extraction (retired)
The prior WHO country-extraction path (`country_extractor`, `_ExtractPlaces`, `_canonicalize`, `_canonical_country_and_alpha2`, `_recover_country_from_subdivision`, `_canonical_subdivision`, `OpenRouterPlaceExtractor`, the `place_extractor` adapter param) — retired in favour of the deterministic country scan. Named only so later states can recognise and exclude them; they appear nowhere as design.
*Aliases: none · Source: rejected 2026-07-07*
*Aliases: none · Source: discovery interview 2026-07-04*

## Rejected pre-pivot model terms

Named only so later states can recognise and exclude them; they appear nowhere
as design. See the Dead Terms register in `.cache/default/interview-notes.md`:
synthetic cross-source identity key (`YYYYMMDD-CC[-SUB]-TYPE`), identity-key
dedup at intake, `IncidentResolver`, identity `resolution`/`merge` services,
`place normalization`, `canonical_name`, `search_keys`, `identity-key
derivation`, `factor table`, `Verdict`, `monotonic ratchet`, `should_report
latch`, `non_event`, `Slowly Changing Dimension`/`SCD`, `canonical JSON
report`/`CanonicalReport`, and `last_news_at`.

## Security note

v3 `config.toml:15` committed a live OpenRouter key (`sk-or-v1-…`); it remains
in v3 git history and must be **rotated**. v4 reads all secrets from
`~/.secrets/<project>.env` via `dotenv_values()` into a frozen Settings, and the
key is never logged or committed.
