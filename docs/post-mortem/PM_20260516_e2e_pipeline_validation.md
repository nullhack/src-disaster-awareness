# PM_20260516 — E2E Pipeline Validation

**Date**: 2026-05-16
**Scope**: End-to-end pipeline run with real APIs (GDACS, WHO DON, EONET) + AI extraction via opencode serve
**Verdict**: **PASS** — pipeline core works. 6 bugs found, 0 blockers.

---

## Context

Full E2E pipeline test: fetch 3 live sources (GDACS 95 events, WHO DON 50 articles, EONET 100 events), run all 9 pipeline steps, extract AI data from one bundle via opencode serve at `localhost:4096` (password `abc123`). Raw fixtures saved to `/tmp/e2e/`.

## Summary of Findings

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | HIGH | `store.py:102,328,506` | `dt.now()` crash — `import datetime as dt` uses module alias, can't call `.now()` on module. Masked because `classification_date` is always set. |
| 2 | MEDIUM | `store.py:108` | `json.dumps(bundle, default=str)` serializes dataclass as `IncidentBundle(...)` Python repr, NOT valid JSON. `json.loads()` on stored data fails. |
| 3 | LOW | `store.py:104` | Path doubling: `base_path / "incidents" / "by-date" / ...` when `base_path` already includes `incidents/` |
| 4 | MEDIUM | `correlate.py`, `classify.py` | WHO + EONET mega-bundle: 150 records collapsed into 1. WHO has no `country` field; EONET country requires AI extraction. Both missing country → correlation treats as identical → all union into one giant bundle. |
| 5 | HIGH | `classify.py:134-163` | EONET not in `_derive_level()` chain. Only checks GDACS, WHO, GDELT. EONET records invisible to level derivation. |
| 6 | LOW | — | All bundles default to Group C without AI. `rules.get_country_group("")` → `"C"`. With `DSR_AI_PROVIDER=none`, this is always the case. |

---

## Detail

### Finding 1: `dt.now()` type error `(b68)`

`store.py:11` imports `datetime as dt`. Three call sites use the bare `dt.now(tz=dt.timezone.utc)` pattern:

```python
# store.py:102 — JSONLStore.store()
cls_date = bundle.classification_date or dt.now(tz=dt.timezone.utc).date()

# store.py:328 — JSONLStore.exists()
cls_date = bundle.classification_date or dt.now(tz=dt.timezone.utc).date()

# store.py:506 — _bundle_to_incident()
report_date=bundle.classification_date or dt.now(tz=dt.timezone.utc).date(),
```

`dt` is the `datetime` module. `datetime.datetime.now()` is the classmethod; `datetime.now()` doesn't exist. The call would raise `AttributeError: module 'datetime' has no attribute 'now'`.

**Why it's masked**: `ClassifyEngine.classify()` always sets `bundle.classification_date = now.date()` (line 64), so the `or` short-circuits and `dt.now()` is never reached in normal pipeline flow.

**Fix**: Replace all three with `dt.datetime.now(tz=dt.timezone.utc)`.

### Finding 2: Python repr, not valid JSON

`store.py:108`: `json.dumps(bundle, default=str)` on an `IncidentBundle` dataclass produces:

```
"IncidentBundle(incident_id='20260516-MG-DR', records=[RawRecord(source_name='GDACS', ...)], ...)"
```

This is a Python representation string, not a JSON object. `json.loads()` on this string returns a plain `str`, not a `dict`. The `_reconstruct_bundle()` method at line 152 handles this via `eval()` — but `eval()` is fragile and fails if dataclass field order changes or if `__repr__` format changes.

**Impact**: Storage files are not interoperable. External tools cannot parse the JSONL. The `eval()` reconstruction is a hard-coupling to Python's `dataclasses.__repr__()`.

**Fix**: Serialize with `dataclasses.asdict(bundle)` before `json.dumps()`. Deserialize with `IncidentBundle(**data)` after `json.loads()`.

### Finding 3: Path doubling

`store.py:104`: `self.base_path / "incidents" / "by-date" / ...`

When `base_path=/tmp/e2e/incidents/`, the result is `/tmp/e2e/incidents/incidents/by-date/...`. The `incidents/` sub-path is hardcoded in `store.py` regardless of whether `base_path` already includes it.

**Fix**: Either remove the hardcoded `"incidents"` segment from `store.py`, or document that `base_path` must NOT include `incidents/`.

### Finding 4: WHO + EONET mega-bundle

WHO DON articles have no `country` field (`regionscountries` is usually `null`). EONET events have country in `title` text, not as a structured field. When both records lack `country`, the correlator's country-overlap criterion says "one record has no country → match." This paired with title similarity transitively chains ALL world-wide events into one bundle.

Output from E2E: 50 WHO + 100 EONET = 150 records → 1 bundle with `incident_id=20260513-UNX-OTH`.

**Fix**: When BOTH records lack country, require title similarity above threshold instead of auto-matching.

### Finding 5: EONET not in level derivation

`classify.py:134-163` `_derive_level()` iterates `source_name == "GDACS"`, `"WHO"`, `"GDELT"` only. EONET records are skipped. The `_eonet_level()` helper exists but is never called.

**Impact**: EONET bundles always get default Level 2 with no source-specific level derivation.

**Fix**: Add EONET to the `_derive_level()` iteration chain, between WHO and GDELT per reliability order.

### Finding 6: Group C default without AI

`classify.py:24`: `rules.get_country_group(bundle.country or "")` — when country is `None`, `""` maps to Group C. Without AI extraction (`DSR_AI_PROVIDER=none`), country is always `None` for WHO and EONET bundles (GDACS has `iso3`).

**Impact**: All WHO/EONET bundles get Group C, which affects priority matrix: Level 2 Group C → `should_report=False` → skip DDG + AI. This is correct behavior (should_report=False means not reportable), but means WHO disease outbreaks in Group A countries are missed.

**Fix**: Non-actionable in code — requires AI or regex-based country extraction. GDACS provides `iso3` which maps cleanly.

---

## AI Integration: PASS

OpencodeProvider works correctly with opencode serve at `localhost:4096`. Extracted from GDACS Madagascar drought event:
- `disaster_type`: "Drought" ✅ (matches GDACS `eventtype=DR`)
- `country`: "Madagascar" ✅ (GDACS country field)
- `country_iso`: "MG" ✅ (ISO 3166-1 alpha-2)

Session management, basic auth, and response parsing all work. No retries needed, first attempt succeeded.

---

## Remediation Priority

1. **Fix Finding 1** (dt.now crash) — one-liner, no tests break
2. **Fix Finding 5** (EONET level derivation) — add to `_derive_level()` chain
3. **Fix Finding 4** (mega-bundle correlator) — tighten both-missing-country rule
4. **Fix Finding 2** (JSON serialization) — `dataclasses.asdict()` — breaks storage format
5. **Fix Finding 3** (path doubling) — adjust CLI or store.py
6. **Finding 6** (Group C default) — accept as design constraint; AI fills this gap
