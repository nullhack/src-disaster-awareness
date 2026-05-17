"""Tests for empty_input_produces_empty_output."""

from disaster_surveillance_reporter.correlation.correlate import Correlator


def test_empty_input_produces_empty_bundles():
    """Empty list of records yields empty list of bundles."""
    result = Correlator().correlate([])
    assert result == []
