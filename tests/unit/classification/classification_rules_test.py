"""Tests for classification rules module."""

import pytest

from disaster_surveillance_reporter.classification import RulesLoader


@pytest.fixture
def rules_loader():
    """Create a RulesLoader instance for testing."""
    return RulesLoader()


def test_get_country_group_indonesia_should_be_a(rules_loader):
    """
    Given: A RulesLoader instance
    When: get_country_group('Indonesia') is called
    Then: Should return 'A'
    """
    result = rules_loader.get_country_group("Indonesia")
    assert result == "A"


def test_get_country_group_australia_should_be_b(rules_loader):
    """
    Given: A RulesLoader instance
    When: get_country_group('Australia') is called
    Then: Should return 'B'
    """
    result = rules_loader.get_country_group("Australia")
    assert result == "B"


def test_get_country_group_germany_should_be_c(rules_loader):
    """
    Given: A RulesLoader instance
    When: get_country_group('Germany') is called
    Then: Should return 'C' (unknown country defaults to C)
    """
    result = rules_loader.get_country_group("Germany")
    assert result == "C"


def test_get_country_group_japan_should_be_a(rules_loader):
    """
    Given: A RulesLoader instance
    When: get_country_group('Japan') is called
    Then: Should return 'A'
    """
    result = rules_loader.get_country_group("Japan")
    assert result == "A"


def test_get_priority_level_4_group_a_should_be_high(rules_loader):
    """
    Given: A RulesLoader instance
    When: get_priority(4, 'A') is called
    Then: Should return 'HIGH'
    """
    result = rules_loader.get_priority(4, "A")
    assert result == "HIGH"


def test_get_priority_level_3_group_a_should_be_high(rules_loader):
    """
    Given: A RulesLoader instance
    When: get_priority(3, 'A') is called
    Then: Should return 'HIGH'
    """
    result = rules_loader.get_priority(3, "A")
    assert result == "HIGH"


def test_get_priority_level_3_group_b_should_be_medium(rules_loader):
    """
    Given: A RulesLoader instance
    When: get_priority(3, 'B') is called
    Then: Should return 'MEDIUM'
    """
    result = rules_loader.get_priority(3, "B")
    assert result == "MEDIUM"


def test_get_priority_level_2_group_c_should_be_low(rules_loader):
    """
    Given: A RulesLoader instance
    When: get_priority(2, 'C') is called
    Then: Should return 'LOW'
    """
    result = rules_loader.get_priority(2, "C")
    assert result == "LOW"


def test_should_report_level_4_all_groups_should_be_true(rules_loader):
    """
    Given: A RulesLoader instance
    When: should_report(4, any_group) is called
    Then: Should return True for all groups
    """
    assert rules_loader.should_report(4, "A") is True
    assert rules_loader.should_report(4, "B") is True
    assert rules_loader.should_report(4, "C") is True


def test_should_report_level_1_group_c_should_be_false(rules_loader):
    """
    Given: A RulesLoader instance
    When: should_report(1, 'C') is called
    Then: Should return False (Group C Level 1 not reported)
    """
    result = rules_loader.should_report(1, "C")
    assert result is False


def test_should_report_level_1_group_a_should_be_true(rules_loader):
    """
    Given: A RulesLoader instance
    When: should_report(1, 'A') is called
    Then: Should return True (Group A Level 1 reported for awareness)
    """
    result = rules_loader.should_report(1, "A")
    assert result is True


def test_should_report_level_2_group_c_should_be_false(rules_loader):
    """
    Given: A RulesLoader instance
    When: should_report(2, 'C') is called
    Then: Should return False (Group C Level 2 not reported)
    """
    result = rules_loader.should_report(2, "C")
    assert result is False
