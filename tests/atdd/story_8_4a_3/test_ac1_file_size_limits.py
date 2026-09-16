"""[P0] ATDD tests for AC-8.4a-3.1: All 31 files split or refactored to <500 LOC each.

Given the 31 moderate priority unit test files are between 500-815 LOC
When the refactoring is complete
Then all resulting files are under 500 LOC each

These tests verify that each of the 31 moderate priority files has been
refactored (split or reduced) to comply with the 500 LOC limit.
"""

from pathlib import Path

import pytest

from .conftest import (
    MODERATE_PRIORITY_FILES,
    count_lines,
    file_exceeds_limit,
    find_test_file,
)


class TestAC1FileSizeLimits:
    """[P0] Tests for AC-8.4a-3.1 - File size compliance."""

    # --- Batch 1: Files 815-864 LOC (3 files) ---

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_1_forecast_query_tool_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.1: test_forecast_query_tool.py (864 LOC) split or <500."""
        filename = "test_forecast_query_tool.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_2_parallel_ingestion_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.2: test_parallel_ingestion.py (858 LOC) split or <500."""
        filename = "test_parallel_ingestion.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_3_eurostat_edge_cases_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.3: test_eurostat_indicators_edge_cases.py (815 LOC) split or <500."""
        filename = "test_eurostat_indicators_edge_cases.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    # --- Batch 2: Files 750-800 LOC (5 files) ---

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_4_anomaly_detection_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.4: test_anomaly_detection.py (811 LOC) split or <500."""
        filename = "test_anomaly_detection.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_5_housing_transactions_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.5: test_housing_transactions.py (767 LOC) split or <500."""
        filename = "test_housing_transactions.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_6_multi_metric_validation_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.6: test_multi_metric_validation.py (760 LOC) split or <500."""
        filename = "test_multi_metric_validation.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_7_model_selection_utils_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.7: test_model_selection_utils.py (750 LOC) split or <500."""
        filename = "test_model_selection_utils.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_8_arima_model_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.8: test_arima_model.py (745 LOC) split or <500."""
        filename = "test_arima_model.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    # --- Batch 3: Files 600-750 LOC (5 files) ---

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_9_eurostat_indicators_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.9: test_eurostat_indicators.py (718 LOC) split or <500."""
        filename = "test_eurostat_indicators.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_10_story_7_4_expanded_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.10: test_story_7_4_expanded_coverage.py (661 LOC) split or <500."""
        filename = "test_story_7_4_expanded_coverage.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_11_retrieval_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.11: test_retrieval.py (653 LOC) split or <500."""
        filename = "test_retrieval.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_12_safety_guard_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.12: test_safety_guard.py (624 LOC) split or <500."""
        filename = "test_safety_guard.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_13_arima_ets_expanded_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.13: test_arima_ets_models_expanded.py (611 LOC) split or <500."""
        filename = "test_arima_ets_models_expanded.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    # --- Batch 4: Files 550-600 LOC (6 files) ---

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_14_mcp_model_routing_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.14: test_mcp_model_routing.py (595 LOC) split or <500."""
        filename = "test_mcp_model_routing.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_15_auto_update_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.15: test_auto_update.py (568 LOC) split or <500."""
        filename = "test_auto_update.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_16_standard_layouts_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.16: test_standard_layouts.py (560 LOC) split or <500."""
        filename = "test_standard_layouts.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_17_catboost_integration_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.17: test_catboost_integration.py (555 LOC) split or <500."""
        filename = "test_catboost_integration.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_18_phase2_centralized_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.18: test_phase2_centralized_validation.py (554 LOC) split or <500."""
        filename = "test_phase2_centralized_validation.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_19_hybrid_search_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.19: test_hybrid_search.py (553 LOC) split or <500."""
        filename = "test_hybrid_search.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    # --- Batch 5: Files 520-550 LOC (6 files) ---

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_20_proactive_insights_mcp_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.20: test_proactive_insights_mcp.py (551 LOC) split or <500."""
        filename = "test_proactive_insights_mcp.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_21_unit_inference_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.21: test_unit_inference.py (550 LOC) split or <500."""
        filename = "test_unit_inference.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_22_story_6_23_validation_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.22: test_story_6_23_validation_unit.py (542 LOC) split or <500."""
        filename = "test_story_6_23_validation_unit.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_23_ets_model_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.23: test_ets_model.py (541 LOC) split or <500."""
        filename = "test_ets_model.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_24_ecb_macroeconomic_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.24: test_ecb_macroeconomic.py (539 LOC) split or <500."""
        filename = "test_ecb_macroeconomic.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_25_scripts_accuracy_utils_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.25: test_scripts_accuracy_utils.py (533 LOC) split or <500."""
        filename = "test_scripts_accuracy_utils.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    # --- Batch 6: Files 500-520 LOC (6 files) ---

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_26_synthesis_agent_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.26: test_synthesis_agent.py (523 LOC) split or <500."""
        filename = "test_synthesis_agent.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_27_ensemble_forecasting_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.27: test_ensemble_forecasting.py (520 LOC) split or <500."""
        filename = "test_ensemble_forecasting.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_28_regressor_config_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.28: test_regressor_config_story_6_16.py (512 LOC) split or <500."""
        filename = "test_regressor_config_story_6_16.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_29_base64_ingestion_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.29: test_base64_ingestion.py (512 LOC) split or <500."""
        filename = "test_base64_ingestion.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_30_refactoring_acceptance_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.30: test_refactoring_acceptance.py (507 LOC) split or <500."""
        filename = "test_refactoring_acceptance.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_31_scheduler_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.31: test_scheduler.py (503 LOC) split or <500."""
        filename = "test_scheduler.py"
        assert not file_exceeds_limit(tests_unit_path, filename, file_size_limit), (
            f"{filename} exceeds {file_size_limit} LOC limit"
        )

    # --- Summary Test ---

    @pytest.mark.atdd
    def test_ac_8_4a_3_1_summary_all_files_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.1.SUMMARY: All 31 moderate priority files comply with limit."""
        violations = []
        for entry in MODERATE_PRIORITY_FILES:
            filepath = find_test_file(tests_unit_path, entry.filename)
            if filepath is not None:
                loc = count_lines(filepath)
                if loc > file_size_limit:
                    violations.append(f"{entry.filename}: {loc} LOC (limit: {file_size_limit})")

        assert not violations, f"Files exceeding {file_size_limit} LOC limit:\n" + "\n".join(
            violations
        )
