"""Unit tests for Story 6.4: Model Ensemble Framework.

Tests ensemble forecasting components including:
- Linear Regression fitting (AC3)
- XGBoost fitting with GridSearchCV (AC4)
- Weighted average calculation (AC5)
- Fallback strategies (AC6)
- Settings configuration (AC2)
"""

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests require real XGBoost/sklearn for ensemble model fitting
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="Ensemble forecasting tests require real XGBoost/sklearn (not mocked)",
)

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData


# Set DYLD_LIBRARY_PATH for XGBoost on macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/opt/libomp/lib")


class TestForecastQueryRequest:
    """Tests for ForecastQueryRequest model_type field."""

    def test_forecast_query_request_default_model_type(self) -> None:
        """ForecastQueryRequest defaults to 'auto' model type.

        Story 6.11: Updated default from 'prophet' to 'auto' for automatic
        model selection based on data availability and quality.
        """
        from raglite.shared.models import ForecastQueryRequest

        request = ForecastQueryRequest(metric="revenue")

        assert request.model_type == "auto"

    def test_forecast_query_request_ensemble_model_type(self) -> None:
        """ForecastQueryRequest accepts 'ensemble' model type."""
        from raglite.shared.models import ForecastQueryRequest

        request = ForecastQueryRequest(
            metric="revenue",
            model_type="ensemble",
        )

        assert request.model_type == "ensemble"


class TestGenerateEnsembleForecast:
    """Tests for generate_ensemble_forecast function (AC5, AC6)."""

    @pytest.fixture
    def sample_historical_data(self) -> "TimeSeriesData":
        """Create sample historical data for testing."""
        from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

        # Generate 8 quarterly data points (Q1 2023 - Q4 2024)
        months = [1, 4, 7, 10, 1, 4, 7, 10]  # Jan, Apr, Jul, Oct for each quarter
        years = [2023, 2023, 2023, 2023, 2024, 2024, 2024, 2024]
        points = [
            TimeSeriesPoint(
                date=datetime(years[i], months[i], 1, tzinfo=UTC),
                value=100.0 + i * 10.0,
                label=f"Q{(i % 4) + 1} {years[i]}",
            )
            for i in range(8)  # 8 quarters of data
        ]
        return TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="quarterly",
            source_documents=["test.pdf"],
        )

    @pytest.mark.asyncio
    async def test_ensemble_forecast_prophet_only_without_regressors(
        self, sample_historical_data: "TimeSeriesData"
    ) -> None:
        """AC5: Ensemble falls back to Prophet when no regressors available."""
        from raglite.forecasting.ensemble import generate_ensemble_forecast

        # Mock generate_forecast to avoid actual Prophet call
        with patch("raglite.forecasting.hybrid.generate_forecast") as mock_generate:
            from raglite.shared.models import ForecastPoint, ForecastResult

            mock_result = ForecastResult(
                metric_name="revenue",
                forecast=[
                    ForecastPoint(
                        date=datetime(2025, 1, 1, tzinfo=UTC),
                        value=180.0,
                        lower=170.0,
                        upper=190.0,
                        label="Q1 2025",
                    ),
                    ForecastPoint(
                        date=datetime(2025, 4, 1, tzinfo=UTC),
                        value=190.0,
                        lower=180.0,
                        upper=200.0,
                        label="Q2 2025",
                    ),
                    ForecastPoint(
                        date=datetime(2025, 7, 1, tzinfo=UTC),
                        value=200.0,
                        lower=190.0,
                        upper=210.0,
                        label="Q3 2025",
                    ),
                    ForecastPoint(
                        date=datetime(2025, 10, 1, tzinfo=UTC),
                        value=210.0,
                        lower=200.0,
                        upper=220.0,
                        label="Q4 2025",
                    ),
                ],
                model_type="prophet_univariate",
            )
            mock_generate.return_value = mock_result

            result = await generate_ensemble_forecast(
                metric="revenue",
                historical_data=sample_historical_data,
                external_regressors=None,  # No regressors
                periods_ahead=4,
                fast_mode=True,
            )

            # Should use Prophet only (no sklearn models without regressors)
            assert "prophet" in result.ensemble_models
            assert len(result.forecast) > 0

    @pytest.mark.asyncio
    async def test_ensemble_forecast_fallback_on_failure(
        self, sample_historical_data: "TimeSeriesData"
    ) -> None:
        """AC6: Ensemble falls back to Prophet when all models fail."""
        from raglite.forecasting.ensemble import generate_ensemble_forecast

        # Mock all models to fail initially, then succeed on fallback
        call_count = [0]

        async def mock_generate_forecast(*args, **kwargs):
            from raglite.shared.models import ForecastPoint, ForecastResult

            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Simulated failure")
            return ForecastResult(
                metric_name="revenue",
                forecast=[
                    ForecastPoint(
                        date=datetime(2025, 1, 1, tzinfo=UTC),
                        value=180.0,
                        lower=170.0,
                        upper=190.0,
                        label="Q1 2025",
                    )
                ],
                model_type="prophet_univariate",
            )

        with patch(
            "raglite.forecasting.hybrid.generate_forecast",
            side_effect=mock_generate_forecast,
        ):
            result = await generate_ensemble_forecast(
                metric="revenue",
                historical_data=sample_historical_data,
                external_regressors=None,
                periods_ahead=4,
                models=["prophet"],  # Only Prophet
            )

            # Should have fallen back
            assert result is not None


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_run_linear_forecast(self) -> None:
        """Test _run_linear_forecast helper."""
        from raglite.forecasting.hybrid import _run_linear_forecast

        # Create a simple mock model
        class MockModel:
            def predict(self, X):
                return np.array([100.0, 110.0, 120.0, 130.0])

        model = MockModel()
        X_future = pd.DataFrame({"feature": [1, 2, 3, 4]})

        result = _run_linear_forecast(model, X_future, periods_ahead=3)

        assert "values" in result
        assert len(result["values"]) == 3
        assert result["values"] == [100.0, 110.0, 120.0]

    def test_run_xgboost_forecast(self) -> None:
        """Test _run_xgboost_forecast helper."""
        from raglite.forecasting.hybrid import _run_xgboost_forecast

        # Create a simple mock model
        class MockModel:
            def predict(self, X):
                return np.array([200.0, 210.0, 220.0, 230.0])

        model = MockModel()
        X_future = pd.DataFrame({"feature": [1, 2, 3, 4]})

        result = _run_xgboost_forecast(model, X_future, periods_ahead=2)

        assert "values" in result
        assert len(result["values"]) == 2
        assert result["values"] == [200.0, 210.0]


