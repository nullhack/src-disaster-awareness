# derive_keys stays a (strict, loose) pair; pipeline searches strict-first with loose fallback

> A record of a load-bearing architectural decision — the *why* behind a choice
> that multiple viable alternatives competed for. Authored only by the
> system-architect, only when a decision has genuine trade-offs **and**
> cross-cutting impact (reversing it would ripple across contracts); BAU
> decisions are not recorded. Supersession is edit-in-place: amend the body to
> the current decision and append a Change log row — do **not** create a new
> file. Tests are the source of truth for behaviour; the Traceability section
> points at affected artefacts and never restates them.

## Status

Accepted

## Decider + Date

- **Decider:** system-architect
- **Date:** 2026-07-06

## Context

The glossary (`docs/glossary.md` `derive_keys`) fixed the contract as a
`(strict, loose)` pair with strict-first DDG search and loose fallback. An
earlier v0.2 build cycle drifted from this: the pipeline's `_fan_out_queries`
iterated every entry in `report.places` and ignored the loose key entirely,
producing one DDG query per place per report. A live ingest against the three
feeds surfaced the cost — 149 places across 31 reports (WHO LLM extraction
over-split multi-country outbreaks into 14–20 places each) generated 646 news
items from 25-result DDG caps, dominated by msn/yahoo syndication noise, with
zero `report_news_links` committed because the batch aborted before
`_commit_pending`. The pipeline contract and the glossary had diverged, and the
per-place fan-out had no bounded call count.

## Decision

`derive_keys` stays `tuple[str, str]` — a strict key and a loose key — and the
pipeline searches strict-first, falling back to loose only when strict returns
empty results, with at most one call per key per kept source report.

## Alternatives considered

- **Per-place fan-out (the drift):** one DDG query per `places` entry, ignoring
  the loose key. Rejected — unbounded call count grows with `len(places)`, and
  WHO's LLM place extraction can emit 20 places per multi-country outbreak,
  producing hundreds of syndication-dominated results for one report.
- **Single strict key, no fallback:** one DDG call per report on the strict key
  only. Rejected — offshore epicenters (USGS "west of Macquarie Island") and
  multi-country WHO outbreaks yield `strict = ""`, so the report would get zero
  candidate news and bare-store with no second chance.
- **Per-place fan-out with a per-report cap:** keep the fan-out but bound it.
  Rejected — the cap is arbitrary, the loose key's role disappears, and the
  fan-out still favours quantity over the spec's strict-then-loose ordering.

## Consequences

- **(+)** DDG call count is bounded at 1–2 per kept source report, restoring
  the glossary's call-frequency rule.
- **(+)** Multi-country and global reports (strict = `""`) still reach the news
  search via the loose key, so outbreaks like Ebola DRC&Uganda or Yellow fever
  Global are not silently bare-stored.
- **(−)** A single-country report with a noisy strict key (rare place name) can
  miss results the loose key would have found; the strict-first ordering
  accepts this as the cost of precision. Mitigation: the loose fallback fires
  whenever strict returns empty.
- **(neutral)** `derive_keys`'s signature is unchanged, so adapters and the
  pipeline test fakes need no contract edit; only the implementations moved.

## Traceability

Points at the artefacts this decision touches; never restates their content.

- **Tests:** `tests/e2e/pipeline_test.py::test_pipeline_searches_strict_first_loose_only_when_strict_empty`, `test_pipeline_skips_loose_when_strict_returns_results`, `test_pipeline_skips_search_when_both_keys_empty`, `test_active_incident_members_are_repolled_for_news`; `tests/integration/usgs_source_test.py::test_derive_keys_*`; `tests/integration/gdacs_source_test.py::test_derive_keys_*`; `tests/integration/who_source_test.py::test_derive_keys_*` and `test_disease_name_*`
- **Source `.pyi`:** `disaster_report/_search_keys.pyi`, `disaster_report/sources/usgs.pyi`, `disaster_report/sources/gdacs.pyi`, `disaster_report/sources/who.pyi`, `disaster_report/pipeline.pyi`
- **Cassettes:** `tests/cassettes/usgs_summary_feed.yaml`, `tests/cassettes/gdacs_rss_24h.yaml`, `tests/cassettes/who_don.yaml`
- **Glossary:** `docs/glossary.md` `derive_keys`, `DDG news search`, `candidate news`
- **Related ADRs:** none

## Change log

Appended on any amendment; the body above always reflects the current decision.

| Date | Change | Reason |
|---|---|---|
| 2026-07-06 | Created | Reaffirm the glossary contract after the per-place fan-out drift produced 646 news items across 31 reports in a live ingest. |
