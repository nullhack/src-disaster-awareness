---
name: incident-classifier
description: Rules and methodology for classifying disaster incidents by priority level, country group, and reporting urgency
compatibility: "1.0.0+"
metadata:
  category: monitoring
  difficulty: intermediate
  type: incident-classification
---

# Incident Classifier Skill

Systematic methodology for classifying disaster and health incidents by priority, geographic group, and reporting urgency.

## Quick Reference: Priority Matrix

```
              Group A      Group B      Group C
           (Asia Pac 1) (Asia Pac 2)  (Rest)
Level 4      HIGH         HIGH        HIGH
Level 3      HIGH        MEDIUM      MEDIUM
Level 2     MEDIUM       MEDIUM       LOW
Level 1     MEDIUM        LOW         LOW
```

## Country Group Definitions

### Group A: Asia Pacific 1 (PRIMARY FOCUS)
**25 countries - Highest monitoring priority**

South Asia:
- Afghanistan, Bangladesh, Bhutan, India, Maldives, Nepal, Pakistan, Sri Lanka

Southeast Asia:
- Brunei, Cambodia, Indonesia, Laos, Malaysia, Myanmar, Philippines, Singapore, Thailand, Timor Leste, Vietnam

East Asia:
- China, Japan, North Korea, South Korea, Taiwan

**Why Group A matters:**
- Highest population density and disaster frequency
- Greatest humanitarian impact potential
- Closest geographic proximity to key monitoring hubs
- Highest likelihood of SRC involvement

### Group B: Asia Pacific 2 + Middle East & North Africa (SECONDARY FOCUS)

**Asia Pacific 2 (13 countries):**
Australia, Fiji, French Polynesia, Guam, Kazakhstan, Kiribati, Kyrgyzstan, Mariana Islands, Marshall Islands, Micronesia, Mongolia, Nauru, New Caledonia, New Zealand, Niue, Palau, Papua New Guinea, Samoa, Solomon Islands, Tajikistan, Tonga, Turkmenistan, Tuvalu, Uzbekistan, Vanuatu, Wallis and Futuna

**Middle East (14 countries):**
Bahrain, Cyprus, Iran, Iraq, Jordan, Kuwait, Lebanon, Oman, Palestine/Israel, Qatar, Saudi Arabia, Syria, Turkey, United Arab Emirates, Yemen

**North Africa (4 countries):**
Algeria, Egypt, Morocco, Tunisia

**Why Group B matters:**
- Second-tier humanitarian concern
- Moderate disaster frequency
- Some geographic proximity to Group A
- Potential for SRC regional coordination

### Group C: Rest of Africa, Europe & Americas (TERTIARY FOCUS)

**All remaining countries in:**
- Sub-Saharan Africa (45+ countries)
- Europe (50+ countries including Russia)
- North/Central/South America and Caribbean (35+ countries)

**Why Group C matters:**
- Monitored for exceptional/Level 4 events
- Lower SRC operational priority
- Global awareness value
- Included if international significance

## Incident Level Classification

### Level 4: CRITICAL - MUST REPORT
**Report to All Audiences**

**Defining Indicators (Any ONE is sufficient):**

🔴 **Scale & Impact:**
- International assistance explicitly requested
- More than 300,000 people affected
- Death toll of 50+ confirmed deaths
- More than one state/province affected (in same country)

🔴 **Media Coverage:**
- SGP news source publishes daily updates
- Multiple major international news agencies covering
- Breaking news alerts

🔴 **Status:**
- Humanitarian crisis officially declared
- Emergency state declared by national government
- International humanitarian appeal issued

🔴 **Examples:**
- 2025 Iran floods: 25 provinces affected, 8+ deaths, daily coverage
- Taiwan 6.1 magnitude earthquake: regional significance, multiple provinces potential impact
- Major humanitarian crisis in Gaza/Palestine with international aid appeals

**Classification Rule:** If ANY indicator is met → Level 4 → ALWAYS REPORT

**Action:** Immediate report, escalate to priority channels, begin daily monitoring

---

### Level 3: MAJOR - SHOULD REPORT
**Report to Most Audiences**

**Defining Indicators (2+ should be present):**

🟠 **Scale & Impact:**
- More than 100,000 people affected
- Significant death toll (20-50)
- Regional impact starting to emerge
- Multiple provinces/states potentially at risk

🟠 **Media Coverage:**
- SGP news source publishes frequent updates (several over past week)
- Regional news agencies covering extensively
- Sustained media attention

