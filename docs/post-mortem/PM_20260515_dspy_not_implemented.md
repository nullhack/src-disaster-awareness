# PM_20260515_dspy_not_implemented: DSPy required but never imported in AI agents

## Failed At

ai_extractor + ai_classifier TDD (red→green) — SE: "Implemented ExtractorAgent and ClassifierAgent using AIProvider.chat() + json.loads() with hand-written JSON instructions in text prompts. DSPy was never imported, never configured, never used. Docstrings claim 'DSPy-powered' but implementation has zero `import dspy`."

## Root Cause

`review-gate` for ai_extractor and ai_classifier checked only Object Calisthenics nesting (OC-1), feature-to-test traceability, and functional lint — it never verified architectural spec compliance against production code. DSPy is referenced **18 times across 7 specification documents** (domain_spec.md:470,508,510,513,516; product_definition.md:12,65,66,137,148,162; glossary.md:15,330,339,345; ai_extractor.feature:4; ai_classifier.feature:6; ai_provider.feature:8), yet zero `import dspy` statements exist in production code. The review-gate skill's Tier 1 "Domain Spec Alignment" check was exclusively entity/invariant matching, not protocol/dependency verification. The reviewer checked *what entities exist* but never verified *how agents talk to AI*.

## Missed Gate

**review-gate → Tier 1: Design Review → Criterion 2: ADR Compliance / Spec Alignment**

All four review-gate passes for ai_extractor and ai_classifier returned PASS without checking whether `domain_spec.md:508-510` (DSPy Integration section: "Both Extractor and Classifier agents use DSPy typed signatures. DSPy handles prompt engineering, output parsing, and retry logic.") was reflected in the implementation. The reviewer verified that entities matched, invariants held, and tests passed — but never ran `grep "import dspy"` against the production source.

Additionally, the `accept-feature` skill's #7 check ("Verify every stakeholder Q&A from interview notes maps to either a passing test or an explicit stakeholder deferral") should have caught this: `IN_20260514_ai_strategy.md:Q5` explicitly asked about DSPy integration for structured output. This Q&A was never traced during acceptance.

## Fix

1. **Review-gate Tier 1 must include a protocol/dependency verification pass.** After "ADR Compliance," add a check: for every technology dependency listed in `product_definition.md`'s Technology Stack and Dependencies tables, verify it is imported and exercised in the production code under review. A single-command check (`grep -rn "import <dep>\|from <dep>" <pkg>/`) catches dormant dependencies.

2. **Accept-feature must trace every interview Q&A topic that names a specific technology dependency.** The `IN_20260514_ai_strategy.md:Q5` (DSPy) and `IN_20260514_ai_strategy.md:Q6` (Classifier Agent) Q&As both reference DSPy — neither was traced to a passing test or an explicit stakeholder deferral. The acceptance traceability matrix (check #8) must explicitly flag untraced technology Q&As rather than silently omitting them.

3. **Rewrite `ai/extractor.py` and `ai/classifier.py`** to use DSPy typed signatures per domain_spec.md:508-516. Replace manual `json.loads()` + `AIProvider.chat()` with `dspy.Predict(dspy.Signature(...))` backed by a DSPy LM adapter wrapping the pluggable AIProvider. Update the 14 BDD tests (7 extractor + 7 classifier) to verify DSPy signature output structures rather than raw JSON strings.

## Restart Check

Before re-entering ai_extractor or ai_classifier TDD, the SA must verify:
1. `import dspy` succeeds with the pinned dependency
2. Both `ExtractAgent` and `ClassifierAgent` module-level constants are `dspy.Signature` subclasses
3. `dspy.configure(lm=...)` is called at agent init with a LM adapter wrapping the pluggable AIProvider
4. All 14 existing tests still define the same behavioral contracts — only the prompting mechanism changes, not the acceptance criteria
