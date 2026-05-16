# PM_20260515_beehave_literal_pollution: Test bodies polluted with dummy assignments, tautological assertions, and Gherkin step docstrings

## Failed At

Every TDD cycle across 14 features — SE agents write tests with dummy code patterns (lines with zero behavioral value) to satisfy beehave's literal-extraction traceability contract.
Patterns observed:

1. `_ = "<source>"  # noqa: F841` — dummy assignment for Scenario Outline placeholder literals (18+ files)
2. `assert "<source>" == "<source>"` — tautological assertions (3+ files, incident_identity)
3. `_lit_10 = "10"  # beehave traceability` — named dummy assignments for plain numeric literals (3+ files, ai_classifier)
4. `"""Given a bundle missing "<field>"..."""` — docstring copies of Gherkin steps that serve as literal carriers (20+ files)

## Root Cause

**beehave requires Python string literals from .feature file steps to appear verbatim as string constants in the test function body.** This is how beehave verifies traceability: it extracts literals like `"<source>"` or `"10"` from the Given/When/Then steps in the .feature file, then checks those exact strings appear as Python string constants in the corresponding test file.

For **plain Examples** with concrete values, this works naturally — the literal `"GDACS"` from a Then step appears in `assert result == ["GDACS"]`.

For **Scenario Outlines** with `<placeholder>` parameters, it fails. The placeholder string `"<source>"` has no meaningful role in the test body — the parameter `source` (without brackets) carries the actual value. Agents resorted to increasingly creative dummies to satisfy the requirement: `_ = "<source>"`, `assert "<source>" == "<source>"`, embedding in docstrings.

**This is NOT an agent discipline problem.** The agents faithfully implemented the constraint. The constraint itself — requiring placeholder strings to appear as Python string literals — forces dummy code.

## Missed Gate

**No gate catches this.** Spec-review checks cross-document consistency. Review-gate checks design principles (OC-1, YAGNI, KISS etc.) but beehave's literal check runs at test collection time via pytest-beehave. If agents remove the dummies, `beehave_missing_literal` failures block the CI. If agents add the dummies, the tests pass but code is polluted.

The closed loop: beehave requires literals → agent adds dummies → dummies satisfy beehave → no test failure → no gate triggers → reviewer skips "working" code → pollution accumulates.

## Fix

**Process fix**: Accept that `_BEEHAVE_LITERALS = ["<source>", "<raw_date>"]` is a legitimate requirement of the beehave framework, not a code smell. Standardize on a single, minimal pattern per test file:

```python
# Literal traceability for Scenario Outline placeholders
_BEEHAVE_LITERALS = ["<source>", "<raw_date>", "<date_component>"]
```

**Prohibited patterns** (in this file or any future file):
- `_ = "<literal>"` — silent discards, F841 violations
- `assert "<literal>" == "<literal>"` — tautologies
- `"""Given ... When ... Then ..."""` — Gherkin in docstrings, not a docstring's purpose
- `_lit_N = "N"` — meaningless variable names leaking into scope

**Preferred pattern** (one per test file with Scenario Outline placeholders):
```python
_BEEHAVE_LITERALS = ["<placeholder_1>", "<placeholder_2>"]
```
Placed at module level after imports but before test functions. This is self-documenting, F841-free, and satisfies beehave's literal check.

**For plain Example tests** with concrete literals (e.g. `"GDACS"`, `"10"`, `"Japan"`): the literals MUST appear in real assertions, never in dummy assignments. If a test uses `_ = "10"` instead of `assert thing == "10"`, the test is incomplete.

**Documentation fix**: Add this rule to the `AGENTS.md` Golden Rules file under a new "Test Discipline" section, so all agents (SE, SA, PO) know the single correct pattern.

## Restart Check

1. Run `grep -rn '_ = "' tests/features/ --include="*.py" | grep -v noqa`: should return zero matches
2. Run `grep -rn 'assert "<' tests/features/ --include="*.py"`: should return zero matches (tautologies)
3. Run `grep -rn 'Given\|When\|Then' tests/features/ --include="*.py" | grep '"""'`: should return zero matches (step docstrings)
4. Run `grep -rn 'BEEHAVE_LITERALS' tests/features/ --include="*.py"`: shows only valid module-level list constants
5. `beehave check` passes on all features
