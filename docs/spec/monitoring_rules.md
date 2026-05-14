# Disaster Monitoring Rules: Disaster Surveillance Reporter

> **Status:** BASELINED (2026-05-11)
> Recovered and refined from deleted `disaster-monitor` and `incident-classifier` skills.

---

## Overview

These rules govern how incidents are classified, prioritized, and selected for reporting. The classification logic maps each incident to a (country_group, incident_level, priority) tuple, then the reporting decision tree determines whether it reaches distribution.

---

## Country Groups

### Group A — Asia Pacific 1 (Primary Focus)

25 countries. Highest monitoring priority. Any incident in these countries gets more attention.

| Country | ISO Code |
|---------|----------|
| Afghanistan | AF |
| Bangladesh | BD |
| Bhutan | BT |
| Brunei | BN |
| Cambodia | KH |
| China | CN |
| India | IN |
| Indonesia | ID |
| Japan | JP |
| Laos | LA |
| Malaysia | MY |
| Maldives | MV |
| Myanmar | MM |
| Nepal | NP |
| North Korea | KP |
| Pakistan | PK |
| Philippines | PH |
| Singapore | SG |
| South Korea | KR |
| Sri Lanka | LK |
| Taiwan | TW |
| Thailand | TH |
| Timor Leste | TL |
| Vietnam | VN |

### Group B — Asia Pacific 2 + Middle East + North Africa (Secondary Focus)

41 countries. Moderate monitoring priority.

**Asia Pacific 2:**

| Country | ISO Code |
|---------|----------|
| Australia | AU |
| Fiji | FJ |
| French Polynesia | PF |
| Guam | GU |
| Kazakhstan | KZ |
| Kiribati | KI |
| Kyrgyzstan | KG |
| Mariana Islands | MP |
| Marshall Islands | MH |
| Micronesia | FM |
| Mongolia | MN |
| Nauru | NR |
| New Caledonia | NC |
| New Zealand | NZ |
| Niue | NU |
| Palau | PW |
| Papua New Guinea | PG |
| Samoa | WS |
| Solomon Islands | SB |
| Tajikistan | TJ |
| Tonga | TO |
| Turkmenistan | TM |
| Tuvalu | TV |
| Uzbekistan | UZ |
| Vanuatu | VU |
| Wallis and Futuna | WF |

**Middle East:**

| Country | ISO Code |
|---------|----------|
| Bahrain | BH |
| Cyprus | CY |
| Iran | IR |
| Iraq | IQ |
| Jordan | JO |
| Kuwait | KW |
| Lebanon | LB |
| Oman | OM |
| Palestine | PS |
| Israel | IL |
| Qatar | QA |
| Saudi Arabia | SA |
| Syria | SY |
| Turkey | TR |
| UAE | AE |
| Yemen | YE |

**North Africa:**

| Country | ISO Code |
|---------|----------|
| Algeria | DZ |
| Egypt | EG |
| Morocco | MA |
| Tunisia | TN |

### Group C — Rest of World (Tertiary Focus)

All remaining countries. Lowest monitoring priority.

### Classification Rule

If a country is not found in Group A or Group B, it is automatically assigned to Group C.

---

## Incident Levels

### Level 4 — CRITICAL (Must Report)

**Indicators (any ONE sufficient):**
- International assistance requested
- Singapore news publishing daily updates on the event
- More than 300,000 people affected
- 50+ confirmed deaths
- More than one state/province affected
- Humanitarian crisis officially declared

### Level 3 — MAJOR (Should Report)

**Indicators (any ONE sufficient):**
- Singapore news publishing frequent updates (multiple in past week)
- More than 100,000 people affected
- Significant regional impact
- Government-declared emergency

### Level 2 — SIGNIFICANT (Consider Reporting)

**Indicators (any ONE sufficient):**
- Singapore news publishing more than one update
- Less than 100,000 people affected
- Multiple source coverage
- Regional impact developing

### Level 1 — MINOR (Optional Reporting)

**Indicators (any ONE sufficient):**
- No Singapore news coverage, but local news reports exist
- Less than 50,000 people affected
- Limited impact expected
- Early warning / emerging situation

---

## Priority Matrix

Maps (incident_level, country_group) → (priority, should_report).

| Level | Group A | Group B | Group C |
|-------|---------|---------|---------|
| **4** | HIGH ✓ | HIGH ✓ | HIGH ✓ |
| **3** | HIGH ✓ | MEDIUM ✓ | MEDIUM ✓ |
| **2** | MEDIUM ✓ | MEDIUM ✓ | LOW ✗ |
| **1** | MEDIUM ✓ | LOW ✗ | LOW ✗ |

✓ = should_report = true, ✗ = should_report = false

**Summary:**
- Level 4: Always report regardless of group
- Level 3: Always report, but Group A gets HIGH priority
- Level 2: Report for Groups A and B, skip Group C
- Level 1: Only report for Group A

