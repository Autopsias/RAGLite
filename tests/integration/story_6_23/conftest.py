"""Shared fixtures for Story 6.23 integration tests.

Marker Strategy:
- integration: All tests require Qdrant/PostgreSQL infrastructure
- preserve_collection: Read-only tests (skip cleanup overhead)
"""

from pathlib import Path

import pytest

# Mark all tests in this subdirectory with standard integration markers
# xdist_group prevents worker crashes from parallel subprocess execution
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="story_6_23_validation"),
]


@pytest.fixture
def validation_script_path():
    """Path to unified validation script."""
    script_path = (
        Path(__file__).parent.parent.parent.parent / "scripts" / "validate_forecasting_unified.py"
    )
    if not script_path.exists():
        pytest.skip(f"Validation script not found: {script_path}")
    return script_path


@pytest.fixture
def project_root():
    """Project root directory."""
    return Path(__file__).parent.parent.parent.parent
