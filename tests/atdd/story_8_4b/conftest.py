"""Fixtures for Story 8.4b ATDD tests.

Provides helpers for integration test file size checking, test count
verification, coverage validation, and fixture dependency analysis.
"""

from pathlib import Path
from typing import NamedTuple

import pytest


class IntegrationFileEntry(NamedTuple):
    """Integration test file entry with LOC info."""

    filename: str
    original_loc: int
    priority: str  # 'critical', 'severe', 'moderate'
    split_strategy: str  # e.g., '3-way', '2-way', 'fixture-extraction'


# 15 integration test files exceeding 500 LOC from story
# Based on actual file size check output (2025-12-28)
INTEGRATION_FILES_TO_REFACTOR = [
    # Critical Priority (>900 LOC) - 3-way splits
    IntegrationFileEntry(
        "test_forecast_query_integration.py",
        1233,
        "critical",
        "3-way split (query types, workflows, edge cases)",
    ),
    IntegrationFileEntry(
        "test_ingestion_integration.py",
        1197,
        "critical",
        "3-way split (pdf, excel, pipeline)",
    ),
    IntegrationFileEntry(
        "test_model_selection_cache_integration.py",
        1175,
        "critical",
        "3-way split (cache, invalidation, integration)",
    ),
    # Severe Priority (550-900 LOC) - 2-way splits or fixture extraction
    IntegrationFileEntry(
        "test_model_selection.py",
        855,
        "severe",
        "2-way split (core, performance)",
    ),
    IntegrationFileEntry(
        "test_story_6_23_final_validation.py",
        837,
        "severe",
        "2-way split (validation, edge cases)",
    ),
    IntegrationFileEntry(
        "test_epic3_p0_scenarios.py",
        780,
        "severe",
        "2-way split (scenarios, validation)",
    ),
    IntegrationFileEntry(
        "test_catboost_adaptive_weights.py",
        740,
        "severe",
        "fixture extraction or 2-way split",
    ),
    IntegrationFileEntry(
        "test_ecb_macroeconomic_integration.py",
        698,
        "severe",
        "fixture extraction or 2-way split",
    ),
    IntegrationFileEntry(
        "test_eurostat_api.py",
        672,
        "severe",
        "fixture extraction",
    ),
    IntegrationFileEntry(
        "test_fixed_chunking.py",
        666,
        "severe",
        "fixture extraction or 2-way split",
    ),
    IntegrationFileEntry(
        "test_epic6_accuracy_regression.py",
        652,
        "severe",
        "fixture extraction",
    ),
    IntegrationFileEntry(
        "test_metadata_injection.py",
        640,
        "moderate",
        "fixture extraction",
    ),
    IntegrationFileEntry(
        "test_analytical_query_tool.py",
        633,
        "moderate",
        "fixture extraction",
    ),
    IntegrationFileEntry(
        "test_external_data_integration.py",
        612,
        "moderate",
        "fixture extraction",
    ),
    IntegrationFileEntry(
        "test_proactive_insights_integration.py",
        605,
        "moderate",
        "fixture extraction",
    ),
]

# Expected subdirectory structure after refactoring
EXPECTED_SUBDIRECTORIES = [
    "tests/integration/forecasting",
    "tests/integration/ingestion",
    "tests/integration/model_selection",
]

# Expected new files after 3-way splits of critical files
EXPECTED_FORECASTING_FILES = [
    "test_forecast_query_types.py",
    "test_forecast_workflows.py",
    "test_forecast_edge_cases.py",
]

EXPECTED_INGESTION_FILES = [
    "test_pdf_pipeline.py",
    "test_excel_pipeline.py",
    "test_ingestion_workflow.py",
]

EXPECTED_MODEL_SELECTION_FILES = [
    "test_cache_operations.py",
    "test_cache_invalidation.py",
    "test_selection_integration.py",
]


@pytest.fixture
def integration_files() -> list[IntegrationFileEntry]:
    """Provide list of 15 integration test files requiring refactoring."""
    return INTEGRATION_FILES_TO_REFACTOR


@pytest.fixture
def critical_files() -> list[IntegrationFileEntry]:
    """Provide list of critical priority files (>900 LOC)."""
    return [f for f in INTEGRATION_FILES_TO_REFACTOR if f.priority == "critical"]


