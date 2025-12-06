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

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData


# Set DYLD_LIBRARY_PATH for XGBoost on macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/opt/libomp/lib")


class TestLinearRegressionFitting:
    """Tests for fit_linear_regression (AC3)."""

    def test_fit_linear_regression_basic(self) -> None:
        """AC3: Linear Regression fits with TimeSeriesSplit CV."""
        from raglite.forecasting.hybrid import fit_linear_regression

        # Create sample data
        X = pd.DataFrame(
            {
                "feature1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
                "feature2": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0],
            }
        )
        y = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0])

        model, metrics = fit_linear_regression(X, y, ["feature1", "feature2"])

        # Verify model is fitted
        assert hasattr(model, "predict")
        assert hasattr(model, "coef_")

        # Verify metrics are returned
        assert "rmse" in metrics
        assert isinstance(metrics["rmse"], float)
        assert metrics["rmse"] >= 0

    def test_fit_linear_regression_small_dataset(self) -> None:
        """AC3: Linear Regression handles small datasets gracefully."""
        from raglite.forecasting.hybrid import fit_linear_regression

        # Minimum viable dataset (3 points for 2-fold CV)
        X = pd.DataFrame({"feature": [1.0, 2.0, 3.0]})
        y = pd.Series([10.0, 20.0, 30.0])

        model, metrics = fit_linear_regression(X, y, ["feature"])

        assert hasattr(model, "predict")
        assert metrics["rmse"] >= 0


class TestXGBoostFitting:
    """Tests for fit_xgboost (AC4)."""

    def test_fit_xgboost_fast_mode(self) -> None:
        """AC4: XGBoost fits with fast mode (reduced grid)."""
        from raglite.forecasting.hybrid import fit_xgboost

        # Create sample data
        X = pd.DataFrame(
            {
                "feature1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
                "feature2": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0],
            }
        )
        y = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0])

        model, metrics = fit_xgboost(X, y, fast_mode=True)

        # Verify model is fitted
        assert hasattr(model, "predict")

        # Verify metrics include best_params
        assert "rmse" in metrics
        assert "best_params" in metrics
        assert isinstance(metrics["best_params"], dict)

    def test_fit_xgboost_returns_best_params(self) -> None:
        """AC4: XGBoost returns best hyperparameters from GridSearchCV."""
        from raglite.forecasting.hybrid import fit_xgboost

        X = pd.DataFrame(
            {
                "feature1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            }
        )
        y = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0])

        _, metrics = fit_xgboost(X, y, fast_mode=True)

        best_params = metrics["best_params"]
        assert "n_estimators" in best_params
        assert "max_depth" in best_params
        assert "learning_rate" in best_params


class TestWeightedAverage:
    """Tests for _calculate_weighted_average (AC5)."""

    def test_weighted_average_basic(self) -> None:
        """AC5: Weighted average calculates correctly."""
        from raglite.forecasting.hybrid import _calculate_weighted_average

        predictions = {
            "prophet": [100.0, 110.0, 120.0],
            "linear": [90.0, 100.0, 110.0],
            "xgboost": [95.0, 105.0, 115.0],
        }
        weights = {"prophet": 0.4, "linear": 0.3, "xgboost": 0.3}
        models = ["prophet", "linear", "xgboost"]

        result = _calculate_weighted_average(predictions, weights, models)

        # Expected: 0.4*100 + 0.3*90 + 0.3*95 = 40 + 27 + 28.5 = 95.5
        assert len(result) == 3
        assert abs(result[0] - 95.5) < 0.01

    def test_weighted_average_normalizes_missing_models(self) -> None:
        """AC5: Weights are normalized for available models only."""
        from raglite.forecasting.hybrid import _calculate_weighted_average

        predictions = {
            "prophet": [100.0, 110.0],
            "linear": [90.0, 100.0],
        }
        # XGBoost weight ignored because model not in predictions
        weights = {"prophet": 0.4, "linear": 0.3, "xgboost": 0.3}
        models = ["prophet", "linear"]  # Only 2 models available

        result = _calculate_weighted_average(predictions, weights, models)

        # Normalized: prophet=0.4/(0.4+0.3)=0.571, linear=0.3/(0.4+0.3)=0.429
        # Expected: 0.571*100 + 0.429*90 = 57.1 + 38.6 = 95.7
        assert len(result) == 2
        assert 95.0 < result[0] < 96.0

    def test_weighted_average_equal_weights_when_zero(self) -> None:
        """AC5: Equal weights applied when all weights are zero."""
        from raglite.forecasting.hybrid import _calculate_weighted_average

        predictions = {
            "prophet": [100.0],
            "linear": [80.0],
        }
        weights = {}  # No weights defined
        models = ["prophet", "linear"]

        result = _calculate_weighted_average(predictions, weights, models)

        # Equal weights: (100 + 80) / 2 = 90
        assert abs(result[0] - 90.0) < 0.01


