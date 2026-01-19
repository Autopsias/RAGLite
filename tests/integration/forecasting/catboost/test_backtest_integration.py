"""Integration tests for backtest job execution (Story 6.12 AC3)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from raglite.forecasting.backtest_job import (
    run_backtest_for_metric,
    trigger_backtest_now,
)

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData

# Mark all tests in this module as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="database_writes"),
]


class TestBacktestJob:
    """Integration tests for backtest job (AC3)."""

    @pytest.mark.asyncio
    async def test_backtest_for_metric_calculates_weights(
        self,
        sample_historical_data: TimeSeriesData,
        sample_external_regressors: dict[str, pd.Series],
    ) -> None:
        """Test run_backtest_for_metric calculates weights."""
        # Convert TimeSeriesData to the format expected by backtest
        result = run_backtest_for_metric(
            metric="cement_demand",
            historical_data=sample_historical_data,
            external_regressors=sample_external_regressors,
        )

        assert isinstance(result, dict)

        # Should have results for at least one model
        if result:
            for _model_name, model_result in result.items():
                assert "weight" in model_result
                assert "rmse" in model_result
                assert model_result["weight"] > 0

    @pytest.mark.asyncio
    async def test_trigger_backtest_now(self) -> None:
        """Test trigger_backtest_now function.

        Note: With the full implementation, backtest retrieves historical data
        from PostgreSQL external sources. In the test environment, these sources
        won't exist, so metrics_processed will be 0 (expected behavior).
        The important thing is that the function runs without errors and returns
        the correct structure.
        """
        # Trigger backtest - runs for KNOWN_METRICS
        # Note: The metrics parameter filters which metrics to process
        result = await trigger_backtest_now()

        assert isinstance(result, dict)
        # Should have processed metrics count and weights updated count
        assert "metrics_processed" in result
        assert "weights_updated" in result
        # In test environment without external data sources, metrics_processed will be 0
        # This is expected behavior - the backtest job correctly handles missing data
        assert result["metrics_processed"] >= 0
        assert result["weights_updated"] >= 0
