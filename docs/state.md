# Specification (current state)

> The living specification of this project's current state — what it is and
> where it is in its build. Regenerated each pipeline cycle by the refresh step
> from the truth: test `.pyi`, pending marks, cassettes, migrations, and the
> glossary. Never hand-edited; hand-authoring creates a second source of truth
> that drifts. Tests are the source of truth for behaviour — this file is a
> derived view. When prose and a test disagree, the test wins.

## Snapshot

- **Project:** src-disaster-report-v4
- **Version:** 0.1.0
- **Generated:** 2026-07-11 by flowr session `log-news-provenance`
- **Suite:** green · **Contracts:** 13/13 built (0 pending)
- **Purpose:** → see `README.md`

## Entry points & boundaries

**Entry points:** CLI — `task run` / `python -m disaster_report.cli ingest` runs the full pipeline (`run_pipeline`: fetch+store → search news → repoll active incidents → generate logs, non-atomic, each phase committing its own work); `ingest-records` runs phase one only (fetch+store, no DDG, no AI); `search-news` runs phase two only (relevance-gate + commit, `--source-id` bypass, `--news-timelimit` window, `--repoll` for active-incident re-poll only); `generate-logs` runs phase three only (delta summary + timeline append with provenance); `report` renders the markdown brief from the read model with no AI on the read path.

**Boundary:**
- *Internal (ours):* `cli`, `pipeline`, `store.base`, `sources.{who,usgs,gdacs,ddg_news}`, `ai.{base,openrouter}`, `reporting.{markdown,report}`, `_countries`, `_country_names`, `_regions`, `_search_keys`, `config`, `models`
- *External (depends on):* WHO DON OData feed, USGS GeoJSON feed, GDACS RSS feed, DuckDuckGo News search, OpenRouter LLM (deepseek-v4-flash)

## Contract index

The derived map of what this system does. Each row points at the test (the
behavioural truth) and the source `.pyi` (the type surface). Intent is
regenerator-authored from the test body and self-corrects each cycle.

| Contract | Module | Test | Intent (one line) | Status |
|---|---|---|---|---|
| CLI | `disaster_report.cli` | `tests/e2e/cli_test.py` | `ingest` calls `run_pipeline`; `ingest-records`/`search-news`/`generate-logs` call their phase function; `report` renders markdown; no `reclassify`/`redigest` commands | built |
| Pipeline | `disaster_report.pipeline` | `tests/e2e/pipeline_test.py` | Three phase functions (`ingest_source_reports`, `search_news`, `generate_logs`) + orchestrator (`run_pipeline`); P1 stores all fetched reports; P2 gates+searches+filters+births/joins + active re-poll; P3 delta-fetches unsummarized news via `read_summarized_news_ids` anti-join, summarizes per-incident with prior chain, appends timeline atomically with provenance junction + `clock_fn` fallback on `log_datetime` PK collision; orchestrator runs 1→2→3 non-atomically and returns `IngestReport` | built |
| Country scanner | `disaster_report._countries` | `tests/integration/_countries_test.py` | Deterministic text-scan country + subdivision extraction; Global short-circuit; alias table longest-first; per-country exact subdivision match | built |
| Country names | `disaster_report._country_names` | `tests/integration/_countries_test.py` | 249-entry static alpha_2→common name map (overrides pycountry for display + search keys) | built |
| Config | `disaster_report.config` | `tests/integration/config_test.py` | Frozen settings from `config.toml` + secrets env; non-empty openrouter_api_key/model enforced (fail-loud); `active_window_days` from `[ingest]` | built |
| DDG news source | `disaster_report.sources.ddg_news` | `tests/integration/ddg_news_source_test.py` | DuckDuckGo News adapter with timelimit windowing, 3s rate-limit, exponential backoff; crawl-timestamp dates resolved via URL date extraction | built |
| GDACS source | `disaster_report.sources.gdacs` | `tests/integration/gdacs_source_test.py` | GDACS RSS → SourceReport; coordinate-based ReportPlace places; Orange/Red `should_monitor` gate; soft-200 detected via content-type | built |
| OpenRouter digester | `disaster_report.ai.openrouter` | `tests/integration/openrouter_ai_test.py` | Two-mode digester: `.filter()` (dspy ChainOfThought(FilterDigest) relevance gate, returns FilterResult, no summary) + `.summarize()` (dspy ChainOfThought(SummaryDigest) delta summary over selected_news + prior_summaries, returns str) | built |
| Reporting (markdown) | `disaster_report.reporting.markdown` | `tests/integration/reporting_test.py` | Two-level brief: `## Geophysical` / `## Disease` + `### <type>`; routes by `incident_category` (not id-token scan); AI summary HTML-escaped | built |
| Store | `disaster_report.store.base` | `tests/integration/store_test.py` | Idempotent operational store: 7 tables (6 + `incident_log_news` junction) + `incidents` VIEW; surrogate integer keys (unix ms); `active_incidents` reads `MAX(news_items.published_date)` within window; `append_timeline_with_provenance` writes log row + junction edges atomically; `read_summarized_news_ids` is the delta anti-join source | built |
| USGS source | `disaster_report.sources.usgs` | `tests/integration/usgs_source_test.py` | USGS GeoJSON → SourceReport; coordinate-based ReportPlace via iso3166-2 reverse_lookup; ocean fallback; M5.5+ `should_monitor` gate; soft-404 detected via body | built |
| WHO source | `disaster_report.sources.who` | `tests/integration/who_source_test.py` | WHO DON OData → SourceReport; deterministic text-scan ReportPlace places from 5 body sections; specific disease `incident_type` from title | built |
| Log-news provenance | `disaster_report.store.base` | `tests/integration/store_test.py` | `incident_log_news` junction gives each `incident_logs` row auditable provenance to the `news_items` that fed it; `read_summarized_news_ids` returns the already-linked `news_id` set per incident; `append_timeline_with_provenance` writes log + junction atomically (FK-failure rolls back both); one-time backfill links existing logs to news with `published_date <= log_datetime` (approximate, idempotent under `INSERT OR IGNORE`) | built |

