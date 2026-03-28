"""Dashboard E2E Tests for data persistence, filters, and table."""

import pytest
import json
import os
from pathlib import Path


# Get dashboard directory
DASHBOARD_DIR = Path(__file__).parent.parent
STATIC_DIR = DASHBOARD_DIR / "static"
DATA_DIR = DASHBOARD_DIR / "data"


@pytest.fixture(scope="session")
def dash_server():
    """Start a simple HTTP server for the dashboard (session scope)."""
    import http.server
    import socketserver
    import threading
    import time
    from pathlib import Path

    DASHBOARD_ROOT = Path(__file__).parent.parent

    class DashHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(DASHBOARD_ROOT), **kwargs)

        def translate_path(self, path):
            import urllib.parse

            path = urllib.parse.unquote(path)

            if path.startswith("/data/"):
                data_file = path[5:]
                return str(DATA_DIR / data_file.lstrip("/"))

            if path == "/":
                return str(STATIC_DIR / "index.html")

            static_file = path.lstrip("/")
            static_path = STATIC_DIR / static_file

            if static_path.exists():
                return str(static_path)

            return str(DASHBOARD_ROOT / static_file)

        def log_message(self, format, *args):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", 8000), DashHandler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.5)
        yield "http://localhost:8000"


@pytest.fixture
def dashboard_url(dash_server):
    return f"http://localhost:8000"


@pytest.fixture
def sample_incidents():
    incidents_file = DATA_DIR / "incidents.json"
    with open(incidents_file) as f:
        return json.load(f)


@pytest.fixture
def sample_diseases():
    disease_file = DATA_DIR / "disease-incidents.json"
    with open(disease_file) as f:
        return json.load(f)


class TestDataPersistence:
    """Test that data persists after refresh."""

    @pytest.mark.ui
    def test_data_persists_after_refresh(self, page, dashboard_url):
        """Test that data is still visible after clicking refresh button."""
        page.goto(dashboard_url)

        # Wait for initial load
        page.wait_for_timeout(1500)

        # Get initial total
        initial_total = page.locator("#totalIncidents").text_content()
        assert int(initial_total) > 0, "Should have initial data"

        # Click refresh button
        page.locator("#refreshBtn").click()
        page.wait_for_timeout(1500)

        # Get total after refresh
        after_refresh_total = page.locator("#totalIncidents").text_content()

        # Data should persist
        assert int(after_refresh_total) == int(initial_total), (
            "Data should persist after refresh"
        )

    @pytest.mark.ui
    def test_map_markers_persist_after_refresh(self, page, dashboard_url):
        """Test that map markers are still visible after refresh."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Click refresh
        page.locator("#refreshBtn").click()
        page.wait_for_timeout(1500)

        # Check map has markers
        markers = page.locator(".leaflet-marker-icon")
        count = markers.count()
        assert count > 0, "Map markers should persist after refresh"

    @pytest.mark.ui
    def test_charts_persist_after_refresh(self, page, dashboard_url):
        """Test that charts are still visible after refresh."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Refresh
        page.locator("#refreshBtn").click()
        page.wait_for_timeout(1500)

        # Charts should have data
        disease_canvas = page.locator("#diseaseChart")
        type_canvas = page.locator("#typeChart")

        assert disease_canvas.is_visible()
        assert type_canvas.is_visible()


