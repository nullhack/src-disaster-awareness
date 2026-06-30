# Fact-Table Dead Weight Audit

Column-by-column scan of `disaster.db` cross-referenced against the source
adapters and `store/_source_factories.py`. Two categories: **buggy** (data
exists upstream, we read the wrong key) and **truly dead** (upstream has no
such field, so the column can never be populated).

---

## Category 1 — Buggy columns (fix the adapter/factory) — DONE

### `fact_usgs_earthquake.magnitude` — all rows `0.0` — FIXED

- Factory read `raw_fields.get("magnitude")` but the USGS GeoJSON property key
  is `mag`. `dict(p)` already copies it under the right name; only the factory
  key was wrong.
- **Fix:** `build_usgs` now reads `raw.raw_fields.get("mag", 0)`.

### `fact_usgs_earthquake.depth` — all rows `0.0` — FIXED

- Depth is not a GeoJSON *property*; it lives in
  `feature["geometry"]["coordinates"][2]` (lon, lat, depth_km). The adapter
  never read `geometry`, so the key was absent from `raw_fields`.
- **Fix:** `usgs.py` `fetch()` now extracts `coords[2]` into
  `raw_fields["depth"]`.

### `fact_usgs_earthquake.place` — stored the *title*, not the place — FIXED

- The factory set `place=raw.incident_name`. `incident_name` comes from
  `p.get("title")`, i.e. the event title. The GeoJSON also has a separate
  `place` property (the human-readable location string). `dict(p)` already
  copied it into `raw_fields["place"]`; the factory just passed the wrong
  source field.
- **Fix:** `build_usgs` now reads `raw.raw_fields.get("place", "")`.

---

## Category 2 — Truly dead columns (upstream provides nothing)

### GDACS XML *does* contain these — enhance the adapter — DONE

`sources/gdacs.py` previously built `raw_fields` with only `eventtype`,
`country`, `fromdate`, `event_id`. The five GDACS-namespaced elements were
present in each `<item>` (namespace `g = http://www.gdacs.org`, bound as `_NS`)
but ignored.

| column                    | before | GDACS element    |
|---------------------------|--------|------------------|
| `fact_gdacs_event.episodeid`   | `""` | `g:episodeid` (text)    |
| `fact_gdacs_event.alertlevel`  | `""` | `g:alertlevel` (text)   |
| `fact_gdacs_event.alertscore`  | `0`  | `g:alertscore` (text)   |
| `fact_gdacs_event.severity`    | `""` | `g:severity` (text)     |
| `fact_gdacs_event.population`  | `0`  | `g:population` (`value` attr) |

- **Fix:** `gdacs.py` `fetch()` now reads all five. `population` reads the
  element's `value=` attribute (the text content is descriptive, e.g.
  "20 thousand in 100km", and is not a clean integer); the other four read the
  text. The factory (`build_gdacs`) was already keyed correctly.

### WHO API has no such keys — remove the columns

`sources/who.py` does `raw_fields = dict(it)`, copying every WHO API key. The
API exposes `Title`, `OverrideTitle`, `PublicationDateAndTime`,
`ItemDefaultUrl`, `Summary`, `Description`, etc. — but no key named
`epidemiology`/`advice`/`assessment`/`overview`. These are aspirational columns
with no source.

| column                    | factory reads                   |
|---------------------------|---------------------------------|
| `fact_who_don.epidemiology` | `raw_fields.get("epidemiology")` |
| `fact_who_don.advice`       | `raw_fields.get("advice")`       |
| `fact_who_don.assessment`   | `raw_fields.get("assessment")`   |
| `fact_who_don.overview`     | `raw_fields.get("overview")`     |

**Direction:** drop the four columns via an Alembic migration.

### HealthMap listview has no such fields — remove the columns

HealthMap `getAlerts.php` rows are `[place, date, summary, disease, location]`.
There is no `species`/`cases`/`deaths`/`significance` anywhere in the response.
Those data come from WHO/ProMED, not HealthMap.

| column                        | factory reads                     |
|-------------------------------|-----------------------------------|
| `fact_healthmap_alert.species`      | `raw_fields.get("species")`      |
| `fact_healthmap_alert.cases`        | `raw_fields.get("cases")`        |
| `fact_healthmap_alert.deaths`       | `raw_fields.get("deaths")`       |
| `fact_healthmap_alert.significance` | `raw_fields.get("significance")` |

**Direction:** drop the four columns via an Alembic migration.

### `fact_news_article.country_key` — redundant, drop

The model column and FK exist, but `store/sqlite.py` `link_news` never assigns
`country_key` when inserting a `FactNewsArticle`. Every row is `NULL`.

A news article is always linked to exactly one `fact_incident` (via
`incident_key`), and that incident already carries its `country_key`. The
country is reachable as `fact_news_article → fact_incident → dim_country`, so
the denormalised copy on the news row adds nothing — any country filter/join
goes through the incident. Keeping the column would just be a redundant
denormalisation we'd have to keep in sync.

**Direction:** drop the column via an Alembic migration.

---

## Status

