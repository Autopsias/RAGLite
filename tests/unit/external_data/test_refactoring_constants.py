"""Constants for Story 7.1 refactoring acceptance tests.

Extracted from test_refactoring_acceptance.py to keep file size under 500 LOC.
"""

# Expected modules after refactoring
# NOTE (2025-12-18): test_basegov_story695.py split out separately for file size limits
EXPECTED_MODULES = [
    "test_ine_client.py",
    "test_basegov_client.py",
    "test_basegov_story695.py",  # Split from test_basegov_client.py for file size limits
    "test_bpstat_client.py",
    "test_omie_client.py",
    "test_oil_bulletin_client.py",
    "test_commodities_client.py",
    "test_atic_client.py",
    "test_ipma_client.py",
    "test_exceptions.py",
]

# Expected test classes per module (from story analysis)
# NOTE (2025-12-18): Updated to reflect actual refactoring structure
EXPECTED_TEST_CLASSES = {
    "test_ine_client.py": [
        "TestINEClient",
        "TestINEDateFiltering",
        "TestINEClientAdditional",
        "TestStory68INEExtensions",
    ],
    "test_basegov_client.py": [
        "TestBaseGovClient",
        "TestBaseGovClientAdditional",
        "TestBaseGovClientCoverage",
    ],
    "test_basegov_story695.py": [
        "TestBaseGovStory695",  # Extracted to separate file for file size limits
    ],
    "test_bpstat_client.py": [
        "TestBPstatClient",
        "TestBPstatClientAdditional",
        "TestBPstatStory693",
        "TestStory68BPstatExtensions",
    ],
    "test_omie_client.py": [
        "TestOMIEClient",
        "TestOMIEStory692",
        "TestOMIEClientAdditional",
    ],
    "test_oil_bulletin_client.py": [
        "TestEUOilBulletinClient",
        "TestEUOilBulletinAdditional",
        "TestEUOilBulletinStory694",
    ],
    "test_commodities_client.py": [
        "TestCommoditiesURLFix",
        "TestCommoditiesClient",
        "TestCommoditiesClientAdditional",
        "TestCommoditiesClientCoverage",
    ],
    "test_atic_client.py": [
        "TestATICClient",
        "TestATICClientAdditional",
    ],
    "test_ipma_client.py": [
        "TestIPMAClient",
        "TestIPMAClientAdditional",
        "TestIPMAClientCoverage",
    ],
    "test_exceptions.py": [
        "TestExceptions",
        "TestRateLimitHandling",
    ],
}

# File size limits (from .claude/rules/file-size-limits.md)
HARD_LIMIT_LOC = 500
IDEAL_MAX_LOC = 400
CONFTEST_MAX_LOC = 200

# Baseline test count from original file (Story 8.2 refactoring added tests)
# Note: Original estimate was 131, updated to 197, then 188, now 323 after Story 8.2 consolidation
# (2025-12-29): Updated to 323 to reflect actual test count after Story 8.2 refactoring
# Uses >= comparison to allow legitimate test additions while catching deletions
BASELINE_CLIENT_TEST_COUNT = 323