🟠 **Status:**
- Ongoing humanitarian crisis (not yet declaration)
- Major emergency declared
- Regional coordination efforts initiated

🟠 **Examples:**
- Aceh flood: Ongoing updates about government response, water truck deployment
- Regional earthquake: Potential for broader impact assessment
- Disease outbreak: Multiple reported cases, investigation ongoing

**Classification Rule:** If 2+ indicators present → Level 3 → Report according to group priority

**Action:** Include in regular monitoring, document updates, flag if escalating

---

### Level 2: SIGNIFICANT - CONSIDER REPORTING
**Report Selectively by Group**

**Defining Indicators (2+ should be present):**

🟡 **Scale & Impact:**
- Less than 100,000 people affected
- Moderate impact (5-20 deaths)
- Single state/province primarily affected
- Localized but noteworthy impact

🟡 **Media Coverage:**
- SGP news source publishes more than one update
- Local/regional news coverage
- Story getting sustained but not intensive coverage

🟡 **Status:**
- Emergency response initiated
- Assessment ongoing
- Further development possible

🟡 **Examples:**
- Minor earthquake with damage assessment ongoing
- Local flooding with relief efforts beginning
- Emerging disease case with investigation starting

**Classification Rule:** If 2+ indicators present → Level 2 → Report based on country group

**Action:**
- Group A: Include in regular reports (MEDIUM priority)
- Group B: Include if notable (MEDIUM priority)
- Group C: Include only if exceptional (LOW priority)

---

### Level 1: MINOR - OPTIONAL REPORTING
**Report Only for Awareness in Group A**

**Defining Indicators:**

🟢 **Scale & Impact:**
- Less than 50,000 people affected
- Few deaths (0-5)
- Isolated incident, contained impact
- Unlikely to require international assistance

🟢 **Media Coverage:**
- No coverage in SGP/major international news
- Only local/country-specific news reporting
- Limited story traction

🟢 **Status:**
- Initial reports only
- Early warning/emerging situation
- Low escalation probability

🟢 **Examples:**
- Small earthquake offshore with no tsunami
- Minor avalanche in isolated mountain region (5.3 magnitude in Bolivia)
- Limited localized flooding with quick resolution

**Classification Rule:** If indicators met → Level 1 → Report selectively

**Action:**
- Group A: Include for awareness (MEDIUM priority) - track for escalation
- Group B: Exclude or track silently (LOW priority)
- Group C: Exclude (LOW priority)

---

## Special Cases and Override Criteria

### Case 1: Humanitarian Crisis Declaration
**Override Level:** Always HIGH priority, regardless of level

**Examples:**
- "Official humanitarian crisis declared in [country]"
- "UN issues international humanitarian appeal"
- "Humanitarian situation deteriorating rapidly"

**Action:** Report immediately regardless of country group or incident level

---

### Case 2: Likely Further Development
**Override:** Elevate one priority level if development likely

**Indicators:**
- "No immediate reports of damage" (further assessment needed)
- "Impact assessment ongoing"
- "Initial figures suggest..." (preliminary data)
- Warning/forecast with high probability

**Example:** Taiwan 6.1 earthquake with no immediate damage reports → Level 2 becomes Level 3 (requires monitoring for actual impact)

**Action:** Include in reports with flag: "[Monitor for updates]"

---

### Case 3: Widespread/Multi-Regional Impact
**Override:** Elevate priority if affecting multiple provinces/states/countries

**Indicators:**
- "affecting X provinces" (X > 1)
- "cross-border impact"
- "regional scale event"
- "multiple states impacted"

**Examples:**
- Cyclone affecting multiple states
- Disease outbreak across several provinces
- Air pollution affecting multiple countries

**Action:** Always include, elevate one priority level

---

### Case 4: Environmental/Climate/Long-term Awareness
**Priority:** Include if regional/widespread

**Examples:**
- "Air pollution in Thailand affecting regional air quality"
- "Global economic impact of disasters: $220 billion in 2025"
- "Climate change impact study on disaster frequency"

**Action:**
- Include if affecting Group A or widespread
- Include if long-term strategic importance
- Can exclude if purely academic/future-focused

---

### Case 5: Forecast/Early Warning
**Priority:** Include for awareness, lower urgency

**Indicators:**
- "Forecasted continuous rain in [region]"
- "Weather warning issued for [area]"
- "Disease outbreak potential in [region]"

**Action:**
- Include all forecasts in Group A areas
- Include significant forecasts in Group B/C
- Mark as "[Forecast]" to distinguish from active incidents
- Update as forecast develops or resolves