class TestEnsembleSettings:
    """Tests for Settings configuration (AC2)."""

    def test_default_ensemble_weights(self) -> None:
        """AC2: Default ensemble weights match story requirements."""
        from raglite.shared.config import Settings

        # Create fresh settings instance
        settings = Settings()

        assert settings.ensemble_weight_prophet == 0.4
        assert settings.ensemble_weight_linear == 0.3
        assert settings.ensemble_weight_xgboost == 0.3
        assert settings.forecasting_models == "prophet,linear,xgboost"

    def test_ensemble_weights_from_env(self) -> None:
        """AC2: Ensemble weights can be overridden via environment."""
        import os

        from raglite.shared.config import Settings

        # Set custom weights via env
        os.environ["ENSEMBLE_WEIGHT_PROPHET"] = "0.5"
        os.environ["ENSEMBLE_WEIGHT_LINEAR"] = "0.25"
        os.environ["ENSEMBLE_WEIGHT_XGBOOST"] = "0.25"

        try:
            settings = Settings()
            assert settings.ensemble_weight_prophet == 0.5
            assert settings.ensemble_weight_linear == 0.25
            assert settings.ensemble_weight_xgboost == 0.25
        finally:
            # Cleanup
            del os.environ["ENSEMBLE_WEIGHT_PROPHET"]
            del os.environ["ENSEMBLE_WEIGHT_LINEAR"]
            del os.environ["ENSEMBLE_WEIGHT_XGBOOST"]


class TestForecastResultEnsembleFields:
    """Tests for ForecastResult ensemble fields (AC1)."""

    def test_forecast_result_has_ensemble_fields(self) -> None:
        """AC1: ForecastResult includes ensemble-specific fields."""
        from raglite.shared.models import ForecastResult

        result = ForecastResult(
            metric_name="revenue",
            model_type="ensemble",
            ensemble_models=["prophet", "linear", "xgboost"],
            individual_predictions={
                "prophet": [100.0, 110.0],
                "linear": [95.0, 105.0],
                "xgboost": [98.0, 108.0],
            },
            ensemble_weights={"prophet": 0.4, "linear": 0.3, "xgboost": 0.3},
        )

        assert result.model_type == "ensemble"
        assert len(result.ensemble_models) == 3
        assert "prophet" in result.individual_predictions
        assert result.ensemble_weights["prophet"] == 0.4

    def test_forecast_result_defaults_empty_ensemble(self) -> None:
        """AC1: ForecastResult defaults to empty ensemble fields."""
        from raglite.shared.models import ForecastResult

        result = ForecastResult(metric_name="revenue")

        assert result.ensemble_models == []
        assert result.individual_predictions == {}
        assert result.ensemble_weights == {}


class TestForecastQueryRequest:
    """Tests for ForecastQueryRequest model_type field."""

    def test_forecast_query_request_default_model_type(self) -> None:
        """ForecastQueryRequest defaults to 'prophet' model type."""
        from raglite.shared.models import ForecastQueryRequest

        request = ForecastQueryRequest(metric="revenue")

        assert request.model_type == "prophet"

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
        from raglite.forecasting.hybrid import generate_ensemble_forecast

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
                    )
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
        from raglite.forecasting.hybrid import generate_ensemble_forecast

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
