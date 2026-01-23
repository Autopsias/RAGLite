"""Shared fixtures for Eurostat integration tests."""

import pytest

# Task 0.4: Added external_api marker + 60s timeout for API tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.preserve_collection,
    pytest.mark.external_api,
    pytest.mark.timeout(60),
]
