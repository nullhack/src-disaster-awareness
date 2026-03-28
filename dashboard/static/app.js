/**
 * Disaster Awareness Dashboard - Main Application
 */

// Configuration
const CONFIG = {
    dataPath: 'data/',
    refreshInterval: 300000, // 5 minutes
    mapCenter: [15, 90], // Asia-Pacific focus
    mapZoom: 3,
    // Marker sizes by severity (in pixels)
    markerSizes: {
        4: 40,  // Critical - largest
        3: 32,  // Major
        2: 26,  // Significant
        1: 20,  // Minor - smallest
    },
    // Marker colors by disaster TYPE (not severity)
    markerColors: {
        Flood: '#3b82f6',      // Blue
        Earthquake: '#92400e',  // Brown/amber
        Cyclone: '#06b6d4',    // Cyan
        Fire: '#dc2626',       // Red
        Drought: '#d97706',    // Amber
        Landslide: '#78350f', // Dark brown
        Disease: '#8b5cf6',   // Purple (kept for disease)
    },
};

// State
const state = {
    incidents: [],
    diseaseIncidents: [],
    map: null,
    markers: [],
    filters: {
        type: 'all',
        severity: 'all',
        countryGroup: 'all',
    },
    charts: {
        disease: null,
        type: null,
    },
};

// Severity colors
const SEVERITY_COLORS = {
    4: '#ef4444', // Critical - Red
    3: '#f97316', // Major - Orange
    2: '#eab308', // Significant - Yellow
    1: '#22c55e', // Minor - Green
};

