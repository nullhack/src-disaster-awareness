# ADR_20260514_title_similarity_correlation

## Status

Accepted

## Context

DSR's Correlation context groups `RawRecord`s from different sources (GDACS, WHO, GDELT) that describe the same real-world incident. Title similarity is one of three matching criteria (alongside date proximity and country overlap). The spec requires a "normalized Levenshtein ratio ≥ 0.6" threshold. Quality attribute #1 (Reproducibility) demands deterministic matching — the same title pair must always produce the same similarity score. Quality attribute #5 (Performance) requires <5 seconds for 50 bundles without network calls.

The forces at play are: (1) title similarity must be deterministic and reproducible, (2) the algorithm must be fast enough for O(n²) pairwise comparison within a correlation pass, (3) adding external dependencies should be justified against the value they provide, (4) the threshold (≥0.6) needs to be tunable based on real-world matching results.

## Interview

| Question | Answer |
|---|---|
| Does the similarity algorithm need to be true Levenshtein distance? | The spec says "Levenshtein ratio" but the goal is deterministic title matching, not algorithmic purity. `difflib.SequenceMatcher` provides a similarity ratio (0.0–1.0) that serves the same purpose. |
| Should we use ML embeddings (sentence-transformers) for semantic similarity? | No — embeddings are non-deterministic across runs (model version, random seeds), require a heavy dependency, and add GPU/CPU overhead. Reproducibility (QA #1) is the top priority. |
| Is 0.6 the right threshold? | 0.6 is a starting point validated against example titles. It may need adjustment after testing with real fixture data. The threshold is a constant, easily tunable. |

## Decision

Use `difflib.SequenceMatcher.ratio()` from the Python standard library for title similarity comparison, with a threshold of ≥ 0.6. Titles are normalized before comparison: lowercased, stripped of leading/trailing whitespace, and collapsed multiple spaces to single space.

## Reason

`difflib.SequenceMatcher` provides deterministic, reproducible similarity scoring from the standard library — zero external dependencies — directly supporting Reproducibility (QA #1). While algorithmically different from Levenshtein (it uses the Ratcliff/Obershelp pattern-matching algorithm), it produces comparable similarity ratios suitable for title matching.

## Alternatives Considered

- **`python-Levenshtein` / `Levenshtean` package**: Provides true Levenshtein distance and ratio. Rejected because it's an external C dependency that adds installation complexity (build toolchain on some platforms) for marginal accuracy gain in title matching. The threshold can be calibrated for either algorithm.
- **`rapidfuzz`**: Modern, well-maintained fuzzy matching library with Levenshtein ratio. Rejected because it adds an external dependency (with C extensions) when stdlib `difflib` serves the purpose. Would be reconsidered if real-world testing shows `difflib` produces unacceptable false positive/negative rates.
- **ML embeddings (sentence-transformers)**: Semantic similarity via vector embeddings. Rejected because: (1) embeddings are non-deterministic across runs (violates QA #1 Reproducibility), (2) requires heavy dependencies (torch, transformers, ~2 GB), (3) adds significant processing time, (4) overkill for comparing short disaster title strings.
- **TF-IDF + cosine similarity**: Statistical text similarity. Rejected because it requires building a corpus model, is sensitive to vocabulary size, and adds complexity without clear benefit for short title strings.

## Consequences

- (+) Zero external dependencies — `difflib` is in Python standard library
- (+) Fully deterministic and reproducible across all platforms and Python versions
- (+) Fast: O(n²) pairwise comparison on ~50 titles completes in milliseconds
- (+) Threshold is a single constant, easily tunable based on real fixture testing
- (+) No C extension compilation required during installation
- (-) `SequenceMatcher` uses Ratcliff/Obershelp algorithm, not true Levenshtein edit distance — ratio values may differ slightly from Levenshtein for the same string pair
- (-) Threshold may need calibration: 0.6 in Levenshtein terms may map to a different optimal value in SequenceMatcher terms
- (-) Algorithm is character-level, not semantic — "Earthquake hits Japan" and "Tremor felt in Tokyo" would not match despite describing the same event (mitigated by date + country criteria)

## Risk Assessment

| Risk | Probability | Impact | Mitigation | Accepted? |
|------|------------|--------|------------|-----------|
| `SequenceMatcher` 0.6 threshold produces different correlation results than Levenshtein 0.6 | Medium | Medium | Calibrate threshold using real fixture data; adjust if false positive/negative rates are unacceptable | Yes |
| False negatives: similar titles about the same incident fall below 0.6 | Medium | Low | Correlation uses date + country as additional criteria; a title mismatch alone does not prevent correlation if date and country match | Yes |
| False positives: different incidents with similar titles correlate incorrectly | Low | Medium | Date proximity (±1 day) and country overlap provide additional filtering; manual review of `should_report=True` incidents | Yes |
