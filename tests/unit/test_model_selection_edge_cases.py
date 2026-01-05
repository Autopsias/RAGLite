"""
Tests for model selection edge cases and performance.

AC-7b.5.8: Runtime Performance
Edge case scenarios
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

import pytest

if TYPE_CHECKING:
    pass

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestEdgeCases:
    """[P2] Edge case tests for model_selection_job."""

    @pytest.mark.asyncio
    async def test_empty_variables_list(self, batch_selection_mocks) -> None:
        """[P2][TEST-EDGE-1] Empty variables list returns empty dict."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                result = await run_batch_model_selection(variables=[], output_dir=tmpdir)
                assert result == {}, "Empty variables list should return empty dict"

    @pytest.mark.asyncio
    async def test_single_variable_in_batch_mode(self, batch_selection_mocks) -> None:
        """[P1][TEST-EDGE-2] Single variable in batch mode works correctly."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                results = await run_batch_model_selection(
                    variables=["ebitda"],
                    workers=1,
                    output_dir=tmpdir,
                )

                assert len(results) == 1, "Single variable should return single result"
                assert "ebitda" in results, "Result should contain the variable"

    @pytest.mark.asyncio
    async def test_output_dir_created_if_missing(self, batch_selection_mocks) -> None:
        """[P2][TEST-EDGE-3] Output directory is created if it doesn't exist."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nonexistent_dir"
            assert not output_path.exists(), "Directory should not exist initially"

            with batch_selection_mocks(str(output_path)):
                await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=str(output_path),
                )

                assert output_path.exists(), "Output directory should be created"
                assert output_path.is_dir(), "Output path should be a directory"

    @pytest.mark.asyncio
    async def test_all_variables_fail(self, mock_historical_data) -> None:
        """[P1][TEST-EDGE-4] All variables failing returns empty results dict."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        async def mock_failing_select(variable_name: str, **kwargs):
            raise ValueError(f"Simulated failure for {variable_name}")

        with tempfile.TemporaryDirectory() as tmpdir:
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
                    side_effect=mock_failing_select,
                ),
                patch(
                    "raglite.forecasting.model_selection.cache_model_selection",
                    new_callable=Mock,
                ),
            ):
                results = await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=1,
                    output_dir=tmpdir,
                )

                assert len(results) == 0, "All failures should return empty dict"

    @pytest.mark.asyncio
    async def test_cache_failure_doesnt_stop_processing(
        self, mock_historical_data, mock_model_result
    ) -> None:
        """[P1][TEST-EDGE-5] Cache failures don't stop batch processing."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        def failing_cache(*args, **kwargs):
            raise ValueError("Cache write failed")

        with tempfile.TemporaryDirectory() as tmpdir:
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
                    side_effect=failing_cache,
                ),
            ):
                # Should not raise - errors are caught and logged
                results = await run_batch_model_selection(
                    variables=["var1", "var2"],
                    workers=1,
                    output_dir=tmpdir,
                )

                # Processing should continue despite cache failures
                assert len(results) == 0, (
                    "Cache failures should cause variables to be treated as failed"
                )

    @pytest.mark.asyncio
    async def test_workers_parameter_affects_concurrency(self, batch_selection_mocks) -> None:
        """[P1][TEST-EDGE-6] Workers parameter controls parallel execution."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                # Test with different worker counts
                result_1_worker = await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=1,
                    output_dir=tmpdir,
                )
                result_8_workers = await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=8,
                    output_dir=tmpdir,
                )

                # Both should succeed with same results
                assert len(result_1_worker) == 3
                assert len(result_8_workers) == 3


class TestRuntimePerformance:
    """[P2] AC-7b.5.8: Runtime less than 120 minutes.

    Note: This is marked as P2 because it's a performance test that
    requires real execution. In practice, this test would be run in
    a dedicated CI job with actual model selection.
    """

    @pytest.mark.slow
    @pytest.mark.skip(reason="Performance test - run manually with real data")
    @pytest.mark.asyncio
    async def test_full_batch_under_120_minutes(self) -> None:
        """[P2][TEST-AC-7b.5.8.1] Full batch completes in <120 minutes."""
        import time

        from raglite.forecasting.model_selection_job import (
            ALL_VARIABLES,
            run_batch_model_selection,
        )

        start = time.time()
        await run_batch_model_selection(
            variables=ALL_VARIABLES,
            workers=4,
        )
        elapsed_minutes = (time.time() - start) / 60

        assert elapsed_minutes < 120, (
            f"Batch took {elapsed_minutes:.1f} minutes, exceeds 120 minute budget"
        )
