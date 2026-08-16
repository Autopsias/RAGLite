"""Fixtures for Story 8.4a-3 ATDD tests.

Provides helpers for file size checking and test count verification.
"""

from pathlib import Path
from typing import NamedTuple

import pytest


class FileEntry(NamedTuple):
    """Test file entry with LOC info."""

    filename: str
    original_loc: int
    location: str  # 'root' or subdirectory name


# 31 moderate priority files from story (500-864 LOC)
MODERATE_PRIORITY_FILES = [
    FileEntry("test_forecast_query_tool.py", 864, "forecasting"),
    FileEntry("test_parallel_ingestion.py", 858, "ingestion"),
    FileEntry("test_eurostat_indicators_edge_cases.py", 815, "external_data"),
    FileEntry("test_anomaly_detection.py", 811, "insights"),
    FileEntry("test_housing_transactions.py", 767, "external_data"),
    FileEntry("test_multi_metric_validation.py", 760, "forecasting"),
    FileEntry("test_model_selection_utils.py", 750, "forecasting/model_selection"),
    FileEntry("test_arima_model.py", 745, "forecasting"),
    FileEntry("test_eurostat_indicators.py", 718, "external_data"),
    FileEntry("test_story_7_4_expanded_coverage.py", 661, "root"),
    FileEntry("test_retrieval.py", 653, "retrieval"),
    FileEntry("test_safety_guard.py", 624, "shared"),
    FileEntry("test_arima_ets_models_expanded.py", 611, "forecasting"),
    FileEntry("test_mcp_model_routing.py", 595, "mcp"),
    FileEntry("test_auto_update.py", 568, "forecasting"),
    FileEntry("test_standard_layouts.py", 560, "ingestion"),
    FileEntry("test_catboost_integration.py", 555, "forecasting"),
    FileEntry("test_phase2_centralized_validation.py", 554, "root"),
    FileEntry("test_hybrid_search.py", 553, "retrieval"),
    FileEntry("test_proactive_insights_mcp.py", 551, "insights"),
    FileEntry("test_unit_inference.py", 550, "ingestion"),
    FileEntry("test_story_6_23_validation_unit.py", 542, "root"),
    FileEntry("test_ets_model.py", 541, "forecasting"),
    FileEntry("test_ecb_macroeconomic.py", 539, "external_data"),
    FileEntry("test_scripts_accuracy_utils.py", 533, "root"),
    FileEntry("test_synthesis_agent.py", 523, "retrieval"),
    FileEntry("test_ensemble_forecasting.py", 520, "forecasting"),
    FileEntry("test_regressor_config_story_6_16.py", 512, "forecasting"),
    FileEntry("test_base64_ingestion.py", 512, "ingestion"),
    FileEntry("test_refactoring_acceptance.py", 507, "external_data"),
    FileEntry("test_scheduler.py", 503, "forecasting"),
]


@pytest.fixture
def moderate_files() -> list[FileEntry]:
    """Provide list of 31 moderate priority files with original LOC."""
    return MODERATE_PRIORITY_FILES


@pytest.fixture
def tests_unit_path() -> Path:
    """Get path to tests/unit directory."""
    return Path(__file__).parent.parent.parent / "unit"


@pytest.fixture
def file_size_limit() -> int:
    """Standard file size limit."""
    return 500


def count_lines(filepath: Path) -> int:
    """Count non-blank lines in a file."""
    if not filepath.exists():
        return 0
    try:
        return len(filepath.read_text().splitlines())
    except Exception:
        return 0


def find_test_file(tests_unit: Path, filename: str) -> Path | None:
    """Find a test file in tests/unit or subdirectories."""
    # Check root
    root_path = tests_unit / filename
    if root_path.exists():
        return root_path

    # Check subdirectories
    for subdir in tests_unit.iterdir():
        if subdir.is_dir():
            subdir_path = subdir / filename
            if subdir_path.exists():
                return subdir_path
            # Check nested subdirectories (e.g., forecasting/model_selection)
            for nested in subdir.iterdir():
                if nested.is_dir():
                    nested_path = nested / filename
                    if nested_path.exists():
                        return nested_path

    return None


def file_exceeds_limit(tests_unit: Path, filename: str, limit: int = 500) -> bool:
    """Check if a file exceeds the LOC limit."""
    filepath = find_test_file(tests_unit, filename)
    if filepath is None:
        # File not found - could be deleted/renamed after split
        return False
    return count_lines(filepath) > limit


def get_split_files_for(tests_unit: Path, original_name: str) -> list[Path]:
    """Find potential split files based on original filename.

    For example, test_forecast_query_tool.py might be split into:
    - test_forecast_query_tool_part1.py
    - test_forecast_query_tool_part2.py
    Or moved to subdirectory:
    - forecasting/test_forecast_query_tool_part1.py
    """
    base_name = original_name.replace(".py", "")
    results = []

    # Search for split files in all directories
    for path in tests_unit.rglob("*.py"):
        if base_name in path.name and path.name != original_name:
            results.append(path)

    return results
