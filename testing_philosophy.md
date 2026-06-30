# Testing Philosophy

This document is a philosophy to guide development. It describes *how* we test,
not *what* the system is. It deliberately does not depend on any specific
schema, source, library, or implementation choice. When the implementation
changes, this document does not.

## Tests are the spec

The tests *are* the specification. Every test represents a real requirement of
this system; if a requirement isn't expressed in a test, it isn't a
requirement, and if a test asserts something, that assertion *is* the spec. We
do not keep a parallel universe of prose specs that drifts away from reality.

Corollary — **do not test the framework.** A test that only proves an ORM can
insert a row, or that a constraint the framework enforces for free fires on
cue, is testing someone else's software, not our spec. It adds no protection
and locks in nothing we decided. Every test must express a contract of *this*
system — a shape, a relationship, or a behavior that exists because we chose
it.

Corollary — **pending specs skip, they don't fail.** When a test specifies
behavior that is not yet implemented, it is marked
`@pytest.mark.skip(reason="not implemented")`, placed first on the test. The
suite stays clean (passing + skipped) while advertising every contracted
behavior that is still owing. The skip is removed the moment the implementation
lands, turning the test green.

## What we test: integration and E2E only

We do not write exhaustive unit tests for every function, helper, or
dataclass. We test the seams that matter — where data crosses a boundary or
transforms between representations:

- A source adapter turns a real-shaped external response into our internal
  records.
- The pipeline turns raw source data into persisted state.
- A read-side consumer turns stored records into its output.
- The entrypoint, invoked for real, drives the whole chain end to end.

Trivial code (pure wiring, pass-throughs) is never tested in isolation — it is
exercised for free by the integration tests that use it.

## Data-layer tests: structure we chose, not plumbing we inherited

When a test touches the persistence layer, it verifies the structure *we*
decided — the tables and columns that must exist, the keys, the uniqueness, the
nullability, the relationships between tables. These are our contracts, so they
belong in tests.

It does **not** insert, select, or round-trip rows to "prove the ORM works."
That is testing the framework. Quantitative shape (how many records a source
yields, how they distribute) belongs to the source and pipeline tests, where it
is a real spec.

## Persistence is never mocked

The persistence layer is the foundation every consumer reads from, so it is
always real. Tests build a real, throwaway database (a temporary file under
`tmp_path`, created and disposed per test). We never mock the engine, the
session, or the data-access layer. If a test needs pre-populated data, it
inserts real records into the real temporary database.

## Fixtures are captured reality

Response fixtures are captured by **actually calling each external source once,
for each distinct possibility** — every representative response shape the
source can return in the real world. One captured fixture per possibility,
committed to the repo.

These fixtures are the source of truth for "what does this source actually
return." Re-capture only when an upstream shape changes; treat that change as a
real event and update the affected tests.

## Mock at the boundary, not beneath it

We mock exactly one place per external dependency — **the last mile before
bytes leave the process:**

- **HTTP calls** → intercepted at the transport level, returning a captured
  real fixture.
- **Third-party SDKs / scrape libraries** → intercepted at the SDK call that
  performs the network I/O.
- **Email** → mock the send.
- **Any external API client** → mock the client object.

Everything *after* the mock runs as real production code. The point is the
bug-catching power of integration tests against real external shapes, without
network flakiness, rate limits, credentials, or cost.

## No network in CI

The suite runs fully offline, deterministic, and fast. No live calls, no
credentials, no sleeps, no retries against real services. Network access
happens exactly once, by hand, at fixture-capture time.

## Coverage is a side effect, not a target

There is no minimum coverage percentage. Success is measured by whether the
real value chains are exercised, not by a number. Chasing 100% produces
pedantic tests that lock in implementation details and resist refactoring.

## Clock and filesystem

- **Clock** — frozen at a known UTC instant wherever timestamps or date-based
  filtering are asserted, so tests are deterministic.
- **Filesystem** — real `tmp_path` directories. We do not mock `open`/`Path`.
