"""[P0] ATDD tests for AC-8.4b.1: All Integration Test Files Under 500 LOC.

Given 15 integration test files exceed the 500 LOC limit
When the refactoring is complete
Then all integration test files are under 500 LOC each

These tests verify that each of the 15 integration test files has been
refactored (split or reduced) to comply with the 500 LOC limit.
"""

from pathlib import Path

import pytest

from .conftest import (
    EXPECTED_FORECASTING_FILES,
    EXPECTED_INGESTION_FILES,
    EXPECTED_MODEL_SELECTION_FILES,
    conftest_exists,
    count_lines,
    directory_exists,
    file_exceeds_limit,
    get_files_exceeding_limit,
)


class TestAC1CriticalFileSplits:
    """[P0] Tests for critical priority files (>900 LOC) - 3-way splits."""

    @pytest.mark.atdd
    def test_ac_8_4b_1_1_forecast_query_integration_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.1: test_forecast_query_integration.py (1233 LOC) split."""
        filename = "test_forecast_query_integration.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit - should be split into forecasting/"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_2_ingestion_integration_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.2: test_ingestion_integration.py (1197 LOC) split."""
        filename = "test_ingestion_integration.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit - should be split into ingestion/"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_3_model_selection_cache_integration_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.3: test_model_selection_cache_integration.py (1175 LOC) split."""
        filename = "test_model_selection_cache_integration.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit - should be split into model_selection/"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_4_forecasting_subdirectory_created(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.1.4: forecasting/ subdirectory exists with proper structure."""
        assert directory_exists(tests_integration_path, "forecasting"), (
            "tests/integration/forecasting/ directory not created"
        )

        # Check for expected files after 3-way split
        forecasting_dir = tests_integration_path / "forecasting"
        for expected_file in EXPECTED_FORECASTING_FILES:
            assert (forecasting_dir / expected_file).exists(), (
                f"Expected file {expected_file} not found in forecasting/"
            )

    @pytest.mark.atdd
    def test_ac_8_4b_1_5_ingestion_subdirectory_created(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.1.5: ingestion/ subdirectory exists with proper structure."""
        assert directory_exists(tests_integration_path, "ingestion"), (
            "tests/integration/ingestion/ directory not created"
        )

        # Check for expected files after 3-way split
        ingestion_dir = tests_integration_path / "ingestion"
        for expected_file in EXPECTED_INGESTION_FILES:
            assert (ingestion_dir / expected_file).exists(), (
                f"Expected file {expected_file} not found in ingestion/"
            )

    @pytest.mark.atdd
    def test_ac_8_4b_1_6_model_selection_subdirectory_created(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.1.6: model_selection/ subdirectory exists with proper structure."""
        assert directory_exists(tests_integration_path, "model_selection"), (
            "tests/integration/model_selection/ directory not created"
        )

        # Check for expected files after 3-way split
        model_selection_dir = tests_integration_path / "model_selection"
        for expected_file in EXPECTED_MODEL_SELECTION_FILES:
            assert (model_selection_dir / expected_file).exists(), (
                f"Expected file {expected_file} not found in model_selection/"
            )


class TestAC1SevereFileSplits:
    """[P0] Tests for severe priority files (550-900 LOC) - 2-way splits."""

    @pytest.mark.atdd
    def test_ac_8_4b_1_7_model_selection_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.7: test_model_selection.py (855 LOC) split or reduced."""
        filename = "test_model_selection.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_8_story_6_23_final_validation_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.8: test_story_6_23_final_validation.py (837 LOC) split."""
        filename = "test_story_6_23_final_validation.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_9_epic3_p0_scenarios_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.9: test_epic3_p0_scenarios.py (780 LOC) split."""
        filename = "test_epic3_p0_scenarios.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_10_catboost_adaptive_weights_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.10: test_catboost_adaptive_weights.py (740 LOC) reduced."""
        filename = "test_catboost_adaptive_weights.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_11_ecb_macroeconomic_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.11: test_ecb_macroeconomic_integration.py (698 LOC) reduced."""
        filename = "test_ecb_macroeconomic_integration.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_12_eurostat_api_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.12: test_eurostat_api.py (672 LOC) reduced."""
        filename = "test_eurostat_api.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_13_fixed_chunking_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.13: test_fixed_chunking.py (666 LOC) reduced."""
        filename = "test_fixed_chunking.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_14_epic6_accuracy_regression_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.14: test_epic6_accuracy_regression.py (652 LOC) reduced."""
        filename = "test_epic6_accuracy_regression.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )


class TestAC1ModerateFileSplits:
    """[P0] Tests for moderate priority files (500-550 LOC) - fixture extraction."""

    @pytest.mark.atdd
    def test_ac_8_4b_1_15_metadata_injection_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.15: test_metadata_injection.py (640 LOC) reduced."""
        filename = "test_metadata_injection.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_16_analytical_query_tool_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.16: test_analytical_query_tool.py (633 LOC) reduced."""
        filename = "test_analytical_query_tool.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_17_external_data_integration_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.17: test_external_data_integration.py (612 LOC) reduced."""
        filename = "test_external_data_integration.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_18_proactive_insights_integration_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.18: test_proactive_insights_integration.py (605 LOC) reduced."""
        filename = "test_proactive_insights_integration.py"
        assert not file_exceeds_limit(tests_integration_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )


class TestAC1OverallValidation:
    """[P0] Tests for overall file size compliance."""

    @pytest.mark.atdd
    def test_ac_8_4b_1_19_no_integration_files_exceed_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.19: No integration test files exceed 500 LOC."""
        exceeding = get_files_exceeding_limit(tests_integration_path, file_size_limit)
        assert len(exceeding) == 0, (
            f"Files exceeding {file_size_limit} LOC: {[str(p) for p, _ in exceeding]}"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_1_20_all_new_subdirs_have_conftest(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.1.20: All new subdirectories have conftest.py."""
        subdirs = ["forecasting", "ingestion", "model_selection"]
        for subdir in subdirs:
            if directory_exists(tests_integration_path, subdir):
                assert conftest_exists(tests_integration_path, subdir), (
                    f"{subdir}/ missing conftest.py"
                )

    @pytest.mark.atdd
    def test_ac_8_4b_1_21_split_files_under_limit(
        self, tests_integration_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4b.1.21: All new split files are under 500 LOC."""
        subdirs = ["forecasting", "ingestion", "model_selection"]
        oversized = []

        for subdir in subdirs:
            subdir_path = tests_integration_path / subdir
            if subdir_path.exists():
                for test_file in subdir_path.glob("test_*.py"):
                    loc = count_lines(test_file)
                    if loc > file_size_limit:
                        oversized.append((test_file.name, loc))

        assert len(oversized) == 0, f"New split files exceeding limit: {oversized}"
