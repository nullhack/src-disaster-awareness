# ADR_20260514_sequential_pipeline

## Status

Accepted

## Context

DSR processes disaster data from 3 primary sources (GDACS, WHO DON, GDELT) through 7 pipeline steps: Fetch → Correlate → Initial Classify → Supplementary Search → AI Enrich → Override Re-evaluation → Store. The quality attributes rank Reproducibility (#1) and Reliability (#2) above Performance (#5, #6). Each step has a data dependency on the previous step's output: correlation needs raw records, classification needs correlated bundles, supplementary search needs classification results to know which bundles lack context, enrichment needs classified bundles, re-evaluation needs enriched data, and storage needs fully processed bundles. The tool runs as a single CLI invocation every ~6 hours, processing ~50 incidents per run.

The forces at play are: (1) steps must execute in a fixed order because of data dependencies, (2) the tool is a single-process CLI with no concurrent users, (3) Reproducibility demands that the same input always produces the same output in the same order, (4) simplicity reduces bugs and improves testability.

## Interview

| Question | Answer |
|---|---|
| Should steps run concurrently where possible? | No — data dependencies prevent meaningful parallelism, and concurrency would harm reproducibility |
| Is there a latency SLA that requires streaming? | No — batch processing every ~6 hours with a 5-minute target is generous |
| Could steps be split into separate deployable units? | No — single CLI invocation, single process, no operational benefit |

## Decision

Use a sequential pipeline architecture where `pipeline.py` orchestrates 7 steps in fixed order, each completing before the next begins, with all data passed as Python objects in memory.

## Reason

Sequential execution matches the inherent data dependencies between steps, maximises reproducibility (deterministic ordering), and minimises complexity (no concurrency primitives, no message queues, no coordination logic) for a single-process batch CLI tool.

## Alternatives Considered

- **Streaming/event-driven pipeline**: Steps communicate via events or message queues. Rejected because the fixed data dependency chain means events would fire in the same order every time anyway, adding complexity (event schemas, error handling in async context, debugging difficulty) with zero benefit. Debugging a streaming pipeline is significantly harder than stepping through sequential code.
- **Actor model (e.g., Thespian, dramatiq)**: Each step is an independent actor processing messages. Rejected because actors add a concurrency framework dependency, require message serialization, and complicate error propagation — all for a single-threaded batch tool with no concurrency benefit.
- **Microservices**: Each step deployed as a separate service. Rejected because the operational overhead (service orchestration, network calls, deployment complexity) is disproportionate for a cron-scheduled CLI tool running every 6 hours.

## Consequences

- (+) Deterministic execution order guarantees reproducibility (QA #1)
- (+) Simple error handling: if any step fails, the pipeline can report which step and why
- (+) Easy to test: each step is a pure function call with inputs and outputs
- (+) No concurrency bugs, no race conditions, no deadlocks
- (+) All data fits in memory for typical runs (~50 incidents ≈ ~200 records ≈ ~5 MB)
- (-) Steps cannot overlap; total latency is the sum of all step latencies (~90s for AI, ~5s for deterministic steps)
- (-) Scaling beyond ~1000 incidents per run may require memory management strategies
- (-) Adding parallel steps (e.g., fetching from multiple sources concurrently within Step 1) requires explicit thread/async code within a step

## Risk Assessment

| Risk | Probability | Impact | Mitigation | Accepted? |
|------|------------|--------|------------|-----------|
| Memory pressure with large incident volumes (>1000 bundles) | Low | Medium | Profile memory at 500/1000/2000 bundles; add chunking if needed | Yes |
| Step 1 fetch latency sum exceeds acceptable threshold (3 sources × slow API) | Medium | Low | httpx connection pooling and per-adapter timeout (30s); sources return [] on timeout | Yes |
| Future requirement for parallel step execution forces re-architecture | Low | Medium | Each step's interface (input type → output type) is already decoupled; parallelisation can be added within `pipeline.py` without changing step implementations | Yes |
