/**
 * Disaster Awareness Dashboard - Main Application
 */

// Configuration
const CONFIG = {
    dataPath: '/data/',
    refreshInterval: 300000, // 5 minutes
    mapCenter: [15, 90], // Asia-Pacific focus
    mapZoom: 3,
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
    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadData();
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
        });
    }

    if (severityFilter) {
        severityFilter.addEventListener('change', (e) => {
            state.filters.severity = e.target.value;
            updateMapMarkers();
        });
    }

    if (countryGroupFilter) {
        countryGroupFilter.addEventListener('change', (e) => {
            state.filters.countryGroup = e.target.value;
            updateMapMarkers();
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
 * Load data from JSON files
 */
async function loadData() {
    showLoading(true);

    try {
        // Load incidents data
        const incidentsData = await fetchData('incidents.json');
        state.incidents = incidentsData || [];

        // Load disease data
        const diseaseData = await fetchData('disease-incidents.json');
        state.diseaseIncidents = diseaseData || [];

        // Update UI
        updateStats();
        updateMapMarkers();
        updateRecentIncidents();
        updateCharts();

        // Update timestamp
        updateLastUpdated();

    } catch (error) {
        console.error('Error loading data:', error);
        showError('Failed to load incident data');
    } finally {
        showLoading(false);
    }
}

/**
 * Fetch JSON data
 */
async function fetchData(filename) {
    try {
        const response = await fetch(CONFIG.dataPath + filename);
        if (!response.ok) return [];
        return await response.json();
    } catch (error) {
        console.warn(`Could not load ${filename}:`, error);
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

        return true;
    });
}

/**
 * Create map marker
 */
function createMarker(incident) {
    if (!incident.location?.coordinates?.lat || !incident.location?.coordinates?.lon) {
        return null;
    }

    const isDisease = incident.incident_type === 'Disease' || incident.incident_type === 'Disease Outbreak';
    const color = isDisease ? '#8b5cf6' : SEVERITY_COLORS[incident.incident_level] || '#3b82f6';

    const icon = L.divIcon({
        className: 'incident-marker',
        html: `<div style="
            width: 20px;
            height: 20px;
            background: ${color};
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 0 10px ${color};
        "></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
    });

    const marker = L.marker([incident.location.coordinates.lat, incident.location.coordinates.lon], { icon });

    // Create popup content
    const popupContent = createPopupContent(incident);
    marker.bindPopup(popupContent, {
        className: 'incident-popup',
        maxWidth: 300,
    });

    // Click to open modal
    marker.on('click', () => {
        // Popup shown by default
    });

    return marker;
}

/**
 * Create popup content
 */
function createPopupContent(incident) {
    const severity = getSeverityLabel(incident.incident_level);
    const color = SEVERITY_COLORS[incident.incident_level] || '#3b82f6';

    return `
        <div style="min-width: 200px;">
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
            <p style="font-size: 12px; color: #94a3b8; margin: 0;">
                ${incident.country} • ${incident.incident_type}
            </p>
            ${incident.impact?.deaths ? `<p style="font-size: 12px; margin: 8px 0 0 0;"><strong>Deaths:</strong> ${incident.impact.deaths.toLocaleString()}</p>` : ''}
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

    // Set details
    document.getElementById('modalCountry').textContent = incident.country;
    document.getElementById('modalType').textContent = incident.incident_type;
    document.getElementById('modalLevel').textContent = `Level ${incident.incident_level}`;
    document.getElementById('modalStatus').textContent = incident.status || 'Active';
    document.getElementById('modalDeaths').textContent = incident.impact?.deaths?.toLocaleString() || 'N/A';
    document.getElementById('modalAffected').textContent = incident.impact?.affected?.toLocaleString() || 'N/A';
    document.getElementById('modalDisplaced').textContent = incident.impact?.displaced?.toLocaleString() || 'N/A';
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

// Export for testing
window.Dashboard = {
    state,
    CONFIG,
    loadData,
    getFilteredIncidents,
    openModal,
    closeModal,
};