// Disease type marker
const DISEASE_ICON = L.divIcon({
    className: 'disease-marker',
    html: `<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24" style="color: #8b5cf6;">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
    </svg>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
});

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initCharts();
    setupEventListeners();
    loadData();
    startAutoRefresh();
});

/**
 * Initialize Leaflet map
 */
function initMap() {
    state.map = L.map('map', {
        center: CONFIG.mapCenter,
        zoom: CONFIG.mapZoom,
        zoomControl: true,
        attributionControl: true,
    });

    // Dark map tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19,
    }).addTo(state.map);

    // Add attribution
    state.map.attributionControl.addAttribution('Disaster data from GDACS, WHO, ProMED');
}

/**
 * Initialize Chart.js charts
 */
function initCharts() {
    // Disease Chart
    const diseaseCtx = document.getElementById('diseaseChart');
    if (diseaseCtx) {
        state.charts.disease = new Chart(diseaseCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#8b5cf6',
                        '#a78bfa',
                        '#c4b5fd',
                        '#ddd6fe',
                    ],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#94a3b8',
                            font: { size: 11 },
                            padding: 8,
                            boxWidth: 12,
                        },
                    },
                },
                cutout: '60%',
            },
        });
    }

    // Type Chart
    const typeCtx = document.getElementById('typeChart');
    if (typeCtx) {
        state.charts.type = new Chart(typeCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Incidents',
                    data: [],
                    backgroundColor: [
                        '#ef4444',
                        '#f97316',
                        '#eab308',
                        '#22c55e',
                        '#3b82f6',
                        '#8b5cf6',
                    ],
                    borderRadius: 4,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    x: {
                        grid: { color: '#2d3a4f' },
                        ticks: { color: '#64748b' },
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8' },
                    },
                },
            },
        });
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Refresh button - loads from GitHub on demand
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            refreshFromGitHub();
        });
    }

    // Filters
    const typeFilter = document.getElementById('typeFilter');
    const severityFilter = document.getElementById('severityFilter');
    const countryGroupFilter = document.getElementById('countryGroupFilter');

    if (typeFilter) {
        typeFilter.addEventListener('change', (e) => {
            state.filters.type = e.target.value;
            updateMapMarkers();
            updateTable();
        });
    }

    if (severityFilter) {
        severityFilter.addEventListener('change', (e) => {
            state.filters.severity = e.target.value;
            updateMapMarkers();
            updateTable();
        });
    }

    if (countryGroupFilter) {
        countryGroupFilter.addEventListener('change', (e) => {
            state.filters.countryGroup = e.target.value;
            updateMapMarkers();
            updateTable();
        });
    }

    // Country filter
    const countryFilter = document.getElementById('countryFilter');
    if (countryFilter) {
        countryFilter.addEventListener('change', (e) => {
            state.filters.country = e.target.value;
            updateMapMarkers();
            updateTable();
        });
    }

    // Summary button
    const summarizeBtn = document.getElementById('summarizeBtn');
    const closeSummaryBtn = document.getElementById('closeSummary');
    const summaryPanel = document.getElementById('summaryPanel');

    if (summarizeBtn) {
        summarizeBtn.addEventListener('click', () => {
            showSummary();
        });
    }

    if (closeSummaryBtn && summaryPanel) {
        closeSummaryBtn.addEventListener('click', () => {
            summaryPanel.classList.add('hidden');
        });
    }

    // Modal close
    const modal = document.getElementById('incidentModal');
    const modalClose = modal?.querySelector('.modal-close');
    const modalBackdrop = modal?.querySelector('.modal-backdrop');

    modalClose?.addEventListener('click', closeModal);
    modalBackdrop?.addEventListener('click', closeModal);

    // Escape key to close modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

/**
 * Load data from local files (fast)
 */
async function loadData() {
    showLoading(true);
    console.log('Loading data...');

    try {
        const incidentsData = await fetchData('incidents.json');
        console.log('Incidents:', incidentsData ? incidentsData.length : 0);
        
        const diseaseData = await fetchData('disease-incidents.json');
        
        state.incidents = incidentsData || [];
        state.diseaseIncidents = diseaseData || [];
        
        console.log(`Loaded ${state.incidents.length} incidents`);
    } catch (e) {
        console.error('Error loading data:', e);
    }

    updateAllUI();
    showLoading(false);
}

/**
 * Refresh data from GitHub (on demand)
 */
async function refreshFromGitHub() {
    showLoading(true);
    console.log('Refreshing from GitHub...');
    
    try {
        const API_URL = 'https://api.github.com/repos/nullhack/src-disaster-awareness/contents/incidents/by-date';
        const datesResponse = await fetch(API_URL);
        
        if (!datesResponse.ok) throw new Error('GitHub API failed');
        
        const dateDirs = await datesResponse.json();
        const uniqueDates = dateDirs
            .filter(d => d.type === 'dir' && d.name.match(/^\d{4}-\d{2}-\d{2}$/))
            .map(d => d.name)
            .sort()
            .slice(-30);
        
        const GITHUB_RAW = 'https://raw.githubusercontent.com/nullhack/src-disaster-awareness/main';
        
        const allIncidents = [];
        const allDiseases = [];
        
        for (const date of uniqueDates) {
            try {
                const response = await fetch(`${GITHUB_RAW}/incidents/by-date/${date}/incidents.jsonl`);
                if (!response.ok) continue;
                
                const text = await response.text();
                const lines = text.split('\n').filter(l => l.trim());
                
                for (const line of lines) {
                    try {
                        const record = JSON.parse(line);
                        const normalized = normalizeIncident(record);
                        if (normalized.incident_type === 'Disease') {
                            allDiseases.push(normalized);
                        } else {
                            allIncidents.push(normalized);
                        }
                    } catch (e) {}
                }
            } catch (e) {}
        }
        
        if (allIncidents.length > 0) {
            allIncidents.sort((a, b) => new Date(b.updated_date || b.created_date) - new Date(a.updated_date || a.created_date));
            allDiseases.sort((a, b) => new Date(b.updated_date || b.created_date) - new Date(a.updated_date || a.created_date));
            
            state.incidents = allIncidents;
            state.diseaseIncidents = allDiseases;
            
            // Save to local for offline use
            localStorage.setItem('incidents', JSON.stringify(allIncidents));
            localStorage.setItem('diseases', JSON.stringify(allDiseases));
            
            console.log(`Refreshed: ${allIncidents.length} incidents from GitHub`);
        }
    } catch (error) {
        console.error('GitHub refresh failed:', error);
        alert('Failed to refresh from GitHub. Using cached data.');
    }
    
    updateAllUI();
    showLoading(false);
}

/**
 * Update all UI components
 */
function updateAllUI() {
    populateCountryFilter();
    updateStats();
    updateMapMarkers();
    updateRecentIncidents();
    updateCharts();
    updateTable();
    updateLastUpdated();
}
    
    const datesResponse = await fetch(API_URL);
    if (!datesResponse.ok) throw new Error('GitHub API failed');
    
    const dateDirs = await datesResponse.json();
    const uniqueDates = dateDirs
        .filter(d => d.type === 'dir' && d.name.match(/^\d{4}-\d{2}-\d{2}$/))
        .map(d => d.name)
        .sort()
        .slice(-30);
    
    const GITHUB_RAW = 'https://raw.githubusercontent.com/nullhack/src-disaster-awareness/main';
    
    const allIncidents = [];
    const allDiseases = [];
    
    for (const date of uniqueDates) {
        try {
            const response = await fetch(`${GITHUB_RAW}/incidents/by-date/${date}/incidents.jsonl`);
            if (!response.ok) continue;
            
            const text = await response.text();
            const lines = text.split('\n').filter(l => l.trim());
            
            for (const line of lines) {
                try {
                    const record = JSON.parse(line);
                    const normalized = normalizeIncident(record);
                    
                    if (normalized.incident_type === 'Disease') {
                        allDiseases.push(normalized);
                    } else {
                        allIncidents.push(normalized);
                    }
                } catch (e) {}
            }
        } catch (e) {}
    }
    
    if (allIncidents.length > 0) {
        allIncidents.sort((a, b) => new Date(b.updated_date || b.created_date) - new Date(a.updated_date || a.created_date));
        allDiseases.sort((a, b) => new Date(b.updated_date || b.created_date) - new Date(a.updated_date || a.created_date));
        
        state.incidents = allIncidents;
        state.diseaseIncidents = allDiseases;
        
        // Update UI with fresh data
        populateCountryFilter();
        updateStats();
        updateMapMarkers();
        updateRecentIncidents();
        updateCharts();
        updateTable();
    }
}

/**
 * Normalize incident from JSONL to dashboard format
 */
function normalizeIncident(record) {
    const typeMapping = {
        'Cyclone': 'Cyclone', 'Tropical Cyclone': 'Cyclone', 'Typhoon': 'Cyclone', 'Hurricane': 'Cyclone',
        'Earthquake': 'Earthquake', 'Flood': 'Flood', 'Flash Flood': 'Flood', 'River Flood': 'Flood',
        'Wildfire': 'Fire', 'Forest Fire': 'Fire', 'Fire': 'Fire', 'Volcano': 'Fire',
        'Drought': 'Drought', 'Landslide': 'Landslide', 'Mudslide': 'Landslide',
        'Disease': 'Disease', 'Outbreak': 'Disease', 'Epidemic': 'Disease',
        'Conflict': 'Conflict', 'Food Insecurity': 'Food Insecurity', 'Severe Weather': 'Severe Weather',
    };
    
    const it = record.incident_type || '';
    let dtype = typeMapping[it] || it;
    if (!dtype && it.toLowerCase().includes('cyclone')) dtype = 'Cyclone';
    if (!dtype && it.toLowerCase().includes('fire')) dtype = 'Fire';
    if (!dtype && it.toLowerCase().includes('flood')) dtype = 'Flood';
    if (!dtype && it.toLowerCase().includes('disease')) dtype = 'Disease';
    
    const loc = record.location || {};
    const coords = loc.coordinates || {};
    const provinces = loc.provinces || [];
    const imp = record.impact || {};
    const dd = record.disaster_details || {};
    const cm = record.classification_metadata || {};
    const meta = record.metadata || {};
    
    const sources = (record.sources || []).map(s => ({
        name: s.name || '',
        url: s.url || '',
        type: s.type || '',
        reliability: s.reliability_tier || ''
    }));
    
    return {
        incident_id: record.incident_id || '',
        incident_name: record.incident_name || '',
        country: record.country || '',
        country_group: record.country_group || 'C',
        incident_type: dtype,
        incident_level: record.incident_level || 1,
        priority: record.priority || 'LOW',
        status: record.status || 'Active',
        created_date: record.created_date || '',
        updated_date: record.updated_date || '',
        location: {
            country: record.country || '',
            province: provinces[0]?.name || '',
            affected_provinces: provinces.filter(p => p.affected).length || 1,
            affected_area_description: loc.affected_area_description || '',
            coordinates: {
                lat: coords.latitude || coords.lat || 0,
                lon: coords.longitude || coords.lon || 0
            }
        },
        impact: {
            deaths: imp.deaths || 0,
            missing: imp.missing || 0,
            injured: imp.injuries || 0,
            affected: imp.affected_population || 0,
            displaced: imp.displaced_persons || 0,
            impact_description: imp.impact_description || ''
        },
        disaster_details: {
            disaster_type: dd.disaster_type || '',
            magnitude: dd.magnitude_or_scale || '',
            depth: dd.depth_or_altitude || '',
            forecasted: dd.forecasted || false
        },
        sources: sources,
        classification: {
            classified_by: cm.classified_by || '',
            confidence: cm.classification_confidence || 0,
            rationale: cm.rationale || ''
        },
        metadata: {
            data_quality: meta.data_quality || '',
            completeness: meta.completeness_score || 0
        }
    };
}

/**
 * Fetch JSON data
 */
async function fetchData(filename) {
    try {
        const url = CONFIG.dataPath + filename;
        console.log('Fetching:', url);
        const response = await fetch(url);
        console.log('Response:', response.status, response.ok);
        if (!response.ok) return [];
        const data = await response.json();
        console.log('Got:', data.length, 'records');
        return data;
    } catch (error) {
        console.error(`Error loading ${filename}:`, error);
        return [];
    }
}

/**
 * Update statistics
 */
function updateStats() {
    const total = state.incidents.length + state.diseaseIncidents.length;
    const critical = [...state.incidents, ...state.diseaseIncidents].filter(i => i.incident_level === 4).length;
    const significant = [...state.incidents, ...state.diseaseIncidents].filter(i => i.incident_level === 3).length;
    const diseases = state.diseaseIncidents.length;

    animateValue('totalIncidents', total);
    animateValue('criticalIncidents', critical);
    animateValue('significantIncidents', significant);
    animateValue('diseaseIncidents', diseases);
}

/**
 * Animate number value
 */
function animateValue(elementId, end) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const start = parseInt(element.textContent) || 0;
    const duration = 500;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + (end - start) * easeOut);

        element.textContent = current;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

/**
 * Update map markers
 */
function updateMapMarkers() {
    // Clear existing markers
    state.markers.forEach(marker => state.map.removeLayer(marker));
    state.markers = [];

    // Filter incidents
    const filtered = getFilteredIncidents();

    // Add markers
    filtered.forEach(incident => {
        const marker = createMarker(incident);
        if (marker) {
            marker.addTo(state.map);
            state.markers.push(marker);
        }
    });
}

/**
 * Get filtered incidents
 */
function getFilteredIncidents() {
    const all = [...state.incidents, ...state.diseaseIncidents];

    return all.filter(incident => {
        // Type filter
        if (state.filters.type !== 'all') {
            if (state.filters.type === 'Disease') {
                if (incident.incident_type !== 'Disease' && incident.incident_type !== 'Disease Outbreak') return false;
            } else {
                if (incident.incident_type !== state.filters.type) return false;
            }
        }

        // Severity filter
        if (state.filters.severity !== 'all') {
            if (incident.incident_level !== parseInt(state.filters.severity)) return false;
        }

        // Country group filter
        if (state.filters.countryGroup !== 'all') {
            if (incident.country_group !== state.filters.countryGroup) return false;
        }

        // Country filter
        if (state.filters.country && state.filters.country !== 'all') {
            if (incident.country !== state.filters.country) return false;
        }

        return true;
    });
}

/**
 * Populate country filter dropdown with available countries
 */
function populateCountryFilter() {
    const countryFilter = document.getElementById('countryFilter');
    if (!countryFilter) return;

    // Get all unique countries from data
    const allIncidents = [...state.incidents, ...state.diseaseIncidents];
    const countries = [...new Set(allIncidents.map(i => i.country).filter(Boolean))].sort();

    // Keep the "All Countries" option
    const firstOption = countryFilter.options[0];
    countryFilter.innerHTML = '';
    countryFilter.add(new Option('All Countries', 'all'));

    countries.forEach(country => {
        countryFilter.add(new Option(country, country));
    });
}

/**
 * Create map marker
 * - Color based on DISASTER TYPE (blue=flood, red=fire, brown=earthquake, etc.)
 * - Size based on SEVERITY (larger = more severe)
 */
function createMarker(incident) {
    if (!incident.location?.coordinates?.lat || !incident.location?.coordinates?.lon) {
        return null;
    }

    // Get color by TYPE (flood=blue, fire=red, earthquake=brown, etc.)
    const incidentType = incident.incident_type || 'Unknown';
    const color = CONFIG.markerColors[incidentType] || CONFIG.markerColors['Disease'] || '#6b7280';

    // Get size by SEVERITY (Level 4 = largest, Level 1 = smallest)
    const severity = incident.incident_level || 1;
    const size = CONFIG.markerSizes[severity] || 20;

    const icon = L.divIcon({
        className: 'incident-marker',
        html: `<div style="
            width: ${size}px;
            height: ${size}px;
            background: ${color};
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 0 15px ${color}, 0 4px 8px rgba(0,0,0,0.3);
            transition: transform 0.2s;
        " title="${incident.incident_name} (Level ${severity})"></div>`,
        iconSize: [size, size],
        iconAnchor: [size/2, size/2],
    });

    const marker = L.marker([incident.location.coordinates.lat, incident.location.coordinates.lon], { icon });

    // Create popup content
    const popupContent = createPopupContent(incident);
    marker.bindPopup(popupContent, {
        className: 'incident-popup',
        maxWidth: 300,
    });

    return marker;
}

