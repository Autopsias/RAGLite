"""Shared fixtures for chunking integration tests."""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.order(21),
    pytest.mark.slow,
]
