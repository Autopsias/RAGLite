"""External Data Source Health Checks

Run on PRs that modify external data code to detect API changes before merging.
These tests hit REAL APIs - excluded from regular test runs.

Usage:
    pytest tests/health/test_external_data_health.py -v --tb=short -m ""

CI Trigger: PRs modifying raglite/external_data/** or tests/health/**

Story: 6.9 - External Data Source Client Fixes
Created: 2025-12-08

Refactored: 2025-01-06 - Split into external_data/ package for better maintainability
"""

import pytest

from tests.health.external_data import (
    TestATICHealth,
    TestBaseGovHealth,
    TestBPstatHealth,
    TestCommoditiesHealth,
    TestEUOilBulletinHealth,
    TestHealthSummary,
    TestINEHealth,
    TestIPMAHealth,
    TestOMIEHealth,
)

# All health check tests hit real external APIs - exclude from regular CI runs
# Run manually with: pytest tests/health/ -m "" -v
pytestmark = [
    pytest.mark.health_check,
    pytest.mark.external_api,
]

__all__ = [
    "TestINEHealth",
    "TestCommoditiesHealth",
    "TestOMIEHealth",
    "TestBPstatHealth",
    "TestEUOilBulletinHealth",
    "TestBaseGovHealth",
    "TestIPMAHealth",
    "TestATICHealth",
    "TestHealthSummary",
]
