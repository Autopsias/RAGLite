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

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

if TYPE_CHECKING:
    pass

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestSingleVariableSelection:
    """[P1] Edge cases for run_single_variable_selection."""

    @pytest.mark.asyncio
    async def test_single_variable_error_returns_none(self, mock_historical_data) -> None:
        """[P1][TEST-SINGLE-1] Error in single variable selection returns None."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        async def failing_select(*args, **kwargs):
            raise ValueError("Model selection failed")

        with (
            patch(
                "raglite.forecasting.model_selection.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.model_selection.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection.select_best_model",
                side_effect=failing_select,
            ),
        ):
            result = await run_single_variable_selection(
                variable="ebitda", force_refresh=False, dry_run=False
            )

            assert result is None, "Failed selection should return None"

    @pytest.mark.asyncio
    async def test_single_variable_with_no_regressors(
        self, mock_historical_data, mock_model_result, capsys
    ) -> None:
        """[P1][TEST-SINGLE-2] Single variable with no regressors displays correctly."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        with (
            patch(
                "raglite.forecasting.model_selection.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.model_selection.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_model_result,
            ),
            patch(
                "raglite.forecasting.model_selection.cache_model_selection",
                new_callable=Mock,
            ),
        ):
            result = await run_single_variable_selection(
                variable="ebitda", force_refresh=False, dry_run=False
            )

            assert result is not None
            captured = capsys.readouterr()
            assert "Use Regressors: False" in captured.out or "Regressors: None" in captured.out

    @pytest.mark.asyncio
    async def test_single_variable_comparison_table_output(
        self, mock_historical_data, capsys
    ) -> None:
        """[P2][TEST-SINGLE-3] Single variable displays candidate comparison table."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        mock_result = MagicMock()
        mock_result.best_model = "arima"
        mock_result.best_mape = 0.05
        mock_result.best_mase = 0.8
        mock_result.best_with_regressors = False
        mock_result.best_regressor_set = []
        mock_result.cv_folds = 5
        mock_result.runtime_seconds = 25.0
        mock_result.candidate_results = {
            "arima_False": {"mape": 0.05, "mase": 0.8},
            "prophet_False": {"mape": 0.07, "mase": 0.9},
            "ets_False": {"mape": 0.10, "mase": 1.1},
        }

        with (
            patch(
                "raglite.forecasting.model_selection.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.model_selection.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch(
                "raglite.forecasting.model_selection.cache_model_selection",
                new_callable=Mock,
            ),
        ):
            await run_single_variable_selection(
                variable="ebitda", force_refresh=False, dry_run=False
            )

            captured = capsys.readouterr()
            # Check for comparison table header
            assert "Model" in captured.out or "model" in captured.out.lower()
            assert "MAPE" in captured.out
            assert "BEST" in captured.out or "Status" in captured.out
