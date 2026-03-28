"""Dashboard E2E Tests with Playwright."""

import pytest
import json
import os
from pathlib import Path


# Get dashboard directory
DASHBOARD_DIR = Path(__file__).parent.parent
STATIC_DIR = DASHBOARD_DIR / "static"
DATA_DIR = DASHBOARD_DIR / "data"


@pytest.fixture
def dashboard_url(dash_server):
    """Fixture providing dashboard URL."""
    return f"http://localhost:8000"


@pytest.fixture
def dash_server():
    """Start a simple HTTP server for the dashboard."""
    import http.server
    import socketserver
    import threading
    import time

    os.chdir(STATIC_DIR)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress logging

    with socketserver.TCPServer(("", 8000), Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.5)  # Wait for server to start
        yield "http://localhost:8000"


@pytest.fixture
def sample_incidents():
    """Load sample incident data."""
    incidents_file = DATA_DIR / "incidents.json"
    with open(incidents_file) as f:
        return json.load(f)


@pytest.fixture
def sample_diseases():
    """Load sample disease data."""
    disease_file = DATA_DIR / "disease-incidents.json"
    with open(disease_file) as f:
        return json.load(f)


class TestDashboardUI:
    """Test dashboard UI/UX with Playwright."""

    @pytest.mark.ui
    def test_page_loads_successfully(self, page, dashboard_url):
        """Test that the dashboard page loads without errors."""
        response = page.goto(dashboard_url)

        assert response.status == 200, "Page should load successfully"

        # Check title
        title = page.title()
        assert "Disaster Awareness Dashboard" in title

    @pytest.mark.ui
    def test_header_elements_present(self, page, dashboard_url):
        """Test that header elements are visible."""
        page.goto(dashboard_url)

        # Check logo
        logo = page.locator(".logo h1")
        assert logo.is_visible()
        assert "Disaster Awareness Dashboard" in logo.text_content()

        # Check refresh button
        refresh_btn = page.locator("#refreshBtn")
        assert refresh_btn.is_visible()

    @pytest.mark.ui
    def test_stats_bar_displayed(self, page, dashboard_url):
        """Test that stats bar shows all 4 stat cards."""
        page.goto(dashboard_url)

        # Wait for stats to load
        page.wait_for_timeout(1000)

        stat_cards = page.locator(".stat-card")
        count = stat_cards.count()

        assert count == 4, "Should have 4 stat cards"

        # Check labels
        assert page.locator('[data-i18n="totalIncidents"]').is_visible()
        assert page.locator('[data-i18n="critical"]').is_visible()
        assert page.locator('[data-i18n="significant"]').is_visible()
        assert page.locator('[data-i18n="disease"]').is_visible()

    @pytest.mark.ui
    def test_map_container_initialized(self, page, dashboard_url):
        """Test that map container is present."""
        page.goto(dashboard_url)

        map_container = page.locator("#map")
        assert map_container.is_visible()

        # Check Leaflet is initialized
        leaflet_container = page.locator(".leaflet-container")
        assert leaflet_container.is_visible()

    @pytest.mark.ui
    def test_filters_functional(self, page, dashboard_url):
        """Test that filter dropdowns are functional."""
        page.goto(dashboard_url)

        # Check filter selects exist
        type_filter = page.locator("#typeFilter")
        severity_filter = page.locator("#severityFilter")
        country_filter = page.locator("#countryGroupFilter")

        assert type_filter.is_visible()
        assert severity_filter.is_visible()
        assert country_filter.is_visible()

        # Test filtering
        type_filter.select_option("Flood")
        page.wait_for_timeout(500)

        # Verify selection
        assert type_filter.input_value() == "Flood"

    @pytest.mark.ui
    def test_recent_incidents_panel(self, page, dashboard_url):
        """Test recent incidents panel."""
        page.goto(dashboard_url)

        # Wait for data to load
        page.wait_for_timeout(1000)

        panel = page.locator(".panel-section:has-text('Recent Incidents')")
        assert panel.is_visible()

        # Check incident items loaded
        incident_items = page.locator(".incident-item")
        assert incident_items.count() > 0, "Should have recent incidents"

    @pytest.mark.ui
    def test_disease_chart_present(self, page, dashboard_url):
        """Test disease chart is rendered."""
        page.goto(dashboard_url)

        # Wait for charts
        page.wait_for_timeout(1000)

        disease_chart = page.locator("#diseaseChart")
        assert disease_chart.is_visible()

    @pytest.mark.ui
    def test_type_chart_present(self, page, dashboard_url):
        """Test incident type chart is rendered."""
        page.goto(dashboard_url)

        # Wait for charts
        page.wait_for_timeout(1000)

        type_chart = page.locator("#typeChart")
        assert type_chart.is_visible()

    @pytest.mark.ui
    def test_map_legend_visible(self, page, dashboard_url):
        """Test map legend is displayed."""
        page.goto(dashboard_url)

        legend = page.locator(".map-legend")
        assert legend.is_visible()

        # Check legend items
        assert legend.locator("text=Critical").is_visible()
        assert legend.locator("text=Major").is_visible()
        assert legend.locator("text=Significant").is_visible()
        assert legend.locator("text=Minor").is_visible()


