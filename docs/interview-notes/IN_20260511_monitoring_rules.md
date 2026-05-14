# IN_20260511_monitoring_rules — Disaster Monitoring Rules Interview

> **Status:** COMPLETE
> **Interviewer:** PO
> **Participant(s):** Stakeholder (domain expert)
> **Session type:** Domain deep-dive

---

## General

| ID | Question | Answer |
|----|----------|--------|
| Q1 | What are the country groups and why? | Group A (25 Asia Pacific 1 countries): primary focus, closest to Singapore. Group B (41 countries: Asia Pacific 2 + Middle East + North Africa): secondary, regional relevance. Group C (rest of world): tertiary, only critical events. |
| Q2 | How does the 4-level classification work? | Level 4 (Critical): >300K affected or 50+ deaths or humanitarian crisis. Level 3 (Major): >100K affected or frequent news coverage. Level 2 (Significant): <100K affected, regional developing. Level 1 (Minor): <50K affected, limited impact. |
| Q3 | What's the priority matrix? | Maps (level, group) → (HIGH/MEDIUM/LOW, should_report). Level 4 always HIGH and always reported. Level 1 Group A = MEDIUM reported, Level 1 Group C = LOW not reported. See docs/spec/monitoring_rules.md for full table. |
| Q4 | What overrides exist? | Six override criteria: (O1) Humanitarian crisis → force report, minimum HIGH. (O2) Multi-regional → force report, bump priority. (O3) Likely further development → force report. (O4) Environmental/climate → include for A/B. (O5) Forecast/early warning → include for preparedness. (O6) Singapore/SRC connection → force report, minimum MEDIUM. |

---

## Domain Questions

| ID | Question | Answer |
|----|----------|--------|
| Q5 | What are the reporting formats? | Three: Active Incident ("[Disaster type] in [location], [country]"), Forecasted Event ("Forecasted [type] in [location]"), Update ("Update on [event] in [country]"). |
| Q6 | What types of incidents do we track? | Geophysical (earthquake, volcano, tsunami), Meteorological (cyclone, typhoon, severe weather), Hydrological (flood, landslide), Climatological (drought, wildfire), Biological (disease), Technological (industrial accident), Conflict (armed conflict, displacement), Environmental (pollution, contamination). |
| Q7 | What are common classification mistakes? | Over-reporting Group C (most Level 1-2 should be excluded), under-reporting Group A (even Level 1 is worth reporting), missing "likely development" signals, ignoring forecasts, treating all earthquakes equally. |
| Q8 | How does the decision tree work? | Step 1: humanitarian crisis → include. Step 2: Singapore/SRC → include. Step 3-5: apply (level, group) matrix. Step 6: check override criteria. See docs/spec/monitoring_rules.md for full tree. |
| Q9 | What's in the current classification code? | `classification/__init__.py` has COUNTRY_GROUPS dict, PRIORITY_MATRIX dict, RulesLoader class with get_country_group(), get_priority(), should_report(). But Group C is empty set (relies on "not in A or B → C" logic). |
| Q10 | Why is Group C empty in code? | Because any country not found in A or B automatically maps to C. No need to enumerate all remaining countries. |

---

## Quality Attributes

| ID | Attribute | Scenario | Target | Priority |
|----|-----------|----------|--------|----------|
| QA1 | Accuracy | When an incident is classified, the priority matches the matrix | 100% matrix compliance | Must |
| QA2 | Completeness | When Group A Level 4 incident occurs, it is always reported | Zero missed critical incidents | Must |
| QA3 | Noise Reduction | When Group C Level 1 incident occurs, it is excluded | < 5% false positives in reports | Should |

---

## Pain Points Identified

- Rules were in a deleted skill file, not in code or docs
- The classification module has data but no structured decision tree implementation
- Override criteria are not implemented in code at all
- No tests for classification rules

## Business Goals Identified

- Make monitoring rules discoverable and version-controlled
- Implement the full decision tree including overrides
- Ensure classification is testable and deterministic

## Terms to Define

- `Country Group` — geographic priority tier (A/B/C)
- `Incident Level` — severity scale (1-4)
- `Priority` — reporting urgency (HIGH/MEDIUM/LOW)
- `Override` — condition that bypasses the standard priority matrix

## Action Items

- [x] Create `docs/spec/monitoring_rules.md`
- [ ] Implement decision tree with override criteria in classification module
- [ ] Add tests for priority matrix and all override criteria
- [ ] Add incident type enum and country ISO code mapping
