"""External Data Source Health Checks - Facade for backward compatibility.

This module provides health check tests for external data sources used in RAGLite.
All tests hit REAL APIs and are excluded from regular test runs.

Usage:
    pytest tests/health/external_data/ -v --tb=short -m ""

CI Trigger: PRs modifying raglite/external_data/** or tests/health/**

Story: 6.9 - External Data Source Client Fixes
Created: 2025-12-08
"""

# Import test classes from split modules
from .test_atic import TestATICHealth
from .test_basegov import TestBaseGovHealth
from .test_bpstat import TestBPstatHealth
from .test_commodities import TestCommoditiesHealth
from .test_eu_oil_bulletin import TestEUOilBulletinHealth
from .test_ine import TestINEHealth
from .test_ipma import TestIPMAHealth
from .test_omie import TestOMIEHealth
from .test_summary import TestHealthSummary

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
