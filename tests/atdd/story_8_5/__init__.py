"""Story 8.5 ATDD tests - Facade for backward compatibility.

These tests verify that deprecation warnings from RAGLite code are eliminated.

Test IDs:
- TEST-AC-8.5.1.x: historical_data parameter migration
- TEST-AC-8.5.2.x: Import path updates
- TEST-AC-8.5.3.x: Fixture marker cleanup (pytest 9.0 compatibility)
- TEST-AC-8.5.4.x: Full test suite coverage

Story: docs/stories/8-5-deprecation-cleanup.md
Epic: 8 - Technical Debt Reduction
"""

# Import all test classes from split modules
from .test_fixture_marker_cleanup import TestAC853FixtureMarkerCleanup
from .test_full_suite_coverage import TestAC854FullSuiteCoverage
from .test_historical_data_deprecation import TestAC851HistoricalDataDeprecation
from .test_import_path_deprecation import TestAC852ImportPathDeprecation
from .test_summary import TestAC85DeprecationCleanupSummary

__all__ = [
    "TestAC851HistoricalDataDeprecation",
    "TestAC852ImportPathDeprecation",
    "TestAC853FixtureMarkerCleanup",
    "TestAC854FullSuiteCoverage",
    "TestAC85DeprecationCleanupSummary",
]
