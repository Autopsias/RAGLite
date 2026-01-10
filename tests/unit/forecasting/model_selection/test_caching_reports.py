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

import inspect
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

if TYPE_CHECKING:
    pass

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]

# -----------------------------------------------------------------------------
# AC-7b.5.5: Cache Results in PostgreSQL
# -----------------------------------------------------------------------------


class TestCacheResults:
    """[P0] AC-7b.5.5: Cache results in PostgreSQL."""

    @pytest.mark.asyncio
    async def test_cache_called_for_each_result(self) -> None:
        """[P0][TEST-AC-7b.5.5.1] cache_model_selection called for each successful result."""
        import pandas as pd

        from raglite.forecasting.model_selection_job import run_batch_model_selection

        mock_result = MagicMock()
        mock_result.best_model = "arima"
        mock_result.best_mape = 0.05
        mock_result.best_mase = 0.8
        mock_result.best_with_regressors = False
        mock_result.best_regressor_set = None
        mock_result.cv_folds = 5
        mock_result.runtime_seconds = 10.0
        mock_result.candidate_results = {}

        mock_cache = Mock()
        # Mock historical data with 12+ points to pass validation
        mock_historical = pd.Series(
            [100.0] * 15,
            index=pd.date_range("2023-01-01", periods=15, freq="MS"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch(
                    "raglite.forecasting.model_selection_job.fetch_historical_data",
                    new_callable=AsyncMock,
                    return_value=mock_historical,
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
                    mock_cache,
                ),
            ):
                await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=2,
                    output_dir=tmpdir,
                )

                # cache_model_selection should be called once per variable
                assert mock_cache.call_count == 3, (
                    f"Expected 3 cache calls, got {mock_cache.call_count}"
                )


# -----------------------------------------------------------------------------
# AC-7b.5.6: Generate JSON + Markdown Report
# -----------------------------------------------------------------------------


class TestReportGeneration:
    """[P1] AC-7b.5.6: Report generation."""

    def test_generate_reports_function_exists(self) -> None:
        """[P1][TEST-AC-7b.5.6.1] _generate_reports helper must exist."""
        from raglite.forecasting.model_selection_job import _generate_reports

        assert callable(_generate_reports)

    def test_generate_reports_is_async(self) -> None:
        """[P1][TEST-AC-7b.5.6.2] _generate_reports is an async function."""
        from raglite.forecasting.model_selection_job import _generate_reports

        assert inspect.iscoroutinefunction(_generate_reports), "_generate_reports must be async"

    @pytest.mark.asyncio
    async def test_reports_created_in_output_dir(self, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.6.3] JSON and Markdown reports created in output_dir."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=tmpdir,
                )

                # Check for JSON report
                json_files = list(Path(tmpdir).glob("model-selection-*.json"))
                assert len(json_files) >= 1, "No JSON report generated"

                # Check for Markdown report
                md_files = list(Path(tmpdir).glob("model-selection-*.md"))
                assert len(md_files) >= 1, "No Markdown report generated"

    @pytest.mark.asyncio
    async def test_json_report_has_required_fields(self, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.6.4] JSON report contains required fields."""
        import json

        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=tmpdir,
                )

                json_files = list(Path(tmpdir).glob("model-selection-*.json"))
                assert len(json_files) >= 1, "No JSON report generated"

                with open(json_files[0]) as f:
                    report = json.load(f)

                assert "timestamp" in report, "Missing timestamp in JSON report"
                assert "runtime_minutes" in report, "Missing runtime_minutes in JSON report"
                assert "results" in report, "Missing results in JSON report"

    @pytest.mark.asyncio
    async def test_markdown_report_has_summary_table(self, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.6.5] Markdown report contains summary table."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=tmpdir,
                )

                md_files = list(Path(tmpdir).glob("model-selection-*.md"))
                assert len(md_files) >= 1, "No Markdown report generated"

                content = md_files[0].read_text()
                # Check for table structure
                assert "| Variable |" in content or "| variable |" in content.lower(), (
                    "Missing summary table in Markdown report"
                )
                assert "| Best Model |" in content or "best_model" in content.lower(), (
                    "Missing best model column in Markdown report"
                )


# -----------------------------------------------------------------------------
# AC-7b.5.7: Progress Logging with Status Updates
# -----------------------------------------------------------------------------


class TestProgressLogging:
    """[P1] AC-7b.5.7: Progress logging with status updates."""

    @pytest.mark.asyncio
    async def test_progress_printed_for_each_variable(self, capsys, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.7.1] Progress printed as each variable completes."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["var1", "var2"],
                    workers=1,
                    output_dir=tmpdir,
                )

                captured = capsys.readouterr()
                # Check for [N/total] format
                assert "[1/" in captured.out or "[2/" in captured.out, (
                    "Missing [N/total] progress format in output"
                )

    @pytest.mark.asyncio
    async def test_summary_printed_at_completion(self, capsys, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.7.2] Summary section printed at completion."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=tmpdir,
                )

                captured = capsys.readouterr()
                # Check for summary section
                assert "Summary" in captured.out or "Variables processed" in captured.out, (
                    "Missing summary section in output"
                )
