"""ATDD Test Configuration.

This module configures pytest for ATDD (Acceptance Test-Driven Development) tests.
ATDD tests verify acceptance criteria before implementation (RED phase) and
confirm they pass after implementation (GREEN phase).
"""


def pytest_configure(config):
    """Register custom markers for ATDD tests."""
    config.addinivalue_line("markers", "atdd: ATDD acceptance test")
    config.addinivalue_line("markers", "story_8_4b: Story 8.4b integration test file consolidation")
    config.addinivalue_line("markers", "story_8_5: Story 8.5 deprecation cleanup")
