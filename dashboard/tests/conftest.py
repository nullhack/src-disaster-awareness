"""Pytest configuration for dashboard tests."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "ui: UI tests with Playwright")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "dashboard: Dashboard-specific tests")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "en-US",
    }