/**
 * Create popup content
 */
function createPopupContent(incident) {
    const severity = getSeverityLabel(incident.incident_level);
    const color = SEVERITY_COLORS[incident.incident_level] || '#3b82f6';
    
    // Get description
    const description = incident.impact?.impact_description || incident.location?.affected_area_description || '';

    return `
        <div style="min-width: 250px; max-width: 300px;">
            <div style="
                display: inline-block;
                padding: 2px 8px;
                background: ${color}20;
                color: ${color};
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                margin-bottom: 8px;
            ">
                ${severity}
            </div>
            <h4 style="font-size: 14px; font-weight: 600; margin: 0 0 4px 0;">
                ${incident.incident_name}
            </h4>
            <p style="font-size: 12px; color: #94a3b8; margin: 0 0 8px 0;">
                ${incident.country} • ${incident.incident_type}
            </p>
            ${description ? `<p style="font-size: 11px; color: #cbd5e1; margin: 0 0 8px 0; line-height: 1.4; max-height: 60px; overflow: hidden; text-overflow: ellipsis;">${description}</p>` : ''}
            ${incident.impact?.deaths ? `<p style="font-size: 12px; margin: 4px 0 0 0;"><strong>Deaths:</strong> ${incident.impact.deaths.toLocaleString()}</p>` : ''}
            ${incident.impact?.affected ? `<p style="font-size: 12px; margin: 4px 0 0 0;"><strong>Affected:</strong> ${incident.impact.affected.toLocaleString()}</p>` : ''}
            <button 
                onclick="openModal('${incident.incident_id}')"
                style="
                    margin-top: 12px;
                    padding: 6px 12px;
                    background: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    cursor: pointer;
                "
            >
                View Details
            </button>
        </div>
    `;
}

