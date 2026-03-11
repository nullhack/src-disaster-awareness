---
name: disaster-monitor
description: Standardized formats and incident grouping rules for disaster and health emergency monitoring
compatibility: "1.0.0+"
metadata:
  category: monitoring
  difficulty: intermediate
  type: disaster-monitoring
---

# Disaster Monitor Skill

Standardized reporting formats and incident classification for consistent disaster awareness monitoring across all data sources.

## Incident Report Formats

### Format 1: Active Incident Report
```
[Disaster type] in [regions/provinces/states], [country]
[Link]
```

**Example:**
```
Earthquake in northern Afghanistan
https://www.aljazeera.com/gallery/2025/11/3/deadly-earthquake-hits-northern-afghanistan
```

### Format 2: Forecasted Event Report
```
Forecasted [disaster type] in [regions/provinces/states], [country]
[Link]
```

**Example:**
```
Forecasted continuous rain in Sarawak, Malaysia
https://www.thestar.com.my/news/nation/2025/12/31/metmalaysia-warns-of-severe-weather-in-sarawak
```

### Format 3: Update on Ongoing Incident
```
Update on [disaster event/name/type] in [country]
[Link]
```

**Example:**
```
Update on floods in Aceh, Indonesia
https://en.antaranews.com/news/397840/indonesia-sends-25-water-trucks-to-aceh-after-floods-landslides
```

## Incident Categorization

### By Geographic Region

**Group A - Asia Pacific 1 (HIGH priority)**
Primary monitoring focus. Countries:
Afghanistan, Bangladesh, Bhutan, Brunei, Cambodia, China, India, Indonesia, Japan, Laos, Malaysia, Maldives, Myanmar, Nepal, North Korea, Pakistan, Philippines, Singapore, South Korea, Sri Lanka, Taiwan, Thailand, Timor Leste, Vietnam

**Group B - Asia Pacific 2 + Middle East & North Africa (MEDIUM priority)**
Secondary monitoring focus. Regions:
- Asia Pacific 2: Australia, Fiji, French Polynesia, Guam, Kazakhstan, Kiribati, Kyrgyzstan, Mariana Islands, Marshall Islands, Micronesia, Mongolia, Nauru, New Caledonia, New Zealand, Niue, Palau, Papua New Guinea, Samoa, Solomon Islands, Tajikistan, Tonga, Turkmenistan, Tuvalu, Uzbekistan, Vanuatu, Wallis and Futuna
- Middle East: Bahrain, Cyprus, Iran, Iraq, Jordan, Kuwait, Lebanon, Oman, Palestine/Israel, Qatar, Saudi Arabia, Syria, Turkey, United Arab Emirates, Yemen
- North Africa: Algeria, Egypt, Morocco, Tunisia

**Group C - Rest of Africa, Europe & Americas (VARIABLE priority)**
Tertiary monitoring focus. Includes all remaining countries in Africa, Europe, and the Americas.

## Incident Priority Classification

### Level 4 - CRITICAL (Must Report)
**Indicators:**
- International assistance requested
- SGP news publish daily updates
- More than 300,000 people affected
- High death toll (50+)
- More than one state/province affected
- Humanitarian crisis declared

**Priority by Group:**
- Group A: **HIGH** - Include in all reports
- Group B: **HIGH** - Include in all reports
- Group C: **HIGH** - Include in all reports

### Level 3 - MAJOR (Should Report)
**Indicators:**
- SGP news publish frequent updates (few updates over past week)
- More than 100,000 people affected
- Significant regional impact

**Priority by Group:**
- Group A: **HIGH** - Include in all reports
- Group B: **MEDIUM** - Include in regular reports
- Group C: **MEDIUM** - Include if significant coverage

### Level 2 - SIGNIFICANT (Consider Reporting)
**Indicators:**
- SGP news publish more than one update
- Less than 100,000 people affected
- Multiple source coverage
- Regional impact starting to develop

**Priority by Group:**
- Group A: **MEDIUM** - Include in reports
- Group B: **MEDIUM** - Include if notable
- Group C: **LOW** - Include only if widespread

### Level 1 - MINOR (Optional Reporting)
**Indicators:**
- No SGP news coverage, but local news reports
- Less than 50,000 people affected
- Limited impact expected
- Early warning/emerging situation

**Priority by Group:**
- Group A: **MEDIUM** - Include for awareness
- Group B: **LOW** - Include if tracking
- Group C: **LOW** - Exclude from general reporting

## Reporting Inclusion Criteria

### Reports to INCLUDE

✅ **Humanitarian Crisis Declaration**
- Incident officially declared as humanitarian crisis
- Ongoing humanitarian crisis update
Example: https://apnews.com/article/afghanistan-aid-cuts-hunger-humanitarian-crisis-0c8f7335bc58979c36b053347b862c32

✅ **Flagged for Continued Monitoring**
- Incident in Group A country
- Previously reported incident with new developments
- Ongoing response coordination
Example: https://www.thestar.com.my/aseanplus/aseanplus-news/2025/12/28/beyond-physical-damage-floods-leave-deep-emotional-wounds-in-indonesia039s-aceh

