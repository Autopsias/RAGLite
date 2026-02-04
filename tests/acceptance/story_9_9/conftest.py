"""
Conftest for Story 9.9 Acceptance Tests.

Story 9.9 validates the full Epic 9 classification pipeline meets all success criteria.
These tests are primarily validation-focused and require the complete pipeline to be
implemented and re-ingestion completed.
"""

import pytest


@pytest.fixture
def ground_truth_file_path() -> str:
    """Path to the ground truth dataset."""
    return "tests/fixtures/classification_ground_truth.json"


@pytest.fixture
def validation_report_path() -> str:
    """Path to the Epic 9 validation report."""
    return "docs/sprint-artifacts/epic-9-validation-report.md"


@pytest.fixture
def accuracy_validation_script() -> str:
    """Path to the accuracy validation script."""
    return "scripts/validate-classification-accuracy.py"


@pytest.fixture
def coverage_validation_script() -> str:
    """Path to the coverage validation script."""
    return "scripts/validate-classification-coverage.py"


@pytest.fixture
def expected_minimum_rows() -> int:
    """Expected minimum row count after re-ingestion (Story 9.7)."""
    return 78759


@pytest.fixture
def accuracy_thresholds() -> dict:
    """Accuracy thresholds for Epic 9 success criteria."""
    return {
        "period_type": 0.95,  # >= 95%
        "value_type": 0.90,  # >= 90%
        "entity_level": 0.90,  # >= 90%
    }


@pytest.fixture
def performance_threshold() -> float:
    """Maximum acceptable ingestion overhead percentage."""
    return 0.20  # < 20%
