# Storage Specification: Disaster Surveillance Reporter

> **Status:** BASELINED (2026-05-11)
> Rethought storage rules replacing the old reference-tracking system.

---

## What Was Wrong With the Old Approach

The previous storage design (v2.0) used a complex reference-tracking system with separate JSONL files for indexing (`by-country-group.jsonl`, `by-incident-type.jsonl`, `by-country.jsonl`, `all-incidents-index.jsonl`). Problems:

1. **Reference drift** — line numbers in reference files become stale when records are appended or updated
2. **Maintenance burden** — daily/weekly cleanup scripts needed to rebuild references
3. **Over-engineering** — the dataset is small (dozens of incidents/day), not a big-data problem
4. **Three storage backends with different semantics** — JSONL, Email, Google Sheets each treated the same via `StorageBackend` protocol, but they have fundamentally different purposes

---

## New Storage Rules

### Rule 1: Three Distinct Backends, Three Distinct Purposes

The three storage backends are NOT interchangeable. Each serves a specific role:

| Backend | Purpose | Write Pattern | Read Pattern |
|---------|---------|---------------|--------------|
| **JSONLStore** | Canonical data store | Append-only, immutable | Query by date, filter in memory |
| **EmailReporter** | Distribution output | Batch send (once per pipeline run) | Not readable (fire-and-forget) |
| **GoogleSheetsStore** | Shared viewing/filtering | Append to daily tab | Read for dashboard/analysis |

### Rule 2: JSONLStore Is the Single Source of Truth

**Directory structure:**

```
incidents/
├── by-date/
│   ├── 2025-03-11.jsonl    # All incidents for that date, one per line
│   ├── 2025-03-10.jsonl
│   └── ...
└── media/
    ├── 2025-03-11.jsonl    # Media coverage records
    └── ...
```

**Key decisions:**
- ONE file per date. No subdirectories, no separate reference files.
- Records are appended, never modified in place.
- Updates to an existing incident produce a NEW record in today's file with the same `incident_id` and an incremented `updated_date`.
- Queries work by scanning files. With <100 incidents/day, this is fast enough.
- No reference files, no index files, no summary files. The JSONL files ARE the data.

**Write contract:**
```python
class JSONLStore:
    def append(self, records: list[dict], date: str | None = None) -> int:
        """Append records to the date file. Returns count written."""
        ...

    def query(self, *, date_from: str, date_to: str,
              country_group: str | None = None,
              incident_type: str | None = None,
              priority: str | None = None,
              status: str | None = None) -> list[dict]:
        """Query records across date range with optional filters."""
        ...
```

**Dedup rule:** If a record with the same `incident_id` already exists in today's file, skip it. Use content similarity (rapidfuzz) to detect near-duplicates across sources for the same event.

### Rule 3: Email and Sheets Are Derived Outputs, Not Storage

**EmailReporter:**
- Called once at the end of each pipeline run
- Takes the list of incidents that passed `should_report=true`
- Sends an HTML table via Gmail SMTP
- Does NOT implement `read()` — it's a delivery endpoint, not a data store
- Template: today's date, priority-sorted table with key fields

**GoogleSheetsStore:**
- One tab per date (YYYY-MM-DD format)
- Appends classified incidents to the current day's tab
- Used for team visibility and manual filtering
- Column headers: `incident_id`, `incident_name`, `summary`, `country`, `country_group`, `incident_type`, `incident_level`, `priority`, `status`, `estimated_affected`, `estimated_deaths`, `sources`, `classification`
- Can be read back for reconciliation

---

## StorageBackend Protocol (Revised)

```python
class StorageBackend(Protocol):
    """Base protocol for storage backends."""

    def write(self, records: list[dict]) -> None:
        """Write records to storage (replace or append, backend-specific)."""
        ...

    def read(self) -> list[dict]:
        """Read records from storage. May return empty for write-only backends."""
        ...
```

```python
class ReportBackend(Protocol):
    """Protocol for distribution backends (email, etc.)."""

    def send(self, records: list[dict]) -> None:
        """Send report for the given records."""
        ...
```

Backends implement ONE of these protocols, not both. The pipeline configures which backends to use for each purpose.

---

## Pipeline Integration

```python
@dataclass
class PipelineConfig:
    sources: list[SourceAdapter]
    store: JSONLStore           # Canonical data store
    reporters: list[ReportBackend]  # Email, etc.
    viewers: list[StorageBackend]   # Google Sheets, etc.
```

Pipeline flow:
1. **Fetch** from all sources → `list[RawIncidentData]`
2. **Transform** (AI enrichment) → `list[dict]` (ClassifiedIncident)
3. **Dedup** against today's existing records
4. **Store** → append to JSONLStore (always)
5. **Report** → send to ReportBackends (email) if `should_report=true`
6. **View** → append to Viewers (Google Sheets) for visibility

---

## Data Retention

| Period | Action |
|--------|--------|
| 0–30 days | Active in `by-date/`, full query access |
| 30–365 days | Keep as-is, available for queries |
| 1+ years | Optional: compress to `.jsonl.gz` |

No automated archival needed at current scale. Manual cleanup when `by-date/` exceeds 1000 files.

---

## File Format

Each `.jsonl` file contains one `ClassifiedIncident` JSON object per line.

```jsonl
{"incident_id":"20250311-ID-EQ","incident_name":"Earthquake in Sumatra, Indonesia","created_date":"2025-03-11T10:15:00Z","updated_date":"2025-03-11T14:30:00Z","status":"Active","classification":{...},"sources":[...],...}
{"incident_id":"20250311-PH-FL","incident_name":"Floods in Manila, Philippines","created_date":"2025-03-11T08:00:00Z","updated_date":"2025-03-11T08:00:00Z","status":"Active","classification":{...},"sources":[...],...}
```

**Encoding:** UTF-8
**Line separator:** `\n`
**No trailing newline required**
**No empty lines**

---

## Query Examples

```python
store = JSONLStore(Path("incidents"))

# Today's incidents
today = store.query(date_from="2025-03-11", date_to="2025-03-11")

# This week's HIGH priority Group A incidents
weekly = store.query(
    date_from="2025-03-05",
    date_to="2025-03-11",
    country_group="A",
    priority="HIGH",
)

# All active earthquakes this month
earthquakes = store.query(
    date_from="2025-03-01",
    date_to="2025-03-11",
    incident_type="Earthquake",
    status="Active",
)
```

---

## Changes

| Date | Source | Change | Reason |
|------|--------|--------|--------|
| 2026-05-11 | Rethought design | Replaced reference-tracking system with simple date-file store | Old system was over-engineered for the data volume |
