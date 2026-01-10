"""
Tests for model selection execution logic and error handling.

AC-7b.5.3: run_single_variable_selection helper
AC-7b.5.5: Cache Results in PostgreSQL
Error handling tests
"""

from __future__ import annotations

import inspect
import tempfile
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest

if TYPE_CHECKING:
    pass

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestRunSingleVariableSelection:
    """[P1] AC-7b.5.3: Single variable selection helper function."""

    def test_run_single_variable_selection_exists(self) -> None:
        """[P1][TEST-AC-7b.5.3.11] run_single_variable_selection function exists."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        assert callable(run_single_variable_selection)

    def test_run_single_variable_selection_is_async(self) -> None:
        """[P1][TEST-AC-7b.5.3.12] run_single_variable_selection is async."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        assert inspect.iscoroutinefunction(run_single_variable_selection), (
            "run_single_variable_selection must be async"
        )

    def test_run_single_variable_selection_has_dry_run_param(self) -> None:
        """[P1][TEST-AC-7b.5.3.13] run_single_variable_selection has dry_run parameter."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        sig = inspect.signature(run_single_variable_selection)
        params = list(sig.parameters.keys())
        assert "dry_run" in params, "Missing dry_run parameter"

    def test_run_single_variable_selection_has_force_refresh_param(self) -> None:
        """[P1][TEST-AC-7b.5.3.14] run_single_variable_selection has force_refresh parameter."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        sig = inspect.signature(run_single_variable_selection)
        params = list(sig.parameters.keys())
        assert "force_refresh" in params, "Missing force_refresh parameter"

    @pytest.mark.asyncio
    async def test_dry_run_skips_cache(self, single_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.3.15] dry_run=True skips caching."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        with single_selection_mocks() as mock_cache:
            # Run with dry_run=True
            await run_single_variable_selection(
                variable="test_var", force_refresh=False, dry_run=True
            )

            # cache_model_selection should NOT be called
            assert mock_cache.call_count == 0, (
                f"Expected 0 cache calls with dry_run=True, got {mock_cache.call_count}"
            )

    @pytest.mark.asyncio
    async def test_normal_mode_calls_cache(self, single_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.3.16] dry_run=False calls cache."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        with single_selection_mocks() as mock_cache:
            # Run with dry_run=False
            await run_single_variable_selection(
                variable="test_var", force_refresh=False, dry_run=False
            )

            # cache_model_selection should be called once
            assert mock_cache.call_count == 1, (
                f"Expected 1 cache call with dry_run=False, got {mock_cache.call_count}"
            )


class TestSingleVariableSelection:
    """[P1] Edge cases for run_single_variable_selection."""

    @pytest.mark.asyncio
    async def test_single_variable_error_returns_none(self, mock_historical_data) -> None:
        """[P1][TEST-SINGLE-1] Error in single variable selection returns None."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

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
                side_effect=ValueError("Model selection failed"),
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
                "raglite.forecasting.model_selection_job.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.regressor_fetch.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_model_result,
            ),
            patch(
                "raglite.external_data.storage.model_selection.cache_model_selection",
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
                "raglite.forecasting.model_selection_job.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.regressor_fetch.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch(
                "raglite.external_data.storage.model_selection.cache_model_selection",
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


class TestCacheResults:
    """[P0] AC-7b.5.5: Cache results in PostgreSQL."""

    @pytest.mark.asyncio
    async def test_cache_called_for_each_result(self) -> None:
        """[P0][TEST-AC-7b.5.5.1] cache_model_selection called for each successful result."""
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


class TestErrorHandling:
    """[P1] Error handling in batch model selection."""

    @pytest.mark.asyncio
    async def test_individual_failures_dont_stop_batch(self, mock_historical_data) -> None:
        """[P1][TEST-ERR-1] Individual variable failures don't stop batch processing."""

        from raglite.forecasting.model_selection_job import run_batch_model_selection

        call_count = 0

        async def mock_select_best_model(variable_name: str, **kwargs) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if variable_name == "var2":
                raise ValueError("Simulated failure for var2")
            mock_result = MagicMock()
            mock_result.best_model = "arima"
            mock_result.best_mape = 0.05
            mock_result.best_mase = 0.8
            mock_result.best_with_regressors = False
            mock_result.best_regressor_set = None
            mock_result.cv_folds = 5
            mock_result.runtime_seconds = 10.0
            mock_result.candidate_results = {}
            return mock_result

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
                    side_effect=mock_select_best_model,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.cache_model_selection",
                    new_callable=Mock,
                ),
            ):
                results = await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=1,
                    output_dir=tmpdir,
                )

                # All 3 should have been attempted
                assert call_count == 3, f"Expected 3 calls, got {call_count}"
                # var1 and var3 should succeed
                assert len(results) == 2, f"Expected 2 successful results, got {len(results)}"

    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self, batch_selection_mocks) -> None:
        """[P0][TEST-RET-1] run_batch_model_selection returns dict of results."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                results = await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=tmpdir,
                )

                assert isinstance(results, dict), f"Expected dict, got {type(results)}"
                assert "test_var" in results, "Result should contain variable key"
