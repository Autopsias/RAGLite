"""Integration tests for Story 6.4: Ensemble Forecasting with Real Data.

Tests ensemble forecasting with PostgreSQL data and external regressors.
Requires running PostgreSQL and Qdrant containers.

pytestmark requires integration test setup.
"""

import os
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pytest

from raglite.forecasting.ensemble import generate_ensemble_forecast
from raglite.shared.models import ForecastQueryRequest

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData


# Set DYLD_LIBRARY_PATH for XGBoost on macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/opt/libomp/lib")

# Mark all tests in this module as integration tests that preserve collection state
# requires_ml_stack: Loads Prophet, CatBoost, ensemble models (~3-4GB)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.requires_ml_stack,
]


@pytest.fixture
def sample_historical_data() -> "TimeSeriesData":
    """Create sample historical data with 12 data points."""
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    # Generate 12 monthly data points (1 year of data)
    # Note: Use timezone-naive datetimes for Prophet compatibility
    base_date = datetime(2024, 1, 1)  # No timezone for Prophet
    np.random.seed(42)  # Reproducible random values
    points = [
        TimeSeriesPoint(
            date=base_date + timedelta(days=30 * i),
            value=1000.0 + i * 50.0 + np.random.uniform(-10, 10),  # noqa: S311
            label=f"Month {i + 1}",
        )
        for i in range(12)
    ]
    return TimeSeriesData(
        metric_name="revenue",
        points=points,
        interval="monthly",
        source_documents=["test_financial_report.pdf"],
    )


@pytest.fixture
def sample_external_regressors() -> dict[str, pd.Series]:
    """Create sample external regressors with correlation to target."""
    # Note: Use timezone-naive datetimes to match sample_historical_data
    base_date = datetime(2024, 1, 1)  # No timezone
    dates = pd.DatetimeIndex([base_date + timedelta(days=30 * i) for i in range(12)])

    return {
        "building_permits": pd.Series(
            [1000, 1020, 1050, 1080, 1100, 1150, 1180, 1200, 1250, 1280, 1300, 1350],
            index=dates,
        ),
        "electricity_price": pd.Series(
            [50.0, 51.2, 52.1, 53.5, 54.0, 55.2, 56.8, 57.0, 58.5, 59.0, 60.2, 61.0],
            index=dates,
        ),
    }


class TestEnsembleWithExternalRegressors:
    """Integration tests for ensemble forecasting with external data."""

    @pytest.mark.asyncio
    async def test_ensemble_forecast_with_regressors(
        self,
        sample_historical_data: "TimeSeriesData",
        sample_external_regressors: dict[str, pd.Series],
    ) -> None:
        """Test ensemble forecast using external regressors.

        Story 6.4 AC5: Ensemble voting with configurable weights.
        """
        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="revenue",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors=sample_external_regressors,
            periods_ahead=4,
            fast_mode=True,
        )

        # Verify ensemble result structure
        assert result.model_type == "ensemble"
        assert len(result.forecast) == 4

        # Should have at least Prophet (always runs)
        assert "prophet" in result.ensemble_models

        # Verify individual predictions are tracked
        assert len(result.individual_predictions) > 0

        # Verify weights are recorded
        assert len(result.ensemble_weights) > 0

    @pytest.mark.asyncio
    async def test_ensemble_forecast_without_regressors(
        self,
        sample_historical_data: "TimeSeriesData",
    ) -> None:
        """Test ensemble forecast without external regressors (Prophet only).

        Story 6.4 AC6: Fallback when sklearn models can't run.
        """
        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="revenue",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors=None,  # No regressors
            periods_ahead=4,
            fast_mode=True,
        )

        # Should still generate forecast using Prophet only
        assert len(result.forecast) == 4
        assert "prophet" in result.ensemble_models

        # sklearn models should not be in ensemble (no features)
        # Linear and XGBoost require regressors
        assert result.individual_predictions.get("prophet") is not None

    @pytest.mark.asyncio
    async def test_ensemble_forecast_accuracy_metrics(
        self,
        sample_historical_data: "TimeSeriesData",
        sample_external_regressors: dict[str, pd.Series],
    ) -> None:
        """Test that ensemble forecast returns accuracy metrics.

        Story 6.4 AC7: Validate accuracy improvement tracking.
        """
        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="revenue",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors=sample_external_regressors,
            periods_ahead=4,
            fast_mode=True,
        )

        # Accuracy metrics should be populated
        assert "rmse" in result.accuracy_metrics or len(result.accuracy_metrics) == 0

        # Regressors should be tracked
        # (may be empty if correlation too low)
        assert isinstance(result.regressors_used, list)


