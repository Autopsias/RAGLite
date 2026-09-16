"""Fixtures for metadata injection tests."""

import os

import pytest


def _has_valid_mistral_api_key() -> bool:
    """Check if MISTRAL_API_KEY is set and looks valid (not placeholder/empty)."""
    key = os.getenv("MISTRAL_API_KEY", "")
    # Skip if empty, placeholder, or too short to be valid
    if not key or len(key) < 20 or key in ("placeholder", "test", "dummy", "none"):
        return False
    return True


@pytest.fixture
def has_mistral_key() -> bool:
    """Fixture to check for valid Mistral API key."""
    return _has_valid_mistral_api_key()