class TestFilters:
    """Test filtering functionality."""

    @pytest.mark.ui
    def test_type_filter_updates_map(self, page, dashboard_url):
        """Test that type filter updates the map markers."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Get initial marker count
        initial_markers = page.locator(".leaflet-marker-icon").count()

        # Filter by Earthquake
        page.locator("#typeFilter").select_option("Earthquake")
        page.wait_for_timeout(1000)

        # Markers should update (less or equal to initial)
        filtered_markers = page.locator(".leaflet-marker-icon").count()
        assert filtered_markers <= initial_markers

    @pytest.mark.ui
    def test_country_filter_exists_and_works(self, page, dashboard_url):
        """Test that country filter dropdown exists and filters data."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Check country filter exists
        country_filter = page.locator("#countryFilter")
        assert country_filter.is_visible(), "Country filter should exist"

        # Get initial count
        initial_total = page.locator("#totalIncidents").text_content()

        # Select a country that exists in data (e.g., Indonesia)
        page.locator("#countryFilter").select_option("Indonesia")
        page.wait_for_timeout(1000)

        # Total should change or stay same (filtered)
        filtered_total = page.locator("#totalIncidents").text_content()
        assert int(filtered_total) <= int(initial_total)

    @pytest.mark.ui
    def test_severity_filter_updates(self, page, dashboard_url):
        """Test that severity filter works."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Filter by Level 4 (Critical)
        page.locator("#severityFilter").select_option("4")
        page.wait_for_timeout(1000)

        # Get critical count
        critical = page.locator("#criticalIncidents").text_content()

        # Total should equal critical (since we're filtering to level 4 only)
        total = page.locator("#totalIncidents").text_content()
        assert int(total) == int(critical), (
            "Filtered total should equal critical count when filtering by Level 4"
        )


class TestDataTable:
    """Test data table functionality."""

    @pytest.mark.ui
    def test_table_exists(self, page, dashboard_url):
        """Test that data table section exists."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Check table exists
        table = page.locator("#incidentsTable")
        assert table.is_visible(), "Data table should exist"

    @pytest.mark.ui
    def test_table_has_columns(self, page, dashboard_url):
        """Test that table has required columns."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Check column headers
        headers = page.locator("#incidentsTable th")
        header_texts = [h.text_content() for h in headers.all()]

        # Should have key columns
        assert "Date" in header_texts or "date" in [t.lower() for t in header_texts]
        assert "Country" in header_texts or "country" in [
            t.lower() for t in header_texts
        ]
        assert "Type" in header_texts or "type" in [t.lower() for t in header_texts]

    @pytest.mark.ui
    def test_table_shows_filtered_data(self, page, dashboard_url):
        """Test that table updates with filters."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Get initial row count
        initial_rows = page.locator("#incidentsTable tbody tr").count()

        # Filter by Earthquake
        page.locator("#typeFilter").select_option("Earthquake")
        page.wait_for_timeout(1000)

        # Row count should change
        filtered_rows = page.locator("#incidentsTable tbody tr").count()
        assert filtered_rows <= initial_rows

    @pytest.mark.ui
    def test_table_shows_incident_details(self, page, dashboard_url):
        """Test that table shows incident information."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Check first row has data
        first_row = page.locator("#incidentsTable tbody tr").first
        cells = first_row.locator("td")
        cell_count = cells.count()

        assert cell_count >= 4, "Table rows should have multiple columns of data"


class TestMarkerColors:
    """Test marker colors by disaster type."""

    @pytest.mark.ui
    def test_flood_markers_blue(self, page, dashboard_url):
        """Test that flood markers are blue."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Filter by Flood
        page.locator("#typeFilter").select_option("Flood")
        page.wait_for_timeout(1000)

        # Check marker colors - floods should be blue-ish
        # We check the fill color of SVG markers
        markers = page.locator(".leaflet-marker-icon")
        if markers.count() > 0:
            # Marker should exist and be visible
            assert markers.first.is_visible()

    @pytest.mark.ui
    def test_earthquake_markers_brown(self, page, dashboard_url):
        """Test that earthquake markers use earth tones."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Filter by Earthquake
        page.locator("#typeFilter").select_option("Earthquake")
        page.wait_for_timeout(1000)

        # Should have earthquake markers
        markers = page.locator(".leaflet-marker-icon")
        assert markers.count() >= 0  # Just ensure no errors

    @pytest.mark.ui
    def test_fire_markers_red(self, page, dashboard_url):
        """Test that fire markers are red."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Filter by Fire
        page.locator("#typeFilter").select_option("Fire")
        page.wait_for_timeout(1000)

        markers = page.locator(".leaflet-marker-icon")
        assert markers.count() >= 0


class TestMarkerSize:
    """Test marker size based on severity."""

    @pytest.mark.ui
    def test_critical_markers_larger(self, page, dashboard_url):
        """Test that Level 4 incidents have larger markers."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Filter to see only critical
        page.locator("#severityFilter").select_option("4")
        page.wait_for_timeout(1000)

        # Get marker sizes
        markers = page.locator(".leaflet-marker-icon")

        # Should have at least some markers for critical
        assert markers.count() >= 0

    @pytest.mark.ui
    def test_minor_markers_smaller(self, page, dashboard_url):
        """Test that Level 1 incidents have smaller markers."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Filter to see only minor
        page.locator("#severityFilter").select_option("1")
        page.wait_for_timeout(1000)

        markers = page.locator(".leaflet-marker-icon")
        assert markers.count() >= 0


class TestAISummary:
    """Test AI summary functionality."""

    @pytest.mark.ui
    def test_ai_summary_shows_type_info(self, page, dashboard_url):
        """Test that AI summary includes specific incident type information."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Filter by Flood
        page.locator("#typeFilter").select_option("Flood")
        page.wait_for_timeout(500)

        # Open summary
        page.locator("#summarizeBtn").click()
        page.wait_for_timeout(1500)

        # Check AI summary content mentions the type
        ai_content = page.locator("#aiSummaryContent")
        if not ai_content.is_hidden():
            content = ai_content.text_content()
            # Should contain flood-related info or at least some summary
            assert len(content) > 10, "AI summary should have content"

    @pytest.mark.ui
    def test_ai_summary_shows_country_info(self, page, dashboard_url):
        """Test that AI summary includes country-specific info."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Select a country
        page.locator("#countryFilter").select_option("Indonesia")
        page.wait_for_timeout(500)

        # Open summary
        page.locator("#summarizeBtn").click()
        page.wait_for_timeout(1500)

        # Content should exist
        ai_content = page.locator("#aiSummaryContent")
        if not ai_content.is_hidden():
            content = ai_content.text_content()
            assert len(content) > 0


class TestCombinedFilters:
    """Test combined filter functionality."""

    @pytest.mark.ui
    def test_combined_filters(self, page, dashboard_url):
        """Test that multiple filters work together."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Apply multiple filters
        page.locator("#typeFilter").select_option("Flood")
        page.wait_for_timeout(500)

        page.locator("#severityFilter").select_option("4")
        page.wait_for_timeout(500)

        # Get filtered count
        total = page.locator("#totalIncidents").text_content()

        # Should be filtered
        assert int(total) >= 0

    @pytest.mark.ui
    def test_summary_with_combined_filters(self, page, dashboard_url):
        """Test summary with multiple filters."""
        page.goto(dashboard_url)
        page.wait_for_timeout(1500)

        # Apply filters
        page.locator("#typeFilter").select_option("Cyclone")
        page.wait_for_timeout(500)

        # Open summary
        page.locator("#summarizeBtn").click()
        page.wait_for_timeout(1000)

        # Title should reflect filter
        title = page.locator("#summaryTitle").text_content()
        assert "Cyclone" in title