class TestDashboardInteraction:
    """Test dashboard interactions."""

    @pytest.mark.ui
    def test_refresh_button_clickable(self, page, dashboard_url):
        """Test refresh button can be clicked."""
        page.goto(dashboard_url)

        refresh_btn = page.locator("#refreshBtn")
        assert refresh_btn.is_enabled()

        # Click and verify no errors
        refresh_btn.click()
        page.wait_for_timeout(500)

    @pytest.mark.ui
    def test_modal_opens_on_incident_click(self, page, dashboard_url):
        """Test that clicking an incident opens the modal."""
        page.goto(dashboard_url)

        # Wait for incidents to load
        page.wait_for_timeout(1000)

        # Click first incident
        first_incident = page.locator(".incident-item").first
        first_incident.click()

        # Check modal opens
        modal = page.locator("#incidentModal")
        page.wait_for_selector(".modal.active", timeout=3000)

        assert modal.locator(".modal-content").is_visible()

    @pytest.mark.ui
    def test_modal_close_on_backdrop_click(self, page, dashboard_url):
        """Test modal closes when backdrop is clicked."""
        page.goto(dashboard_url)

        # Wait for incidents to load
        page.wait_for_timeout(1000)

        # Open modal
        page.locator(".incident-item").first.click()
        page.wait_for_selector(".modal.active", timeout=3000)

        # Click backdrop
        page.locator(".modal-backdrop").click()

        # Wait for modal to close
        page.wait_for_timeout(500)

        assert not page.locator("#incidentModal.modal.active").is_visible()

    @pytest.mark.ui
    def test_modal_close_on_escape(self, page, dashboard_url):
        """Test modal closes on Escape key."""
        page.goto(dashboard_url)

        # Wait for incidents to load
        page.wait_for_timeout(1000)

        # Open modal
        page.locator(".incident-item").first.click()
        page.wait_for_selector(".modal.active", timeout=3000)

        # Press Escape
        page.keyboard.press("Escape")

        # Wait for modal to close
        page.wait_for_timeout(500)

        assert not page.locator("#modal.active").is_visible()


class TestDashboardData:
    """Test dashboard data loading."""

    @pytest.mark.ui
    def test_data_loads_correctly(
        self, page, dashboard_url, sample_incidents, sample_diseases
    ):
        """Test that incident data loads and displays correctly."""
        page.goto(dashboard_url)

        # Wait for data to load
        page.wait_for_timeout(1500)

        # Check total count (should be len of both files)
        total_el = page.locator("#totalIncidents")
        total_text = total_el.text_content()
        expected_total = len(sample_incidents) + len(sample_diseases)

        assert int(total_text) == expected_total

    @pytest.mark.ui
    def test_critical_incidents_count(
        self, page, dashboard_url, sample_incidents, sample_diseases
    ):
        """Test critical incidents count is correct."""
        page.goto(dashboard_url)

        page.wait_for_timeout(1500)

        critical_el = page.locator("#criticalIncidents")
        critical_count = int(critical_el.text_content())

        # Count critical (level 4) from sample data
        all_incidents = sample_incidents + sample_diseases
        expected = sum(1 for i in all_incidents if i.get("incident_level") == 4)

        assert critical_count == expected


class TestDashboardResponsive:
    """Test dashboard responsive design."""

    @pytest.mark.ui
    def test_mobile_view(self, page, dashboard_url):
        """Test dashboard is usable on mobile."""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})

        page.goto(dashboard_url)

        # Page should still be usable
        assert page.locator(".header").is_visible()
        assert page.locator(".stats-bar").is_visible()

        # Stats should stack
        stat_cards = page.locator(".stat-card")
        assert stat_cards.count() == 4

    @pytest.mark.ui
    def test_tablet_view(self, page, dashboard_url):
        """Test dashboard on tablet."""
        page.set_viewport_size({"width": 768, "height": 1024})

        page.goto(dashboard_url)

        assert page.locator(".map-section").is_visible()
        assert page.locator(".side-panel").is_visible()


class TestDashboardAccessibility:
    """Test dashboard accessibility."""

    @pytest.mark.ui
    def test_aria_labels_present(self, page, dashboard_url):
        """Test ARIA labels are present for accessibility."""
        page.goto(dashboard_url)

        # Check modal close has aria-label
        modal_close = page.locator(".modal-close")
        assert modal_close.get_attribute("aria-label") is not None

    @pytest.mark.ui
    def test_color_contrast(self, page, dashboard_url):
        """Test basic color contrast (visual check in tests)."""
        page.goto(dashboard_url)

        # This is a basic test - actual contrast should be verified visually
        # or with specialized accessibility testing tools
        body_bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        text_color = page.evaluate("getComputedStyle(document.body).color")

        assert body_bg != text_color, "Background and text should have different colors"


class TestDashboardPerformance:
    """Test dashboard performance."""

    @pytest.mark.ui
    def test_page_loads_quickly(self, page, dashboard_url):
        """Test page loads within reasonable time."""
        import time

        start = time.time()
        page.goto(dashboard_url)
        load_time = time.time() - start

        # Should load within 5 seconds
        assert load_time < 5, f"Page took {load_time}s to load"

    @pytest.mark.ui
    def test_no_console_errors(self, page, dashboard_url):
        """Test there are no console errors."""
        console_errors = []

        page.on(
            "console",
            lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None
            ),
        )

        page.goto(dashboard_url)
        page.wait_for_timeout(1000)

        # Filter out known non-critical errors
        critical_errors = [e for e in console_errors if "Failed to load" not in e]

        assert len(critical_errors) == 0, f"Console errors found: {critical_errors}"