---

## Override Criteria

The following situations override the standard priority matrix and force `should_report = true`:

### O1: Humanitarian Crisis
Incident is officially declared a humanitarian crisis by UN, government, or recognized aid organization. → Force `should_report = true`, minimum priority HIGH.

### O2: Multi-Regional Impact
Incident affects multiple countries or spans a large geographic area. → Force `should_report = true`, bump priority by one level.

### O3: Likely Further Development
Initial damage reports suggest the situation is still developing (e.g., "immediate" status, aftershock risk, ongoing rainfall). → Force `should_report = true` for awareness.

### O4: Environmental/Climate Awareness
Emerging environmental threats with long-term implications (air quality, climate events, pollution alerts). → Include for awareness if in Group A or B.

### O5: Forecast/Early Warning
Event is forecasted but not yet occurred (cyclone track, flood prediction, disease spread model). → Include for preparedness.

### O6: Singapore/SRC Connection
Singapore is mentioned in coverage OR Singapore Red Cross (SRC) is involved. → Force `should_report = true`, priority at least MEDIUM.

---

## Reporting Formats

### Active Incident
```
[Disaster type] in [regions/provinces/states], [country]
[Link]
```
Example: `Earthquake in northern Afghanistan` + URL

### Forecasted Event
```
Forecasted [disaster type] in [regions/provinces/states], [country]
[Link]
```
Example: `Forecasted continuous rain in Sarawak, Malaysia` + URL

### Update on Ongoing Incident
```
Update on [disaster event/type] in [country]
[Link]
```
Example: `Update on floods in Aceh, Indonesia` + URL

---

## Inclusion/Exclusion Decision Tree

```
1. Is it a humanitarian crisis?
   → YES: INCLUDE (override, HIGH priority)

2. Is Singapore or SRC mentioned?
   → YES: INCLUDE (override, at least MEDIUM)

3. Is it in Group A?
   → Level 4 or 3: INCLUDE (HIGH)
   → Level 2: INCLUDE (MEDIUM)
   → Level 1: INCLUDE (MEDIUM)

4. Is it in Group B?
   → Level 4: INCLUDE (HIGH)
   → Level 3: INCLUDE (MEDIUM)
   → Level 2: INCLUDE (MEDIUM)
   → Level 1: EXCLUDE

5. Is it in Group C?
   → Level 4: INCLUDE (HIGH)
   → Level 3: INCLUDE (MEDIUM)
   → Level 2 or 1: EXCLUDE

6. Override checks (apply regardless of above):
   → Multi-regional impact? INCLUDE
   → Likely further development? INCLUDE
   → Forecast/early warning? INCLUDE (for Groups A/B)
   → Environmental/climate awareness? INCLUDE (for Groups A/B)
```

### Reports to INCLUDE
- Humanitarian crisis declaration
- Previously reported incident with new developments
- Initial damage reports (likely further development)
- Multiple provinces/states affected
- Environmental/climate awareness events
- SRC involvement or Singapore connection

### Reports to EXCLUDE
- Low potential for humanitarian impact
- Contained incident with clear resolution path
- No tsunami expected after earthquake (unless Group A)
- Isolated incident, minimal affected population
- Low-impact earthquakes (offshore, deep, <4.5 magnitude)

---

## Incident Types

| Category | Types |
|----------|-------|
| Geophysical | Earthquake, Volcano, Tsunami |
| Meteorological | Cyclone, Hurricane, Typhoon, Tornado, Dust Storm, Severe Weather |
| Hydrological | Flood, Flash Flood, Landslide, Avalanche |
| Climatological | Drought, Extreme Temperature, Wildfire |
| Biological | Disease Outbreak, Epidemic, Pandemic |
| Technological | Industrial Accident, Hazmat Release, Infrastructure Failure |
| Conflict | Armed Conflict, Civil Unrest, Mass Displacement |
| Environmental | Air Pollution, Water Contamination, Desertification |

---

## Common Mistakes to Avoid

1. **Over-reporting Group C** — Most Group C Level 1-2 incidents should be excluded
2. **Under-reporting Group A** — Even Level 1 incidents in Group A are worth reporting
3. **Missing "likely development" signals** — Initial reports often understate severity
4. **Ignoring forecasts** — Early warnings are valuable for preparedness
5. **Treating all earthquakes equally** — Depth, magnitude, and location matter
6. **Forgetting disease incidents** — ProMED alerts in Group A countries should be monitored
7. **Duplicate reporting** — Same event from multiple sources should be deduped, not reported separately

---

## Changes

| Date | Source | Change | Reason |
|------|--------|--------|--------|
| 2026-05-11 | Specification recovery | Created from deleted disaster-monitor and incident-classifier skills | Domain knowledge at risk of loss |