## Composition & data flow

How the contracts assemble into the e2e path, and the data that flows through
it. Entity names follow `docs/glossary.md`.

`cli.ingest → run_pipeline(adapters, warehouse, ddg, digester, clock) → ingest_source_reports(adapters, warehouse): fetch each adapter → skip if key in existing_keys → warehouse.ingest_source_report(report) + ingest_report_places → search_news(warehouse, adapters, ddg_counter, digester_counter, clock): per report — _passes_gate (should_monitor or source_id bypass) → skip if key in searched_keys → derive_keys → _ddg_strict_loose (strict first, loose fallback if empty) → digester.filter(candidate_news, context) → _commit_news_for_report (birth first-new-news, join existing; ingest_news_item, assign_news_to_incident, add_report_incident) → mark_report_searched → search_news(warehouse, [], ddg_counter, digester_counter, clock): repoll active_incidents(window_days) → per incident _repoll_one_incident → generate_logs(warehouse, digester_counter): per incident — read_summarized_news_ids (anti-join source) → read_news → filter to unsummarized delta (news_id NOT IN summarized set) → empty delta → continue (no-churn) → read_timeline (prior chain) → digester.summarize(unsummarized, prior_summaries, context) → log_datetime = max(unsummarized.published_date) with clock_fn().isoformat() fallback on PK collision → append_timeline_with_provenance(log, news_ids) (atomic log row + junction edges) → return IngestReport(source_reports_kept, ai_calls, ddg_calls)`

`cli.search-news --repoll → search_news(warehouse, [], ddg, digester, clock): active_incidents(window_days) → per incident _repoll_one_incident: read_source_report_by_id (genesis) → derive_repoll_keys → ddg.search → dedup existing urls → digester.filter(fresh, context) → _commit_news_for_incident`

`cli.report → reporting.build_report → warehouse.{read_incidents (VIEW), read_timeline, read_news} → MarkdownRenderer.render(## category / ### type)`

