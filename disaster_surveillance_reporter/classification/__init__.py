"""Classification rules for incident prioritization.

This module provides the rules loader for categorizing incidents by country groups,
priority levels, and reporting criteria.
"""

from disaster_surveillance_reporter.classification.rules import (  # noqa: F401
    COUNTRY_GROUPS,
    PRIORITY_MATRIX,
    RulesLoader,
)