✅ **Likely Further Development**
- Initial damage reports only ("immediate" status)
- Impact assessment ongoing
- Early indicators suggest escalation potential
Example: https://www.straitstimes.com/asia/southeastern-taiwan-shaken-by-6-1-magnitude-quake-no-immediate-reports-of-damage

✅ **Widespread Impact (Reported or Forecasted)**
- Multiple provinces/states affected
- Cross-border impact
- Regional/national scale event
Example: https://watchers.news/2025/12/22/floods-heavy-snow-and-blizzards-kill-at-least-eight-across-25-provinces-in-iran/

✅ **Environmental/Climate/Weather Awareness**
- Emerging environmental threats
- Long-term climate impacts
- Regional air quality/pollution alerts
Example: https://www.channelnewsasia.com/asia/thailand-air-pollution-environment-activists-5725091

### Reports to EXCLUDE

❌ **Unlikely Escalation**
- Low potential for humanitarian impact
- Isolated incident with clear resolution path
Example: https://www.bluewin.ch/en/news/four-dead-in-avalanche-accident-in-greece-3025810.html

❌ **Low Probability of Further Development**
- No tsunami expected after earthquake
- Contained incident, impact unlikely to spread
Example: https://www.straitstimes.com/asia/east-asia/5-6-magnitude-earthquake-hits-japans-tokara-islands-no-tsunami-expected

❌ **Low-Impact Earthquakes**
- Offshore epicentres
- Low magnitude (typically <4.5 on Richter scale)
- Great depth reducing surface impact
Example: https://breakingthenews.net/Article/5.3-magnitude-earthquake-hits-southern-Bolivia/65412202

❌ **Isolated Incidents**
- Single location, minimal affected population
- No cross-regional impact
- Clear resolution or containment

## Decision Tree for Reporting

```
Is the incident in Group A (Asia Pacific 1)?
├─ YES → Level 4 or 3? → INCLUDE
├─ YES → Level 2? → INCLUDE (Medium priority)
├─ YES → Level 1? → INCLUDE (Medium priority)
└─ NO → Is it in Group B?
    ├─ YES → Level 4 or 3? → INCLUDE
    ├─ YES → Level 2? → INCLUDE (Medium priority)
    ├─ YES → Level 1? → EXCLUDE
    └─ NO → Is it in Group C?
        ├─ YES → Level 4? → INCLUDE
        ├─ YES → Level 3? → INCLUDE (Medium priority)
        └─ NO → EXCLUDE (Low priority unless exceptional)

Additional checks:
- Is it a humanitarian crisis? → INCLUDE (regardless of level)
- Is it forecasted/early warning? → INCLUDE (for awareness)
- Multiple sources reporting? → INCLUDE (if not low-impact)
- Potential for escalation? → INCLUDE (for monitoring)
```

## Incident Data Structure

Each reported incident should capture:

```
{
  "disaster_type": "Earthquake / Flood / Cyclone / Wildfire / etc.",
  "location": "specific regions/provinces, country",
  "country_group": "A / B / C",
  "incident_level": "1 / 2 / 3 / 4",
  "priority": "HIGH / MEDIUM / LOW",
  "incident_status": "Active / Forecasted / Update",
  "affected_population": "estimated number",
  "death_toll": "confirmed deaths if available",
  "src_mentioned": true/false,
  "humanitarian_aid": true/false,
  "source_url": "link to primary source",
  "report_date": "YYYY-MM-DD",
  "description": "brief summary",
  "next_action": "monitor / track / escalate / close"
}
```

## Key Principles

1. **Consistency**: Use standardized formats across all reports
2. **Accuracy**: Only report verified information from credible sources
3. **Timeliness**: Report incidents as soon as they meet criteria
4. **Relevance**: Focus on incidents affecting or relevant to monitoring areas
5. **Context**: Provide geographic and impact context in each report
6. **Prioritization**: Weight Group A incidents more heavily in monitoring
7. **Escalation**: Flag Level 4 incidents for immediate attention
8. **Tracking**: Maintain updates on ongoing incidents until resolution

## Common Incident Types

- **Geophysical**: Earthquake, Volcano, Tsunami
- **Meteorological**: Cyclone, Hurricane, Typhoon, Tornado, Dust Storm, Severe Weather
- **Hydrological**: Flood, Flash Flood, Landslide, Avalanche
- **Climatological**: Drought, Extreme Temperature, Wildfire
- **Biological**: Disease Outbreak, Epidemic, Pandemic
- **Technological**: Industrial Accident, Hazmat Release, Infrastructure Failure
- **Conflict-Related**: Armed Conflict, Civil Unrest, Mass Displacement
- **Environmental**: Air Pollution, Water Contamination, Desertification

## Reference Links

- **Data Sources**: GDACS, ProMED, ReliefWeb, HealthMap, WHO
- **News Aggregation**: Google News, BBC News, Reuters, Associated Press
- **Regional News**: Local country-specific news outlets
- **Emergency Alerts**: National Emergency Management Agencies
