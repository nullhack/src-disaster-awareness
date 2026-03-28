---
name: dashboard-skill
description: Rules and conventions for the Disaster Awareness Dashboard - data formats, testing, deployment, and UI standards
compatibility: "1.0.0+"
metadata:
  category: dashboard
  difficulty: intermediate
  type: visualization
---

# Dashboard Skill

Rules and conventions for the Disaster Awareness Dashboard project.

## Dashboard Overview

The dashboard is a static web application that visualizes disaster and disease incident data on an interactive global map with charts and statistics.

## Technology Stack

- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Map:** Leaflet.js with CartoDB dark tiles
- **Charts:** Chart.js
- **Testing:** Playwright + pytest
- **Server:** Python http.server (development)
- **Deployment:** GitHub Pages

## Data Formats

### incidents.json

Primary file for natural disaster incidents.

```json
{
  "incident_id": "YYYYMMDD-CC-TT",
  "incident_name": "Human-readable name",
  "country": "Country name",
  "country_group": "A|B|C",
  "incident_type": "Earthquake|Flood|Cyclone|Fire|Drought|Landslide",
  "incident_level": 1-4,
  "priority": "HIGH|MEDIUM|LOW",
  "status": "Active|Resolved|Monitoring",
  "created_date": "ISO8601",
  "updated_date": "ISO8601",
  "location": {
    "country": "string",
    "province": "string",
    "districts": ["array"],
    "coordinates": {"lat": 0.0, "lon": 0.0}
  },
  "impact": {
    "deaths": 0,
    "missing": 0,
    "affected": 0,
    "displaced": 0
  },
  "sources": [
    {"name": "string", "url": "https://..."}
  ]
}
```

### disease-incidents.json

Disease outbreak incidents.

```json
{
  "incident_id": "YYYYMMDD-CC-DS",
  "incident_name": "Disease Outbreak Name",
  "country": "Country name",
  "country_group": "A|B|C",
  "incident_type": "Disease",
  "disease_type": "Dengue|Measles|Cholera|...",
  "incident_level": 1-4,
  "priority": "HIGH|MEDIUM|LOW",
  "status": "Active|Resolved|Monitoring",
  "created_date": "ISO8601",
  "updated_date": "ISO8601",
  "location": {
    "country": "string",
    "province": "string",
    "coordinates": {"lat": 0.0, "lon": 0.0}
  },
  "impact": {
    "affected": 0,
    "deaths": 0
  },
  "sources": [
    {"name": "string", "url": "https://..."}
  ]
}
```

## Severity Color Coding

| Level | Color | Hex |
|-------|-------|-----|
| 4 (Critical) | Red | #ef4444 |
| 3 (Major) | Orange | #f97316 |
| 2 (Significant) | Yellow | #eab308 |
| 1 (Minor) | Green | #22c55e |
| Disease | Purple | #8b5cf6 |

## Country Groups

| Group | Description | Countries |
|-------|-------------|-----------|
| A | Asia Pacific 1 | Indonesia, Philippines, Thailand, Malaysia, Vietnam, Myanmar, India, etc. |
| B | Asia Pacific 2 + MENA | Australia, New Zealand, UAE, Saudi Arabia, etc. |
| C | Rest of World | Europe, Americas, Africa |

## Testing Standards

### Required Tests

1. **Page Load Tests**
   - Page loads successfully (200 status)
   - Title is correct
   - No console errors

2. **UI Component Tests**
   - Header visible
   - Stats bar shows all 4 cards
   - Map container initialized
   - Filters functional
   - Charts rendered

3. **Interaction Tests**
   - Refresh button works
   - Modal opens/closes correctly
   - Filters update map

4. **Data Tests**
   - Data loads correctly
   - Counts match source files

5. **Accessibility Tests**
   - ARIA labels present
   - Color contrast adequate
   - Keyboard navigation works

### Test Commands

```bash
# All tests
pytest

# UI tests only
pytest -m ui

# With browser visible
pytest --headed

# Specific test
pytest tests/test_dashboard.py::TestDashboardUI::test_page_loads
```

## Deployment

### GitHub Pages

- Branch: `main` or `gh-pages`
- Source: `/ (root)` or `/docs`
- Workflow: `.github/workflows/deploy-dashboard.yml`

### Manual Deployment

1. Ensure data files are in `dashboard/data/`
2. Ensure static files in `dashboard/static/`
3. Deploy via GitHub Actions or manual upload

## UI/UX Guidelines

### Color Scheme

- Background: `#0a0e17` (dark)
- Card Background: `#151d2e`
- Border: `#2d3a4f`
- Text: `#f1f5f9`
- Text Secondary: `#94a3b8`

### Responsive Breakpoints

- Mobile: < 768px
- Tablet: 768px - 1200px
- Desktop: > 1200px

### Map Settings

- Center: [15, 90] (Asia-Pacific focus)
- Default Zoom: 3
- Tiles: CartoDB Dark Matter

## File Paths

| Purpose | Path |
|---------|------|
| Dashboard HTML | `dashboard/static/index.html` |
| Dashboard CSS | `dashboard/static/styles.css` |
| Dashboard JS | `dashboard/static/app.js` |
| Incidents Data | `dashboard/data/incidents.json` |
| Disease Data | `dashboard/data/disease-incidents.json` |
| Tests | `dashboard/tests/` |
| Server | `dashboard/src/server.py` |

## Development Workflow

1. **Start Development Server:**
   ```bash
   cd dashboard
   python -m src.server --open
   ```

2. **Run Tests:**
   ```bash
   cd dashboard
   pytest -m ui
   ```

3. **Update Data:**
   - Edit `dashboard/data/incidents.json`
   - Edit `dashboard/data/disease-incidents.json`

4. **Deploy:**
   - Push to main branch
   - GitHub Actions deploys automatically

## Integration with Incident Database

The dashboard can read from:
1. **Static files:** `dashboard/data/*.json` (current)
2. **API endpoint:** Future enhancement
3. **JSONL files:** Via build script transformation

For static deployment, use `data-engineer` to generate JSON from JSONL:
```bash
# Convert incidents/by-date/*/incidents.jsonl to dashboard/data/incidents.json
```

This skill ensures consistent dashboard development and deployment.