**Data flow:** SourceReport → `source_reports` (surrogate report_id) → `report_places` (1:N) → NewsItem → `news_items` (UNIQUE url, sticky published_date, surrogate news_id) → `news_incidents` (1:1, assigns incident) + `report_incidents` (N:M) → `incident_logs` (delta summary keyed incident_id+log_datetime) → `incident_log_news` (junction, M:N log↔news provenance edges, atomic with log row) → store; `incidents` is a VIEW (genesis = earliest-by-date report via ROW_NUMBER()) → ReportDocument → markdown brief.

## Dependencies

**External services** — wire shapes live in the cassettes (the authoritative
external contract); this table points at them and never restates the shape.

| Service | Purpose | Protocol | Cassette | Env vars |
|---|---|---|---|---|
| WHO DON | Disease outbreak news feed | HTTPS (OData JSON) | `tests/cassettes/who_don.yaml` | — |
| USGS | Earthquake summary feed | HTTPS (GeoJSON) | `tests/cassettes/usgs_summary_feed.yaml` | — |
| GDACS | Disaster alert RSS | HTTPS (RSS XML) | `tests/cassettes/gdacs_rss_24h.yaml` | — |
| DuckDuckGo News | News search | HTTPS (JSON) | `tests/cassettes/ddg_news.json` | — |
| OpenRouter | LLM digester (filter + summarize, two call modes) | HTTPS (dspy→litellm) | monkeypatched (not vcrpy) | `API_KEY` |

**Persistence** — schema lives in the migrations (the migration IS the schema
spec); this table points at them and never restates the DDL. Test path uses
`create_all` from the table definitions in `store/base.py`.

| Entity | Store | Migration |
|---|---|---|
| `source_reports`, `report_places`, `news_items`, `report_incidents`, `news_incidents`, `incident_logs` | SQLite (`disaster_report.db`) | `migrations/versions/e7f8a9b0c1d2_redesign_schema_with_surrogate_keys.py` (6 tables, surrogate integer keys) |
| `incident_log_news` (junction) | SQLite (`disaster_report.db`) | `migrations/versions/f8a9b0c1d2e3_add_incident_log_news.py` (head — composite PK `(incident_id, log_datetime, news_id)`, 2 CASCADE FKs, index on `news_id`, one-time `INSERT OR IGNORE` backfill linking existing logs to news with `published_date <= log_datetime`) |
| `incidents` (VIEW) | SQLite | `e7f8a9b0c1d2` — derived via ROW_NUMBER() over `report_incidents` JOIN `source_reports`; genesis = earliest-by-date report; `incident_category` from source (WHO→disease else geophysical) |
| legacy: `report_news_links`, `incidents` (table), `incident_connections`, `relevance_score` | dropped | `e7f8a9b0c1d2` renames to `_legacy_*`, backfills, drops |

## Status & last cycle

- **Built:** 13 · **Pending:** 0 — backlog: none
- **Last cycle:** `log-news-provenance` added per-log news provenance to the disaster-report pipeline. One additive migration (`f8a9b0c1d2e3`) introduced the `incident_log_news` junction table (composite PK + 2 CASCADE FKs + `news_id` index) with a one-time `INSERT OR IGNORE` backfill linking existing logs to news with `published_date <= log_datetime`. `NewsItem` gained a `news_id` field plumbed through `_news_item_from_row`. Two new Warehouse methods: `read_summarized_news_ids(incident_id) -> set[int]` (the delta anti-join source) and `append_timeline_with_provenance(log, news_ids)` (atomic log row + junction edges in one transaction, parallel to — not wrapping — `append_timeline`). P3 `generate_logs` reworked: delta-fetches only unsummarized news (anti-join on `news_id`, not timestamp, so late-arriving news is summarized on the next run into a NEW log row), appends via `append_timeline_with_provenance`, and falls back to `clock_fn().isoformat()` on `log_datetime` PK collision. Conftest moved from root to `tests/conftest.py`; 25 pending markers stripped from green tests; package installed as editable. 212 tests green, 0 skipped, 0 pending, 90.22% coverage. Additive only — no existing column dropped, no existing row rewritten, `append_timeline` preserved for other callers.
- **Next:** none — shipped (backlog empty)