/**
 * Get severity label
 */
function getSeverityLabel(level) {
    const labels = {
        4: 'Critical',
        3: 'Major',
        2: 'Significant',
        1: 'Minor',
    };
    return labels[level] || 'Unknown';
}

/**
 * Update recent incidents list
 */
function updateRecentIncidents() {
    const container = document.getElementById('recentIncidents');
    if (!container) return;

    const all = [...state.incidents, ...state.diseaseIncidents]
        .sort((a, b) => new Date(b.updated_date || b.created_date) - new Date(a.updated_date || a.created_date))
        .slice(0, 10);

    if (all.length === 0) {
        container.innerHTML = '<p style="color: #64748b; text-align: center; padding: 20px;">No incidents recorded</p>';
        return;
    }

    container.innerHTML = all.map(incident => `
        <div class="incident-item" onclick="openModal('${incident.incident_id}')">
            <div class="incident-severity level-${incident.incident_level}"></div>
            <div class="incident-info">
                <div class="incident-name">${incident.incident_name}</div>
                <div class="incident-meta">
                    <span>${incident.country}</span>
                    <span>•</span>
                    <span>${formatDate(incident.updated_date || incident.created_date)}</span>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Update data table with filtered incidents
 */
function updateTable() {
    const tbody = document.getElementById('incidentsTableBody');
    const countEl = document.getElementById('tableCount');
    if (!tbody) return;

    const filtered = getFilteredIncidents()
        .sort((a, b) => new Date(b.updated_date || b.created_date) - new Date(a.updated_date || a.created_date));

    // Update count
    if (countEl) {
        countEl.textContent = `${filtered.length} incident${filtered.length !== 1 ? 's' : ''}`;
    }

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-cell">
                    No incidents match the current filters
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.slice(0, 50).map((incident, index) => {
        const levelColors = { 4: '#ef4444', 3: '#f97316', 2: '#eab308', 1: '#22c55e' };
        const levelColor = levelColors[incident.incident_level] || '#6b7280';
        
        // Get source links
        const sources = incident.sources || [];
        const sourceLinks = sources.slice(0, 2).map(s => 
            `<a href="${s.url}" target="_blank" class="source-link" title="${s.name}">${s.name}</a>`
        ).join(', ') || 'N/A';
        
        // Build summary text
        const summary = buildIncidentSummary(incident);
        
        // Location text
        const province = incident.location?.province || '-';
        const location = incident.location?.province 
            ? `${incident.location.province}, ${incident.country}` 
            : incident.country || 'Unknown';
        
        // Magnitude
        const magnitude = incident.disaster_details?.magnitude || incident.disaster_details?.depth || '-';
        
        // Get description - prefer impact description, fallback to incident name
        const description = incident.impact?.impact_description || incident.location?.affected_area_description || incident.incident_name || '-';

        return `
            <tr class="table-row" data-id="${incident.incident_id}">
                <td class="expand-cell">
                    <button class="expand-btn" onclick="toggleRow(this, '${incident.incident_id}')" title="Expand details">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M9 18l6-6-6-6"/>
                        </svg>
                    </button>
                </td>
                <td>${formatDate(incident.updated_date || incident.created_date)}</td>
                <td>${incident.country || '-'}</td>
                <td><span class="type-badge type-${incident.incident_type?.toLowerCase()}">${incident.incident_type || '-'}</span></td>
                <td class="description-cell" title="${description}">${description}</td>
                <td><span class="level-badge" style="background: ${levelColor}">L${incident.incident_level || 1}</span></td>
                <td>${(incident.impact?.deaths || 0).toLocaleString()}</td>
                <td>${formatNumber(incident.impact?.affected || 0)}</td>
                <td>${formatNumber(incident.impact?.displaced || 0)}</td>
                <td>${magnitude}</td>
                <td><span class="status-badge ${(incident.status || 'Active').toLowerCase()}">${incident.status || '-'}</span></td>
                <td class="sources-cell">${sourceLinks}</td>
            </tr>
            <tr class="summary-row hidden" id="summary-${incident.incident_id}">
                <td colspan="12">
                    <div class="incident-summary">
                        <div class="summary-grid">
                            <div class="summary-item">
                                <span class="summary-label">Location</span>
                                <span class="summary-value">${location}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Affected Provinces</span>
                                <span class="summary-value">${incident.location?.affected_provinces || 1}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Injured</span>
                                <span class="summary-value">${formatNumber(incident.impact?.injured || 0)}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Magnitude/Scale</span>
                                <span class="summary-value">${magnitude}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Forecasted</span>
                                <span class="summary-value">${forecasted}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Country Group</span>
                                <span class="summary-value">Group ${incident.country_group || '-'}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">First Reported</span>
                                <span class="summary-value">${formatDate(incident.first_reported)}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Classification</span>
                                <span class="summary-value">${incident.classification?.classified_by || '-'}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Confidence</span>
                                <span class="summary-value">${Math.round((incident.classification?.confidence || 0) * 100)}%</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Data Quality</span>
                                <span class="summary-value">${incident.metadata?.data_quality || '-'}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Completeness</span>
                                <span class="summary-value">${Math.round((incident.metadata?.completeness || 0) * 100)}%</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Tags</span>
                                <span class="summary-value">${(incident.tags || []).join(', ') || '-'}</span>
                            </div>
                        </div>
                        ${incident.impact?.impact_description ? `
                        <div class="summary-description full-width">
                            <span class="summary-label">Impact Description</span>
                            <p>${incident.impact.impact_description}</p>
                        </div>
                        ` : ''}
                        ${incident.location?.affected_area_description ? `
                        <div class="summary-description full-width">
                            <span class="summary-label">Affected Area</span>
                            <p>${incident.location.affected_area_description}</p>
                        </div>
                        ` : ''}
                        <div class="summary-description">
                            <span class="summary-label">Summary</span>
                            <p>${summary}</p>
                        </div>
                        <div class="summary-actions">
                            <button class="btn btn-primary btn-sm" onclick="openModal('${incident.incident_id}')">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                    <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                                </svg>
                                View Full Details
                            </button>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Toggle table row expansion
 */
function toggleRow(btn, incidentId) {
    const summaryRow = document.getElementById(`summary-${incidentId}`);
    if (!summaryRow) return;
    
    const isHidden = summaryRow.classList.contains('hidden');
    
    if (isHidden) {
        // Close all other expanded rows first
        document.querySelectorAll('.summary-row:not(.hidden)').forEach(row => {
            row.classList.add('hidden');
        });
        document.querySelectorAll('.expand-btn').forEach(b => {
            b.classList.remove('expanded');
        });
        
        // Expand this row
        summaryRow.classList.remove('hidden');
        btn.classList.add('expanded');
    } else {
        // Collapse this row
        summaryRow.classList.add('hidden');
        btn.classList.remove('expanded');
    }
}

/**
 * Build incident summary text
 */
function buildIncidentSummary(incident) {
    const parts = [];
    
    if (incident.location?.province) {
        parts.push(`Affected area: ${incident.location.province}, ${incident.country}`);
    }
    
    if (incident.impact?.deaths) {
        parts.push(`${incident.impact.deaths} death${incident.impact.deaths > 1 ? 's' : ''}`);
    }
    
    if (incident.impact?.affected) {
        parts.push(`${formatNumber(incident.impact.affected)} affected`);
    }
    
    if (incident.impact?.displaced) {
        parts.push(`${formatNumber(incident.impact.displaced)} displaced`);
    }
    
    if (incident.status) {
        parts.push(`Status: ${incident.status}`);
    }
    
    // Add source info
    if (incident.sources?.length > 0) {
        parts.push(`Source: ${incident.sources[0].name}`);
    }
    
    return parts.join(' • ') || 'No details available';
}

/**
 * Update charts
 */
function updateCharts() {
    // Disease chart
    if (state.charts.disease) {
        const diseaseTypes = {};
        state.diseaseIncidents.forEach(d => {
            const type = d.disease_type || d.incident_type || 'Unknown';
            diseaseTypes[type] = (diseaseTypes[type] || 0) + 1;
        });

        state.charts.disease.data.labels = Object.keys(diseaseTypes);
        state.charts.disease.data.datasets[0].data = Object.values(diseaseTypes);
        state.charts.disease.update();
    }

    // Type chart
    if (state.charts.type) {
        const types = {};
        state.incidents.forEach(i => {
            types[i.incident_type] = (types[i.incident_type] || 0) + 1;
        });

        const sorted = Object.entries(types)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 6);

        state.charts.type.data.labels = sorted.map(([k]) => k);
        state.charts.type.data.datasets[0].data = sorted.map(([, v]) => v);
        state.charts.type.update();
    }
}

/**
 * Open incident modal
 */
window.openModal = function(incidentId) {
    const all = [...state.incidents, ...state.diseaseIncidents];
    const incident = all.find(i => i.incident_id === incidentId);

    if (!incident) return;

    const modal = document.getElementById('incidentModal');
    const severity = getSeverityLabel(incident.incident_level);

    // Set severity badge
    const severityBadge = document.getElementById('modalSeverity');
    severityBadge.textContent = `Level ${incident.incident_level} - ${severity}`;
    severityBadge.className = `severity-badge level-${incident.incident_level}`;

    // Set title
    document.getElementById('modalTitle').textContent = incident.incident_name;

    // Set details - including description prominently
    const description = incident.impact?.impact_description || incident.location?.affected_area_description || 'No description available';
    document.getElementById('modalDescription').textContent = description;
    document.getElementById('modalCountry').textContent = incident.country;
    document.getElementById('modalType').textContent = incident.incident_type;
    document.getElementById('modalLevel').textContent = `Level ${incident.incident_level}`;
    document.getElementById('modalStatus').textContent = incident.status || 'Active';
    document.getElementById('modalDeaths').textContent = incident.impact?.deaths?.toLocaleString() || '0';
    document.getElementById('modalAffected').textContent = incident.impact?.affected?.toLocaleString() || '0';
    document.getElementById('modalDisplaced').textContent = incident.impact?.displaced?.toLocaleString() || '0';
    document.getElementById('modalMissing').textContent = incident.impact?.missing?.toLocaleString() || '0';
    document.getElementById('modalInjured').textContent = incident.impact?.injured?.toLocaleString() || '0';
    document.getElementById('modalUpdated').textContent = formatDate(incident.updated_date || incident.created_date);

    // Set sources
    const sourcesList = document.getElementById('sourcesList');
    if (incident.sources && incident.sources.length > 0) {
        sourcesList.innerHTML = incident.sources.map(s => `
            <li>
                <a href="${s.url}" target="_blank" rel="noopener noreferrer">
                    ${s.name || 'Source'}
                </a>
            </li>
        `).join('');
    } else {
        sourcesList.innerHTML = '<li>No sources available</li>';
    }

    // Show modal
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
};

/**
 * Close modal
 */
function closeModal() {
    const modal = document.getElementById('incidentModal');
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

/**
 * Update last updated timestamp
 */
function updateLastUpdated() {
    const element = document.querySelector('.last-updated .value');
    if (element) {
        element.textContent = new Date().toLocaleString();
    }
}

/**
 * Show/hide loading
 */
function showLoading(show) {
    // Could implement loading overlay
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
}

/**
 * Format date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });
    } catch {
        return dateString;
    }
}

/**
 * Start auto-refresh
 */
function startAutoRefresh() {
    setInterval(loadData, CONFIG.refreshInterval);
}

/**
 * Get filtered incidents based on current filters
 */
function getFilteredIncidents() {
    const allIncidents = [...state.incidents, ...state.diseaseIncidents];
    
    return allIncidents.filter(incident => {
        // Type filter
        if (state.filters.type !== 'all') {
            if (state.filters.type === 'Disease') {
                if (incident.incident_type !== 'Disease') return false;
            } else {
                if (incident.incident_type !== state.filters.type) return false;
            }
        }
        
        // Severity filter
        if (state.filters.severity !== 'all') {
            if (incident.incident_level !== parseInt(state.filters.severity)) return false;
        }
        
        // Country group filter
        if (state.filters.countryGroup !== 'all') {
            if (incident.country_group !== state.filters.countryGroup) return false;
        }
        
        return true;
    });
}

/**
 * Show summary panel with filtered data
 */
function showSummary() {
    const filtered = getFilteredIncidents();
    const summaryPanel = document.getElementById('summaryPanel');
    const summaryTitle = document.getElementById('summaryTitle');
    const summaryTotal = document.getElementById('summaryTotal');
    const summaryDeaths = document.getElementById('summaryDeaths');
    const summaryAffected = document.getElementById('summaryAffected');
    const summaryCountries = document.getElementById('summaryCountries');
    const severityBreakdown = document.getElementById('severityBreakdown');
    const countryBreakdown = document.getElementById('countryBreakdown');
    
    if (!summaryPanel) return;
    
    // Show panel
    summaryPanel.classList.remove('hidden');
    
    // Build filter description
    let filterDesc = [];
    if (state.filters.type !== 'all') filterDesc.push(state.filters.type);
    if (state.filters.severity !== 'all') filterDesc.push(`Level ${state.filters.severity}`);
    if (state.filters.countryGroup !== 'all') filterDesc.push(`Group ${state.filters.countryGroup}`);
    
    summaryTitle.textContent = filterDesc.length > 0 
        ? `Summary: ${filterDesc.join(' + ')}`
        : 'All Incidents Summary';
    
    // Calculate totals
    const totalDeaths = filtered.reduce((sum, i) => sum + (i.impact?.deaths || 0), 0);
    const totalAffected = filtered.reduce((sum, i) => sum + (i.impact?.affected || 0), 0);
    const countries = [...new Set(filtered.map(i => i.country))];
    
    summaryTotal.textContent = filtered.length;
    summaryDeaths.textContent = totalDeaths.toLocaleString();
    summaryAffected.textContent = formatNumber(totalAffected);
    summaryCountries.textContent = countries.length;
    
    // Severity breakdown
    const severityCounts = { 4: 0, 3: 0, 2: 0, 1: 0 };
    filtered.forEach(i => {
        const level = i.incident_level || 1;
        if (severityCounts[level] !== undefined) {
            severityCounts[level]++;
        }
    });
    
    const maxCount = Math.max(...Object.values(severityCounts), 1);
    const severityLabels = { 4: 'Critical', 3: 'Major', 2: 'Significant', 1: 'Minor' };
    const severityColors = { 4: 'critical', 3: 'major', 2: 'significant', 1: 'minor' };
    
    severityBreakdown.innerHTML = Object.entries(severityCounts).map(([level, count]) => `
        <div class="breakdown-bar">
            <span class="breakdown-label">${severityLabels[level]}</span>
            <div class="breakdown-bar-container">
                <div class="breakdown-bar-fill ${severityColors[level]}" style="width: ${(count / maxCount) * 100}%"></div>
            </div>
            <span class="breakdown-count">${count}</span>
        </div>
    `).join('');
    
    // Country breakdown
    const countryCounts = {};
    filtered.forEach(i => {
        countryCounts[i.country] = (countryCounts[i.country] || 0) + 1;
    });
    
    const sortedCountries = Object.entries(countryCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    
    countryBreakdown.innerHTML = sortedCountries.map(([country, count]) => 
        `<span class="breakdown-item">${country} (${count})</span>`
    ).join('');
    
    // Generate AI summary
    generateAISummary(filtered);
}

/**
 * Generate AI summary using Ollama or fallback
 */
async function generateAISummary(incidents) {
    const aiSummary = document.getElementById('aiSummary');
    const aiContent = document.getElementById('aiSummaryContent');
    
    if (!aiSummary || !aiContent) return;
    
    aiSummary.classList.remove('hidden');
    aiContent.innerHTML = `
        <div class="ai-loading">
            <div class="spinner-small"></div>
            <span>Generating summary...</span>
        </div>
    `;
    
    // Build summary text
    const summaryText = buildSummaryText(incidents);
    
    // Try Ollama first, then fallback
    try {
        const response = await fetch('http://localhost:11434/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'llama3.2',
                prompt: `You are a disaster analysis assistant. Provide a brief 2-3 sentence summary of the following disaster incidents, highlighting key patterns, risks, and recommendations:\n\n${summaryText}`,
                stream: false,
                format: 'json'
            }),
            signal: AbortSignal.timeout(10000)
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.response) {
                aiContent.textContent = data.response;
                return;
            }
        }
    } catch (e) {
        console.log('Ollama not available, using fallback summary');
    }
    
    // Fallback: Generate summary without LLM
    aiContent.textContent = generateFallbackSummary(incidents);
}

