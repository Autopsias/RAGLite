"""
ATDD tests for Story 7b-5: Model Selection Slash Commands & Subagent.

TDD RED Phase: These tests should FAIL until implementation is complete.

This test file covers:
- AC-7b.5.1: Slash Command Definition
- AC-7b.5.2: Model-Selection-Executor Subagent
- AC-7b.5.3: run_batch_model_selection() Python Function
- AC-7b.5.4: Parallel Execution (4 Workers)
- AC-7b.5.5: Cache Results in PostgreSQL
- AC-7b.5.6: Generate JSON + Markdown Report
- AC-7b.5.7: Progress Logging with Status Updates
- AC-7b.5.8: Runtime Less Than 120 Minutes (P2 - Performance test)

Priority levels:
- P0: Critical path tests (must pass for story completion)
- P1: Important scenarios (should pass)
- P2: Edge cases and performance tests
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

if TYPE_CHECKING:
    pass

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestReportStructure:
    """[P2] Detailed tests for report structure and content."""

    @pytest.mark.asyncio
    async def test_json_report_structure_validation(self, mock_historical_data) -> None:
        """[P2][TEST-REPORT-1] JSON report has all required fields with correct types."""
        import json

        from raglite.forecasting.model_selection_job import run_batch_model_selection

        mock_result = MagicMock()
        mock_result.best_model = "arima"
        mock_result.best_mape = 0.082
        mock_result.best_mase = 0.42
        mock_result.best_with_regressors = True
        mock_result.best_regressor_set = ["euribor_3m", "diesel"]
        mock_result.cv_folds = 5
        mock_result.runtime_seconds = 45.2
        mock_result.candidate_results = {"arima_True": {"mape": 0.082, "mase": 0.42}}

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch(
                    "raglite.forecasting.model_selection_job.fetch_historical_data",
                    new_callable=AsyncMock,
                    return_value=mock_historical_data,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                    new_callable=AsyncMock,
                    return_value={},
                ),
                patch(
                    "raglite.forecasting.model_selection_job.select_best_model",
                    new_callable=AsyncMock,
                    return_value=mock_result,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.cache_model_selection",
                    new_callable=Mock,
                ),
            ):
                await run_batch_model_selection(
                    variables=["ebitda"],
                    workers=1,
                    output_dir=tmpdir,
                )

                json_files = list(Path(tmpdir).glob("model-selection-*.json"))
                assert len(json_files) == 1, "Should create exactly one JSON report"

                with open(json_files[0]) as f:
                    report = json.load(f)

                # Validate structure
                assert "timestamp" in report
                assert "runtime_minutes" in report
                assert "variables_processed" in report
                assert "results" in report
                assert isinstance(report["results"], dict)

                # Validate ebitda result
                assert "ebitda" in report["results"]
                ebitda_result = report["results"]["ebitda"]
                assert ebitda_result["best_model"] == "arima"
                assert ebitda_result["best_mape"] == 0.082
                assert ebitda_result["best_mase"] == 0.42
                assert ebitda_result["use_regressors"] is True
                assert ebitda_result["regressor_set"] == ["euribor_3m", "diesel"]

    @pytest.mark.asyncio
    async def test_markdown_report_structure_validation(self, batch_selection_mocks) -> None:
        """[P2][TEST-REPORT-2] Markdown report has proper table formatting."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["revenue", "ebitda"],
                    workers=1,
                    output_dir=tmpdir,
                )

                md_files = list(Path(tmpdir).glob("model-selection-*.md"))
                assert len(md_files) == 1, "Should create exactly one Markdown report"

                content = md_files[0].read_text()

                # Check for required sections
                assert "# Model Selection Report" in content
                assert "## Summary" in content or "Summary" in content
                assert "## Results" in content or "## Best Performers" in content

                # Check for table structure
                assert "|" in content, "Should contain table formatting"
                assert "Variable" in content or "variable" in content.lower()
                assert "MAPE" in content or "mape" in content.lower()

    @pytest.mark.asyncio
    async def test_print_summary_with_empty_results(self, capsys) -> None:
        """[P2][TEST-REPORT-3] _print_summary handles empty results gracefully."""
        from raglite.forecasting.model_selection_job import _print_summary

        _print_summary(results={}, errors=[], variables=["var1", "var2"])

        captured = capsys.readouterr()
        assert "Variables processed: 0/2" in captured.out
        assert "MODEL SELECTION COMPLETE" in captured.out

    @pytest.mark.asyncio
    async def test_print_summary_with_only_errors(self, capsys) -> None:
        """[P2][TEST-REPORT-4] _print_summary handles error-only scenario."""
        from raglite.forecasting.model_selection_job import _print_summary

        errors = ["var1: timeout", "var2: network error"]
        _print_summary(results={}, errors=errors, variables=["var1", "var2"])

        captured = capsys.readouterr()
        assert "Errors: 2" in captured.out
        assert "var1: timeout" in captured.out
        assert "var2: network error" in captured.out

    @pytest.mark.asyncio
    async def test_generate_markdown_report_sorting(self) -> None:
        """[P2][TEST-REPORT-5] Markdown report sorts variables by MAPE."""
        from raglite.forecasting.model_selection_job import _generate_markdown_report

        # Create mock results with different MAPE values
        result_high = MagicMock()
        result_high.best_model = "arima"
        result_high.best_mape = 0.15  # Worst
        result_high.best_mase = 1.0
        result_high.best_with_regressors = False
        result_high.best_regressor_set = []

        result_low = MagicMock()
        result_low.best_model = "prophet"
        result_low.best_mape = 0.03  # Best
        result_low.best_mase = 0.8
        result_low.best_with_regressors = False
        result_low.best_regressor_set = []

        results = {
            "capacity_utilization": result_high,
            "co2_eua_price": result_low,
        }

        md_content = _generate_markdown_report(results, "20251221-120000")

        # co2_eua_price should appear before capacity_utilization (sorted by MAPE)
        co2_index = md_content.find("co2_eua_price")
        capacity_index = md_content.find("capacity_utilization")
        assert co2_index < capacity_index, "Should be sorted by MAPE (best first)"