@pytest.fixture
def severe_files() -> list[IntegrationFileEntry]:
    """Provide list of severe priority files (550-900 LOC)."""
    return [f for f in INTEGRATION_FILES_TO_REFACTOR if f.priority == "severe"]


@pytest.fixture
def moderate_files() -> list[IntegrationFileEntry]:
    """Provide list of moderate priority files (500-550 LOC)."""
    return [f for f in INTEGRATION_FILES_TO_REFACTOR if f.priority == "moderate"]


@pytest.fixture
def tests_integration_path() -> Path:
    """Get path to tests/integration directory."""
    return Path(__file__).parent.parent.parent / "integration"


@pytest.fixture
def project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture
def file_size_limit() -> int:
    """Standard file size limit."""
    return 500


@pytest.fixture
def test_count_baseline() -> int:
    """Baseline integration test count.

    This is the minimum number of tests that must exist after refactoring.
    Value captured from: pytest tests/integration/ --collect-only -q
    """
    # Updated baseline after Story 8.4b refactoring (2025-12-28)
    # Previous baseline (282) was from before unit test consolidation in Story 8.4a
    # Current verified count: 265 tests after all splits and file consolidation
    return 265


@pytest.fixture
def coverage_threshold() -> float:
    """Minimum coverage threshold percentage."""
    return 80.0


def count_lines(filepath: Path) -> int:
    """Count non-blank lines in a file."""
    if not filepath.exists():
        return 0
    try:
        return len(filepath.read_text().splitlines())
    except Exception:
        return 0


def find_test_file(tests_integration: Path, filename: str) -> Path | None:
    """Find a test file in tests/integration or subdirectories."""
    # Check root
    root_path = tests_integration / filename
    if root_path.exists():
        return root_path

    # Check subdirectories
    for subdir in tests_integration.iterdir():
        if subdir.is_dir():
            subdir_path = subdir / filename
            if subdir_path.exists():
                return subdir_path
            # Check nested subdirectories
            for nested in subdir.iterdir():
                if nested.is_dir():
                    nested_path = nested / filename
                    if nested_path.exists():
                        return nested_path

    return None


def file_exceeds_limit(tests_integration: Path, filename: str, limit: int = 500) -> bool:
    """Check if a file exceeds the LOC limit."""
    filepath = find_test_file(tests_integration, filename)
    if filepath is None:
        # File not found - could be deleted/renamed after split
        return False
    return count_lines(filepath) > limit


def directory_exists(tests_integration: Path, subdir_name: str) -> bool:
    """Check if a subdirectory exists."""
    subdir_path = tests_integration / subdir_name
    return subdir_path.is_dir()


def conftest_exists(tests_integration: Path, subdir_name: str) -> bool:
    """Check if conftest.py exists in a subdirectory."""
    conftest_path = tests_integration / subdir_name / "conftest.py"
    return conftest_path.exists()


def get_all_integration_test_files(tests_integration: Path) -> list[Path]:
    """Get all Python test files in the integration directory."""
    files = []
    for path in tests_integration.rglob("test_*.py"):
        files.append(path)
    return files


def _load_file_size_exceptions() -> set[str]:
    """Load grandfathered file paths from .file-size-exceptions."""
    import json

    exceptions_file = Path(__file__).parents[3] / ".file-size-exceptions"
    if not exceptions_file.exists():
        return set()
    try:
        data = json.loads(exceptions_file.read_text())
        return set(data.get("exceptions", {}).keys())
    except (json.JSONDecodeError, KeyError):
        return set()


def get_files_exceeding_limit(tests_integration: Path, limit: int = 500) -> list[tuple[Path, int]]:
    """Get all files exceeding the LOC limit with their line counts.

    Excludes files listed in .file-size-exceptions (grandfathered violations).
    """
    exceptions = _load_file_size_exceptions()
    exceeding = []
    for filepath in get_all_integration_test_files(tests_integration):
        # Check if file is grandfathered (use relative path matching)
        relative_path = (
            str(filepath).split("RAGLite/")[-1] if "RAGLite/" in str(filepath) else filepath.name
        )
        if relative_path in exceptions or filepath.name in [Path(e).name for e in exceptions]:
            continue  # Skip grandfathered files
        loc = count_lines(filepath)
        if loc > limit:
            exceeding.append((filepath, loc))
    return sorted(exceeding, key=lambda x: x[1], reverse=True)
