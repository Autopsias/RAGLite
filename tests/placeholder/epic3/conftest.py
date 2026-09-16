"""Shared fixtures for Epic 3 integration tests."""

import json
from pathlib import Path

import pytest

# Module-level markers for all Epic 3 tests
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


@pytest.fixture
def load_ground_truth_analytical():
    """Load analytical queries from tests/fixtures/ground_truth_analytical.json.

    Expected format:
    [
        {
            "query": "Calculate year-over-year revenue growth between Q3 2023 and Q3 2024",
            "expected_answer": "Revenue grew 20% year-over-year...",
            "expected_keywords": ["20%", "growth", "Q3 2023", "Q3 2024"],
            "category": "yoy_analysis"
        },
        ...
    ]
    """
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "ground_truth_analytical.json"

    if not fixture_path.exists():
        pytest.skip(f"Ground truth analytical dataset not found: {fixture_path}")

    with open(fixture_path) as f:
        data = json.load(f)

    return data


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests with appropriate markers for selective execution.

    Usage:
    - pytest -m p0                    # Run only P0 critical tests
    - pytest -m "p0 and unit"         # Run P0 unit tests only
    - pytest -m "p0 and integration"  # Run P0 integration tests only
    """
    for item in items:
        # Add story markers
        if "test_story_31" in item.nodeid.lower():
            item.add_marker(pytest.mark.story_3_1)
        elif "test_story_32" in item.nodeid.lower():
            item.add_marker(pytest.mark.story_3_2)
        elif "test_story_33" in item.nodeid.lower():
            item.add_marker(pytest.mark.story_3_3)
        elif "test_story_34" in item.nodeid.lower():
            item.add_marker(pytest.mark.story_3_4)
        elif "test_story_35" in item.nodeid.lower():
            item.add_marker(pytest.mark.story_3_5)
        elif "test_story_38" in item.nodeid.lower():
            item.add_marker(pytest.mark.story_3_8)