1. **Quick wins (no migration, data already fetched) — DONE:**
   - USGS factory: reads `mag` (was `magnitude`); reads `place` from
     `raw_fields["place"]` (was `incident_name`).
   - USGS adapter: extracts `depth` from `geometry["coordinates"][2]` into
     `raw_fields["depth"]`.
   - GDACS adapter: reads the five `g:*` elements into `raw_fields`
     (population via `value` attr); factory already keyed correctly.
   - Tests updated: fixtures now use real keys (`mag`/`depth`/`place`);
     `v_usgs_earthquake` test asserts depth + place round-trip; USGS + GDACS
     adapter tests assert the new extractions. 96 passing.
   - Existing `disaster.db` rows unchanged — the fixes apply to **new**
     ingestions.
2. **Column drops (Alembic migration `bdc77a90477b`) — DONE:**
   - Dropped WHO `epidemiology`/`advice`/`assessment`/`overview`.
   - Dropped HealthMap `species`/`cases`/`deaths`/`significance`.
   - Dropped News `country_key` (redundant — incident already carries country).
   - Migration recreates the 3 affected views (`v_who_don`,
     `v_healthmap_alert`, `v_news_article`) without the dropped columns.
   - `models.py` + `_source_factories.py` + `link_news` updated; schema test
     asserts `country_key` is gone. `alembic check` clean on fresh DB.
3. **Full rebuild of `disaster.db` — DONE (no re-ingest):**
   - `DISASTER_DB_URL=sqlite:///disaster.db alembic upgrade head` created a
     clean empty file at revision `bdc77a90477b` (correct
     `REFERENCES fact_incident` everywhere). `/tmp/opencode/restore_clean.py`
     then ATTACHed the prior backup and copied rows with explicit column
     lists in FK order, `PRAGMA foreign_keys=ON` as the integrity check.
   - All rows preserved (414 incidents / 25 WHO / 1121 HealthMap / 73 news /
     113 GDACS / 21 USGS). Zero `PRAGMA foreign_key_check` violations; zero
     `fact_incident_old` references remain. `alembic check` =
     "No new upgrade operations detected". Backups at `disaster.db.bak{,2,3}`.
4. **Backfill historical rows with real values — DONE:**
   - `/tmp/opencode/backfill_sources.py` looked up each existing row by its
     source-native ID and UPDATEd the stale placeholder values written by
     pre-step-1 code: 21 USGS rows via the FDSN `eventid` archive
     (`mag`/`depth`/`place`); 113 GDACS rows via `rss_7d.xml` indexed by
     `eventid` (`episodeid`/`alertlevel`/`alertscore`/`severity`/`population`).
   - Zero stale rows remain in either table; `v_usgs_earthquake` and
     `v_gdacs_event` now show populated data. Data-only backfill, no schema
     change (alembic check still clean).

Each remaining step ships as its own Alembic migration + edit + test.

---

## Additional finding — Legacy FK corruption (pre-Alembic artifact) — RESOLVED

### All five child tables reference a non-existent `fact_incident_old`

- **Symptom:** `sqlite3 disaster.db ".schema"` shows every child fact table
  (`fact_usgs_earthquake`, `fact_gdacs_event`, `fact_who_don`,
  `fact_healthmap_alert`, `fact_news_article`) with
  `FOREIGN KEY(incident_key) REFERENCES "fact_incident_old"` — a table that no
  longer exists.
- **Cause:** the one-shot `/tmp/opencode/migrate_drop_status.py` script (run
  before Alembic existed) did `RENAME fact_incident TO fact_incident_old`,
  created a new `fact_incident`, copied rows, then
  `DROP TABLE fact_incident_old`. SQLite rewrote the child FK targets to follow
  the rename, leaving them pointing at the dropped table. `PRAGMA
  foreign_keys=OFF` was set during the script, so the dangling references never
  raised.
- **Why `alembic stamp head` didn't reconcile it:** stamping only writes the
  version row; it does not rewrite physical DDL. The DB is *labelled*
  `ec2f0a478cfa` but its schema still carries the corruption.
- **Direction:** rebuild `disaster.db` from a clean `alembic upgrade head` on
  an empty file. The baseline migration emits correct
  `REFERENCES fact_incident`. Because ingest is idempotent and all 414 rows
  come from live source feeds, re-running the pipeline repopulates everything.
- **Resolution (step 3 above):** the full rebuild via `restore_clean.py` did
  exactly this — clean `alembic upgrade head` + surgical row copy. All five
  child tables now `REFERENCES fact_incident`; zero
  `fact_incident_old` references; `PRAGMA foreign_key_check` clean.

### Structurally single-value columns (expected, NOT dead)

These look uniform but are correct by design — included so they are not
mistaken for dead weight in a future audit:

- `source_key` on each child fact (each source owns one row in `dim_source`).
- `fact_healthmap_alert.feed_source` — always `HealthMap`.
- `fact_who_don.provider` — always `WHO Disease Outbreak News`.
- `fact_incident` date columns — all `today` because every ingest so far was a
  single-day run; will diversify once multi-day ingestion happens.
- `type_key` on USGS — always `Earthquake` (USGS only serves quakes).
- `fact_usgs_earthquake.tsunami` — structurally all `0` because no recent 4.5+
  event triggered a tsunami warning; real signal, not a bug.