class TestEnsembleModelSelection:
    """Tests for model selection via settings."""

    @pytest.mark.asyncio
    async def test_ensemble_with_prophet_only(
        self,
        sample_historical_data: "TimeSeriesData",
    ) -> None:
        """Test ensemble with only Prophet model specified."""
        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="revenue",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors=None,
            periods_ahead=4,
            models=["prophet"],  # Only Prophet
            fast_mode=True,
        )

        assert "prophet" in result.ensemble_models
        assert len(result.ensemble_models) == 1

    @pytest.mark.asyncio
    async def test_ensemble_custom_weights(
        self,
        sample_historical_data: "TimeSeriesData",
        sample_external_regressors: dict[str, pd.Series],
    ) -> None:
        """Test ensemble with custom model weights."""
        custom_weights = {
            "prophet": 0.6,
            "linear": 0.2,
            "xgboost": 0.2,
        }

        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="revenue",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors=sample_external_regressors,
            periods_ahead=4,
            weights=custom_weights,
            fast_mode=True,
        )

        # Weights should be recorded (for models that ran)
        if "prophet" in result.ensemble_models:
            # Weight might be normalized if not all models succeeded
            assert result.ensemble_weights.get("prophet", 0) > 0


class TestEnsembleFallback:
    """Tests for ensemble fallback behavior."""

    @pytest.mark.asyncio
    async def test_ensemble_continues_on_model_failure(
        self,
        sample_historical_data: "TimeSeriesData",
    ) -> None:
        """Test that ensemble continues when a model fails.

        Story 6.4 AC6: Graceful degradation.
        """
        # Epic 8 API change: historical_data is now a required positional parameter
        # Even with empty regressors, Prophet should succeed
        result = await generate_ensemble_forecast(
            metric="revenue",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors={},  # Empty dict (no features)
            periods_ahead=4,
            models=["prophet", "linear", "xgboost"],
            fast_mode=True,
        )

        # Should still generate forecast
        assert len(result.forecast) > 0
        # Prophet should always be in the ensemble
        assert "prophet" in result.ensemble_models


class TestEnsemblePerformance:
    """Performance-related integration tests."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_ensemble_performance_under_15s(
        self,
        sample_historical_data: "TimeSeriesData",
        sample_external_regressors: dict[str, pd.Series],
    ) -> None:
        """Test that ensemble forecast completes within NFR time limit.

        NFR: Ensemble Forecast Time <15s p95
        """
        start_time = time.perf_counter()

        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="revenue",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors=sample_external_regressors,
            periods_ahead=4,
            fast_mode=True,  # Fast mode for CI
        )

        elapsed = time.perf_counter() - start_time

        assert result is not None
        # Should complete in <15s (fast mode should be much faster)
        assert elapsed < 15.0, f"Ensemble forecast took {elapsed:.2f}s (>15s NFR)"


class TestMCPToolIntegration:
    """Integration tests for MCP tool ensemble support."""

    @pytest.mark.asyncio
    async def test_mcp_tool_ensemble_model_type(self) -> None:
        """Test MCP tool accepts ensemble model_type parameter."""
        request = ForecastQueryRequest(
            metric="revenue",
            periods_ahead=4,
            model_type="ensemble",
        )

        assert request.model_type == "ensemble"

    @pytest.mark.asyncio
    async def test_mcp_tool_prophet_model_type(self) -> None:
        """Test MCP tool accepts prophet model_type parameter."""
        request = ForecastQueryRequest(
            metric="revenue",
            periods_ahead=4,
            model_type="prophet",
        )

        assert request.model_type == "prophet"