---

## Decision Tree: Quick Classification

```
START: New incident identified

Step 1: Determine Country Group
├─ Asia Pacific 1 → Group A
├─ Asia Pacific 2 / MENA → Group B
└─ Other → Group C

Step 2: Check for Level 4 Indicators
├─ International assistance requested? → LEVEL 4
├─ 300,000+ affected? → LEVEL 4
├─ 50+ deaths? → LEVEL 4
├─ Multi-state/province impact? → LEVEL 4
├─ Daily SGP coverage? → LEVEL 4
├─ Humanitarian crisis declared? → LEVEL 4
└─ NO → Continue to Step 3

Step 3: Check for Level 3 Indicators
├─ 100,000+ affected? → LEVEL 3
├─ 20-50 deaths? → LEVEL 3
├─ Frequent SGP coverage? → LEVEL 3
├─ Ongoing humanitarian crisis? → LEVEL 3
└─ NO → Continue to Step 4

Step 4: Check for Level 2 Indicators
├─ 50,000-100,000 affected? → LEVEL 2
├─ 5-20 deaths? → LEVEL 2
├─ Multiple SGP updates? → LEVEL 2
├─ Further development likely? → LEVEL 2
└─ NO → LEVEL 1

Step 5: Determine Reporting Priority
├─ Group A + Level 4 → HIGH (ALWAYS REPORT)
├─ Group A + Level 3 → HIGH (ALWAYS REPORT)
├─ Group A + Level 2 → MEDIUM (REPORT)
├─ Group A + Level 1 → MEDIUM (REPORT - track)
├─ Group B + Level 4 → HIGH (ALWAYS REPORT)
├─ Group B + Level 3 → MEDIUM (REPORT)
├─ Group B + Level 2 → MEDIUM (REPORT if notable)
├─ Group B + Level 1 → LOW (EXCLUDE)
├─ Group C + Level 4 → HIGH (ALWAYS REPORT)
├─ Group C + Level 3+ → MEDIUM (REPORT)
└─ Group C + Level 2- → LOW (EXCLUDE unless exceptional)

Step 6: Check Special Cases
├─ Humanitarian crisis? → ESCALATE
├─ Multi-regional? → ELEVATE
├─ Further development likely? → FLAG
└─ Forecast? → MARK AS FORECAST

FINAL: Report according to priority level
```

## Data Structure for Classification

```json
{
  "incident_id": "unique identifier",
  "incident_name": "name of disaster",
  "classification": {
    "country": "country name",
    "country_group": "A / B / C",
    "incident_level": "1 / 2 / 3 / 4",
    "priority": "HIGH / MEDIUM / LOW",
    "report": true/false
  },
  "indicators": {
    "affected_population": number,
    "death_toll": number,
    "provinces_affected": number,
    "assistance_requested": boolean,
    "sgp_coverage": "daily / frequent / multiple / single / none",
    "humanitarian_crisis": boolean,
    "further_development_likely": boolean,
    "multi_regional": boolean
  },
  "classification_rationale": "explanation of classification decision",
  "report_channel": "WhatsApp / Timeline / Both / None",
  "classified_date": "YYYY-MM-DD",
  "classified_by": "classifier name/ID"
}
```

## Common Mistakes to Avoid

❌ **Mistake 1:** Over-reporting Group C incidents
- Only report Level 4 or exceptional cases
- Don't include routine low-impact incidents

❌ **Mistake 2:** Under-reporting Group A incidents
- Even Level 1 incidents should be monitored
- Track potential escalation

❌ **Mistake 3:** Ignoring forecast indicators
- Include early warnings and forecasts
- These allow proactive monitoring

❌ **Mistake 4:** Missing "likely development" indicators
- Initial damage reports need follow-up
- Assessment still ongoing = continue monitoring

❌ **Mistake 5:** Misinterpreting casualty numbers
- Confirm deaths vs. injuries
- Preliminary numbers often change
- Use latest verified data

## Tips for Accurate Classification

✅ **Cross-check sources**: Use 2+ independent sources for casualty/impact numbers

✅ **Check official status**: Government declarations trump estimates

✅ **Track history**: Previous incidents in same area may affect classification

✅ **Consider timing**: Hours-old reports may be preliminary; wait for updates

✅ **Note uncertainty**: If unsure about level, escalate rather than downgrade

✅ **Document rationale**: Record why you classified as you did

✅ **Review daily**: Monitor for escalation/de-escalation over time

✅ **Use latest data**: Always update classification as new information emerges
