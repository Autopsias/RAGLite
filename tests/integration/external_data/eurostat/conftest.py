"""Shared fixtures for Eurostat integration tests."""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.preserve_collection]
