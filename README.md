# src-disaster-report-v5

> Disaster surveillance report pipeline

A Python project storing incidents, reports, news, and logs as a Git-backed
YAML tree (the **content tree** on the `data` branch) — replacing the SQLite
store of v4. The storage layer (`disaster_report/store/content.py`) is a
`ContentStore` over the tree; CI workflows attach the tree as a worktree, run
the pipeline in-place, and push normal commits to `data`.

News enrichment is provided by [`trafilatura`](https://trafilatura.readthedocs.io/)
via `disaster_report/fetchers.py` — every news item that survives the DSPy
relevance filter gets its source URL fetched, extracting real `title`,
`body` (≈300-char description), `published_date`, `author`, and `sitename`.

External submissions are accepted via GitHub issues using the
[`📰 Disaster news submission`](.github/ISSUE_TEMPLATE/news_submission.yml)
template; the `ingest-submissions` workflow (cron 3×/day) fetches, classifies
via DSPy, and births incidents from accepted submissions.

## How to run

### Full pipeline (one command)

```
uv run python -m disaster_report ingest -v
```

Runs all three phases in sequence: fetch+store → search news (per-report +
repoll active) → generate logs. Articles selected by the DSPy FilterDigest are
then enriched via trafilatura before being committed to the tree.

### Step by step

```bash
# 1. Fetch source RSS feeds (USGS, GDACS, WHO) — no AI, no network beyond RSS
uv run python -m disaster_report ingest-records -v

# 2a. Per-report news search (DDG + DSPy FilterDigest + trafilatura enrichment)
uv run python -m disaster_report search-news -v

# 2b. Repoll active incidents for fresh news
uv run python -m disaster_report search-news --repoll -v

# 3. Generate delta summaries as logs (DSPy SummaryDigest)
uv run python -m disaster_report generate-logs -v

# 4. Regenerate dashboard JSON + push to gh-pages
uv run python scripts/publish_dashboard_data.py
```

### One-off utilities

```bash
# Render the markdown brief from the read model
uv run python -m disaster_report report

# Generate dashboard JSON only (no gh-pages push)
uv run python scripts/generate_dashboard_data.py --tree-root data

# Manually insert a new incident into the content tree
uv run python scripts/new_incident.py \
    --source USGS --source-id us7000test \
    --type Earthquake --name "M 6.0 - Test" --date 2026-07-17

# Enrich news for active incidents via trafilatura (10s spacing, local commit)
uv run python scripts/enrich_active_news.py --window 7

# (One-time) Bootstrap the content tree from the historical v4 SQLite
PYTHONPATH=. uv run python scripts/migrate_v4_to_tree.py --tree-root data
```

### Options

- `--source USGS|GDACS|WHO` — limit to one source (ingest-records, search-news)
- `--source-id <id>` — force news search for one report (bypasses gate)
- `--news-timelimit d|w|m` — DDG news window: day/week/month (default: w)
- `-v` — verbose INFO logging with `[i/N]` progress indicators

## Local content tree setup

The `data/` directory is **gitignored on code branches** (it lives on `origin/data`).
To run the CLI locally, attach the data branch as a worktree once per clone:

```bash
git worktree add data origin/data
```

After that, every CLI command reads/writes into `data/` in-place. To pull the
latest CI-committed state:

```bash
git -C data pull --ff-only
```

To inspect the tree without a CLI run:

```bash
PYTHONPATH=. uv run python -c "from disaster_report.store.content import ContentStore; \
s = ContentStore('data'); \
print(len(s.read_incidents()), 'incidents,', len(s.active_incidents(7)), 'active(7d)')"
```

## External submissions

External users can submit disaster-related news articles via GitHub issues.
The flow is fully automated end-to-end:

1. **Submit**: open a new issue at
   https://github.com/nullhack/src-disaster-awareness/issues/new/choose and
   pick the **📰 Disaster news submission** template. Paste the article URL
   (required); optionally hint a category, country, or event date.
2. **Triage**: the `ingest-submissions` workflow (cron `0 1,9,17 * * *`, 3×/day)
   extracts the URL, fetches metadata via trafilatura, classifies via the DSPy
   `SubmissionClassifier`, and either births a new `MANUAL` incident or rejects.
3. **Outcome**: the issue is labeled `submission-imported` (with a tracking
   comment showing the new incident id) or `submission-rejected` (closed with a
   reason). Re-running on the same URL is idempotent (`sha1(url)[:16]` natural
   key) so duplicates are silently skipped.

The three labels — `submission-pending`, `submission-imported`,
`submission-rejected` — are the only state machine.

## Secrets

Secrets never live in the repo. Non-secret config goes in `config.toml`
(`[tree]`, `[openrouter]`, `[ingest]`); the OpenRouter API key goes in
`~/.secrets/disaster_report.env` (out-of-workspace), loaded with
`dotenv_values()` into a frozen typed `Settings` — never into `os.environ`.
Add one opencode permission rule so a direct read of the secrets path prompts:

```json
{ "permission": { "external_directory": { "~/.secrets/**": "ask", "*": "allow" } } }
```

CI uses the `OPENROUTER_API_KEY` GitHub secret.

## Branch topology

| Branch | Holds |
|---|---|
| `main` | Source code + CI + dashboard assets (`dashboard/{app.js,styles.css,index.html}`) |
| `data` | The content tree — incident-rooted YAML files (orphan branch) |
| `gh-pages` | Generated dashboard JSON + MD reports, auto-published by `publish.yml` |
| `db` | The historical v4 SQLite binary (`disaster_report.db`), preserved for reference |

The migration script `scripts/migrate_v4_to_tree.py` extracts `origin/db` one-time
to (re)bootstrap the content tree.

## CI workflows

| Workflow | Cron (UTC) | Purpose |
|---|---|---|
| `ingest.yml` | `0 */6 * * *` | P1: fetch source RSS, write reports to `data/` |
| `search-news.yml` | `30 */6 * * *` | P2: DDG + DSPy FilterDigest + trafilatura enrichment |
| `generate-logs.yml` | `0 1-23/6 * * *` | P3: DSPy SummaryDigest for active incidents |
| `ingest-submissions.yml` | `0 1,9,17 * * *` | Triage `submission-pending` issues → incidents |
| `publish.yml` | `30 1-23/6 * * *` | Regenerate `gh-pages` from `data/` |
| `tests.yml` | on push/PR | ruff + pyright + pytest + stubtest gates |

All four data-writing workflows share the `data-update` concurrency group
(serialise writes to `data/`) and push via `git push origin HEAD:data` (the
worktree is detached-HEAD). `publish.yml` runs in its own concurrency group
because it reads `data/` but does not write to it.

## Content tree layout

```
data/
├── reports/source={USGS,GDACS,WHO}/<ruuid>.yaml     # raw feed staging (unlinked)
├── news/<nuuid>.yaml                                 # transient news staging
└── incidents/<iuuid>/
    ├── incident.yaml                                 # {id, search_keys:[…]}
    ├── reports/source=<src>/<ruuid>.yaml             # linked reports
    ├── news/<nuuid>.yaml                             # pending news (unsummarized)
    └── logs/<YYYY-MM-DD>/
        ├── log.yaml                                  # {log_date, summary}
        └── news/<nuuid>.yaml                         # summarized news (co-located)
```

Relationships are encoded **by location, not by reference fields**:
- A report is "linked" iff it lives under `incidents/<iuuid>/reports/`; else staging.
- A news item's incident is its ancestor `<iuuid>` directory.
- A news item is "summarized" iff it lives under `logs/<date>/news/`; else pending.
- Genesis identity (name, type, category, first_seen_at) is derived lazily at
  read time from the earliest-dated linked report.

## Where things live

| Path | Holds |
|---|---|
| `disaster_report/` | source — `.pyi` stubs + `.py` bodies |
| `disaster_report/store/` | `ContentStore` + `_tree` (path helpers) — the v5 storage layer |
| `disaster_report/fetchers.py` | trafilatura-based `fetch_article` + `FetchedArticle` |
| `disaster_report/ai/openrouter.py` | DSPy `FilterDigest`, `SummaryDigest`, `SubmissionClassifier` |
| `tests/integration/`, `tests/e2e/` | integration + E2E tests only (no unit) |
| `tests/cassettes/`, `tests/fixtures/` | recorded vcrpy cassettes; fixtures |
| `scripts/` | migration, manual insert, enrichment, dashboard publish |
| `docs/glossary.md` | ubiquitous language |
| `dashboard/` | static dashboard assets (app.js, styles.css, index.html) |
| `.github/workflows/` | CI: ingest / search-news / generate-logs / publish / ingest-submissions / tests |
| `.github/ISSUE_TEMPLATE/` | external submission form |
| `.opencode/`, `.templates/` | methodology, templates |

## Tests

```bash
# Fast tests (config, fetcher, enrichment, submissions, cli, content store) — ~16s
uv run pytest tests/integration/config_test.py \
               tests/integration/fetchers_test.py \
               tests/integration/pipeline_enrich_test.py \
               tests/integration/ingest_submissions_test.py \
               tests/integration/content_store_test.py \
               tests/integration/_countries_test.py \
               tests/e2e/cli_test.py -q -o pythonpath=.

# Full suite (adds VCR-backed source adapter + AI tests) — ~3min
uv run pytest tests/ -o pythonpath=.

# Lint + types + stub contract
uv run ruff check disaster_report/ tests/
uv run pyright disaster_report/ tests/
uv run --with mypy python -m mypy.stubtest disaster_report.store.content \
                                       disaster_report.config \
                                       disaster_report.models \
                                       disaster_report.pipeline
```

## Dashboard

The dashboard is a static site served from `gh-pages`:
**https://nullhack.github.io/src-disaster-awareness/**

Aggregation windows: **1d, 3d, 7d, 30d, 90d, 365d** (read dynamically from
`agg/index.json`, so the trend dropdown auto-picks up new windows).

To run locally:

```bash
uv run python -m http.server 8000 --directory dashboard
# → http://localhost:8000
```

## Workflow methodology

The staged-contract pipeline runs discover → explore → plan → build → deliver →
shipped, one state at a time through flowr. Tests are the source of truth for
behaviour. See `AGENTS.md` for the binding constraints, the driving loop, and
the flowr commands.