class TestLazyLoading:
    """Tests for lazy-loading of sklearn/xgboost."""

    def test_lazy_load_linear_regression(self) -> None:
        """Lazy loading returns LinearRegression class."""
        from raglite.forecasting.hybrid import _get_linear_regression

        LinearRegression = _get_linear_regression()
        assert LinearRegression.__name__ == "LinearRegression"

    def test_lazy_load_time_series_split(self) -> None:
        """Lazy loading returns TimeSeriesSplit class."""
        from raglite.forecasting.hybrid import _get_time_series_split

        TimeSeriesSplit = _get_time_series_split()
        assert TimeSeriesSplit.__name__ == "TimeSeriesSplit"

    def test_lazy_load_xgboost_regressor(self) -> None:
        """Lazy loading returns XGBRegressor class."""
        from raglite.forecasting.hybrid import _get_xgboost_regressor

        XGBRegressor = _get_xgboost_regressor()
        assert XGBRegressor.__name__ == "XGBRegressor"

    def test_lazy_load_grid_search_cv(self) -> None:
        """Lazy loading returns GridSearchCV class."""
        from raglite.forecasting.hybrid import _get_grid_search_cv

        GridSearchCV = _get_grid_search_cv()
        assert GridSearchCV.__name__ == "GridSearchCV"


class TestXGBoostParamGrids:
    """Tests for XGBoost hyperparameter grids."""

    def test_full_param_grid_structure(self) -> None:
        """Full param grid has expected structure."""
        from raglite.forecasting.hybrid import XGBOOST_PARAM_GRID

        assert "n_estimators" in XGBOOST_PARAM_GRID
        assert "max_depth" in XGBOOST_PARAM_GRID
        assert "learning_rate" in XGBOOST_PARAM_GRID
        assert "subsample" in XGBOOST_PARAM_GRID

        # Full grid should have multiple options
        assert len(XGBOOST_PARAM_GRID["n_estimators"]) >= 3

    def test_fast_param_grid_structure(self) -> None:
        """Fast param grid has single values for quick training."""
        from raglite.forecasting.hybrid import XGBOOST_PARAM_GRID_FAST

        # Fast grid should have single values
        assert len(XGBOOST_PARAM_GRID_FAST["n_estimators"]) == 1
        assert len(XGBOOST_PARAM_GRID_FAST["max_depth"]) == 1