/**
 * Build text summary for LLM
 */
function buildSummaryText(incidents) {
    if (incidents.length === 0) return 'No incidents to summarize.';
    
    const totalDeaths = incidents.reduce((sum, i) => sum + (i.impact?.deaths || 0), 0);
    const totalAffected = incidents.reduce((sum, i) => sum + (i.impact?.affected || 0), 0);
    
    const typeCounts = {};
    const countryCounts = {};
    const levelCounts = {};
    
    incidents.forEach(i => {
        typeCounts[i.incident_type] = (typeCounts[i.incident_type] || 0) + 1;
        countryCounts[i.country] = (countryCounts[i.country] || 0) + 1;
        levelCounts[i.incident_level] = (levelCounts[i.incident_level] || 0) + 1;
    });
    
    return `Total: ${incidents.length} incidents, ${totalDeaths} deaths, ${totalAffected.toLocaleString()} affected.
Types: ${JSON.stringify(typeCounts)}.
Countries: ${Object.keys(countryCounts).join(', ')}.
Severity: ${JSON.stringify(levelCounts)}.
Latest: ${incidents[0]?.incident_name || 'N/A'}.`;
}

/**
 * Generate fallback summary without LLM - more detailed and specific
 */
function generateFallbackSummary(incidents) {
    if (incidents.length === 0) return 'No incidents match the current filters.';
    
    // Basic stats
    const totalDeaths = incidents.reduce((sum, i) => sum + (i.impact?.deaths || 0), 0);
    const totalAffected = incidents.reduce((sum, i) => sum + (i.impact?.affected || 0), 0);
    const totalDisplaced = incidents.reduce((sum, i) => sum + (i.impact?.displaced || 0), 0);
    
    // Detailed breakdown by type
    const typeCounts = {};
    const typeDeaths = {};
    incidents.forEach(i => {
        const type = i.incident_type || 'Unknown';
        typeCounts[type] = (typeCounts[type] || 0) + 1;
        typeDeaths[type] = (typeDeaths[type] || 0) + (i.impact?.deaths || 0);
    });
    
    // Breakdown by country
    const countryCounts = {};
    incidents.forEach(i => {
        countryCounts[i.country] = (countryCounts[i.country] || 0) + 1;
    });
    
    // Severity breakdown
    const severityCounts = { 4: 0, 3: 0, 2: 0, 1: 0 };
    incidents.forEach(i => {
        const level = i.incident_level || 1;
        if (severityCounts[level] !== undefined) severityCounts[level]++;
    });
    
    // Get top affected country
    const sortedCountries = Object.entries(countryCounts).sort((a, b) => b[1] - a[1]);
    const topCountry = sortedCountries[0];
    const top3Countries = sortedCountries.slice(0, 3);
    
    // Build detailed summary
    let summary = `📊 **Filtered Results: ${incidents.length} incident${incidents.length !== 1 ? 's' : ''}**\n\n`;
    
    // Impact summary
    summary += `💔 **Impact:** ${totalDeaths.toLocaleString()} death${totalDeaths !== 1 ? 's' : ''}, `;
    summary += `${formatNumber(totalAffected)} affected, ${formatNumber(totalDisplaced)} displaced\n\n`;
    
    // Type breakdown
    summary += `📋 **By Type:**\n`;
    Object.entries(typeCounts).sort((a, b) => b[1] - a[1]).forEach(([type, count]) => {
        const deaths = typeDeaths[type];
        summary += `  • ${type}: ${count} incident${count !== 1 ? 's' : ''} (${deaths} deaths)\n`;
    });
    
    // Severity breakdown
    summary += `\n⚠️ **By Severity:**\n`;
    if (severityCounts[4] > 0) summary += `  • Critical (L4): ${severityCounts[4]} - URGENT\n`;
    if (severityCounts[3] > 0) summary += `  • Major (L3): ${severityCounts[3]}\n`;
    if (severityCounts[2] > 0) summary += `  • Significant (L2): ${severityCounts[2]}\n`;
    if (severityCounts[1] > 0) summary += `  • Minor (L1): ${severityCounts[1]}\n`;
    
    // Countries
    summary += `\n🌍 **Top Countries:** ${top3Countries.map(([c, n]) => `${c} (${n})`).join(', ')}\n`;
    
    // Most severe incident
    const mostSevere = incidents.find(i => i.incident_level === 4);
    if (mostSevere) {
        summary += `\n🚨 **Most Severe:** ${mostSevere.incident_name} in ${mostSevere.country} `;
        summary += `(${mostSevere.impact?.deaths || 0} deaths)\n`;
    }
    
    // Recommendations based on data
    summary += `\n💡 **Analysis:** `;
    if (severityCounts[4] > 0) {
        summary += `${severityCounts[4]} critical incident${severityCounts[4] !== 1 ? 's' : ''} require${severityCounts[4] === 1 ? 's' : ''} immediate attention. `;
    }
    if (typeCounts['Flood'] && typeCounts['Flood'] > 2) {
        summary += `Multiple flood events indicate seasonal pattern. `;
    }
    if (typeCounts['Disease'] && typeCounts['Disease'] > 0) {
        summary += `Disease outbreaks require health monitoring. `;
    }
    
    return summary;
}

/**
 * Format large numbers
 */
function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

// Export for testing
window.Dashboard = {
    state,
    CONFIG,
    loadData,
    getFilteredIncidents,
    openModal,
    closeModal,
    showSummary,
    generateAISummary,
    updateTable,
    populateCountryFilter,
    toggleRow,
    buildIncidentSummary,
};
