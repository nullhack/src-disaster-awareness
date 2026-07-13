# src-disaster-report-v4

> Disaster surveillance report pipeline

A Python project on the staged-contract workflow: tests are authored up front as
a contract surface and built out one cycle at a time under flowr orchestration,
with the methodology layer (agents, skills, knowledge), the drift gates
(pyright, `mypy.stubtest`, ruff, pytest), and CI already in place.

## How to run

### Full pipeline (one command)

```
uv run python -m disaster_report ingest -v
```

Runs all three phases in sequence: fetch+store → search news → repoll active incidents → generate logs.

### Step by step

```bash
# 1. Fetch + store source reports (USGS, GDACS, WHO)
uv run python -m disaster_report ingest-records -v

# 2. Search news for new reports (DDG + AI filter)
uv run python -m disaster_report search-news -v

# 3. Repoll active incidents for fresh news
uv run python -m disaster_report search-news --repoll -v

# 4. Generate delta summaries as logs
uv run python -m disaster_report generate-logs -v

# 5. Generate dashboard JSON from DB + push to gh-pages
uv run python scripts/publish_dashboard_data.py
```

### Other commands

```bash
# Render the markdown brief from the read model
uv run python -m disaster_report report

# Generate dashboard JSON only (no gh-pages push)
uv run python scripts/generate_dashboard_data.py

# Inspect DB tables
uv run python scripts/show_tables.py
```

### Options

- `--source USGS|GDACS|WHO` — limit to one source (ingest-records, search-news)
- `--source-id <id>` — force news search for one report (bypasses gate)
- `--news-timelimit d|w|m` — DDG news window: day/week/month (default: w)
- `-v` — verbose INFO logging with `[i/N]` progress indicators
```

## Secrets

Secrets never live in the repo. Non-secret config goes in the workspace `.env`
(gitignored, `load_dotenv()`); secrets go in `~/.secrets/src-disaster-report-v4.env`
(out-of-workspace), loaded with `dotenv_values()` into a frozen typed `Settings`
— never into `os.environ`. `.env.example` is the committed env contract. Add one
opencode permission rule so a direct read of the secrets path prompts:

```json
{ "permission": { "external_directory": { "~/.secrets/**": "ask", "*": "allow" } } }
```

Full threat model in the `secrets-and-config` knowledge.

## Where things live

| Path | Holds |
|---|---|
| `disaster_report/` | source — `.pyi` stubs + `.py` bodies |
| `tests/integration/`, `tests/e2e/` | integration + E2E tests only (no unit) |
| `tests/cassettes/`, `tests/fixtures/` | recorded vcrpy cassettes; fixtures |
| `migrations/` | Alembic migrations — the schema spec |
| `docs/glossary.md` | ubiquitous language |
| `.flowr/flows/` | the six flow definitions |
| `.opencode/`, `.templates/`, `.github/` | methodology, templates, CI |

## Workflow

The staged-contract pipeline runs discover → explore → plan → build → deliver →
shipped, one state at a time through flowr. Tests are the source of truth for
behaviour. See `AGENTS.md` for the binding constraints, the driving loop, and
the flowr commands.
