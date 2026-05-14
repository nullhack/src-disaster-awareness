# IN_20260514_classification_rules — Deterministic Classification, Priority Matrix, and Overrides

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** eol
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | Who are the users? | Backend Developers, Ops Teams, Researchers. |
| Q2 | What does the product do at a high level? | Backend pipeline: fetch → correlate → classify → enrich → store. |
| Q3 | Why does it exist — what problem does it solve? | Provides deterministic, reproducible classification of disaster incidents. |
| Q4 | When and where is it used? | Scheduled CLI tool, backend batch processing. |
| Q5 | Success — what does "done" look like? | Every classification rule has a passing test with named fixtures. Same fixtures always produce same results. |
| Q6 | Failure — what must never happen? | AI must never be used for classification — only for extraction and enrichment. Classification must be deterministic. |
| Q7 | Out-of-scope — what are we explicitly not building? | AI-based classification, real-time classification, human-in-the-loop classification. |

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q8 | How does the classification engine work? | It works on IncidentBundle.records, trying each source's raw_fields in order of reliability: GDACS > WHO > GDELT > DDG-NEWS. It extracts whatever fields are available and falls back to AI for missing fields. |
| Q9 | What does the classify.py module contain? | ClassifyEngine, country groups definitions, priority matrix, level derivation rules per source, and overrides O1-O6. |

## Feature: Country Groups

| ID | Question | Answer |
|----|----------|--------|
| Q10 | What are the country groups? | Three groups: A (25 countries), B (41 countries), and C (rest of world). |
| Q11 | What is Group A? | 25 countries: Afghanistan, Bangladesh, Bhutan, Brunei, Cambodia, China, India, Indonesia, Japan, Laos, Malaysia, Maldives, Myanmar, Nepal, North Korea, Pakistan, Philippines, Singapore, South Korea, Sri Lanka, Taiwan, Thailand, Timor Leste, Vietnam. These are the primary monitoring focus — highest priority for reporting. |
| Q12 | What is Group B? | 41 countries: Asia Pacific 2 (Australia, Fiji, etc.) + Middle East (Bahrain, Cyprus, Iran, Iraq, Jordan, Kuwait, Lebanon, Oman, Palestine, Israel, Qatar, Saudi Arabia, Syria, Turkey, UAE, Yemen) + North Africa (Algeria, Egypt, Morocco, Tunisia). Secondary monitoring focus. |
| Q13 | What is Group C? | Rest of world. Lowest monitoring priority. |

## Feature: Priority Matrix

| ID | Question | Answer |
|----|----------|--------|
| Q14 | How does the priority matrix work? | It combines incident_level (1-4) with country_group (A/B/C) to determine priority (HIGH/MED/LOW) and should_report (true/false). |
| Q15 | What is the full priority matrix? | Group A: Level 4→HIGH/✓, Level 3→HIGH/✓, Level 2→MED/✓, Level 1→MED/✓. Group B: Level 4→HIGH/✓, Level 3→MED/✓, Level 2→MED/✓, Level 1→LOW/✗. Group C: Level 4→HIGH/✓, Level 3→MED/✓, Level 2→LOW/✗, Level 1→LOW/✗. The ✓ means should_report=True, ✗ means should_report=False. |
| Q16 | What are the reporting rules? | Everything in Group A is reported (all ✓). Group B reports levels 2-4. Group C only reports levels 3-4. |

## Feature: Level Derivation (source-specific)

| ID | Question | Answer |
|----|----------|--------|
| Q17 | How is the incident level derived? | It tries the most reliable available source first. Each source has its own derivation rules. |
| Q18 | How does GDACS derive levels? | Green→1, Orange→3, Red→4. There's also a severity bump for Group A countries. |
| Q19 | How does WHO derive levels? | Keyword scan of the content: "pandemic" or "PHEIC"→4, "epidemic" or "widespread"→3, "cluster" or "cases reported"→2, "isolated case"→1, default→2. |
| Q20 | How does GDELT derive levels? | Based on tone value: tone < -5→4, < -3→3, >= 0→1, else→2. |

## Feature: Level Indicators

| ID | Question | Answer |
|----|----------|--------|
| Q21 | What does Level 4 (CRITICAL) mean? | International assistance requested, 300K+ affected, 50+ deaths, multi-state impact, humanitarian crisis declared. |
| Q22 | What does Level 3 (MAJOR) mean? | 100K+ affected, 20-50 deaths, frequent media coverage, ongoing humanitarian crisis. |
| Q23 | What does Level 2 (SIGNIFICANT) mean? | <100K affected, 5-20 deaths, multiple source coverage, regional impact developing. |
| Q24 | What does Level 1 (MINOR) mean? | <50K affected, 0-5 deaths, local coverage only, contained impact. |

## Feature: Overrides (O1-O6)

| ID | Question | Answer |
|----|----------|--------|
| Q25 | What are overrides? | Special flags that mark incidents with additional characteristics beyond the standard level/priority classification. Six overrides from day 1: O1 through O6. |
| Q26 | What is O1 (Humanitarian Crisis)? | Detected by keywords for GDACS, AI for WHO/GDELT. Marks incidents where a humanitarian crisis is declared or evident. |
| Q27 | What is O2 (Multi-Regional)? | GDACS: structured `affectedcountries` field. AI for other sources. Marks incidents affecting multiple countries or regions. |
| Q28 | What is O3 (Likely Development)? | AI-assisted text understanding. Marks incidents likely to escalate or develop further. |
| Q29 | What is O4 (Environmental)? | Deterministic rule: disaster type is in {WF (Wildfire), DR (Drought), FL (Flood)} AND country is in Group A. No AI needed. |
| Q30 | What is O5 (Forecast/Early Warning)? | GDACS: `istemporary` field. AI for other sources. Marks incidents that are forecasts or early warnings rather than current events. |
| Q31 | What is O6 (Singapore/SRC)? | Keyword detection: "Singapore", "SRC", or "Red Cross". Marks incidents relevant to Singapore or the Singapore Red Cross. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Reproducibility | Same fixtures → same classified incidents, every time | Deterministic output | Must |
| QA2 | Testability | Every classification rule has a passing test with named fixture | 100% rule coverage | Must |

---

## Pain Points Identified

- WHO keyword-based level derivation is fragile — new terminology may be missed
- GDELT tone thresholds are approximations — may misclassify edge cases
- Overrides O1, O2, O3, O5 require AI, creating a dependency on AI availability
- 25 countries in Group A is a large set to maintain

## Business Goals Identified

- Deterministic classification ensures reproducibility and auditability
- Three-tier country grouping reflects organizational monitoring priorities
- Priority matrix ensures critical incidents are always reported regardless of source
- Overrides capture nuances that the level/priority system alone cannot express

## Terms to Define (for glossary)

- ClassifyEngine
- Country Group A / B / C
- Priority matrix
- incident_level (1-4: MINOR/SIGNIFICANT/MAJOR/CRITICAL)
- should_report
- Override (O1-O6)
- Humanitarian Crisis (O1)
- Multi-Regional (O2)
- Likely Development (O3)
- Environmental (O4)
- Forecast/Early Warning (O5)
- Singapore/SRC (O6)
- PHEIC (Public Health Emergency of International Concern)
- Severity bump (GDACS Group A)
- Tone (GDELT)

## Action Items

- [ ] Validate WHO keyword lists against real WHO DON content
- [ ] Test GDELT tone thresholds against real GDELT responses
- [ ] Confirm Group A country list is complete and current
- [ ] Verify O4 deterministic rule: disaster type codes {WF, DR, FL}
- [ ] Validate O6 keyword list with stakeholder
