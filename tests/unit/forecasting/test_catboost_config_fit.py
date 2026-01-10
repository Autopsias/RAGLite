"""Unit tests for Story 6.12: CatBoost Integration + Adaptive Weights.

Tests:
- AC1: CatBoost integration (fit_catboost function)
- AC2: Model weights PostgreSQL schema
- AC3: Backtest weight calculation
- AC4: Adaptive weight retrieval
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests require real CatBoost library
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="CatBoost tests require real CatBoost library (not mocked)",
)


class TestCatBoostConfig:
    """Test CatBoost configuration and lazy loading (AC1)."""

    def test_catboost_param_grid_exists(self):
        """Test CATBOOST_PARAM_GRID is defined correctly."""
        from raglite.forecasting.hybrid import CATBOOST_PARAM_GRID

        assert "iterations" in CATBOOST_PARAM_GRID
        assert "learning_rate" in CATBOOST_PARAM_GRID
        assert "depth" in CATBOOST_PARAM_GRID
        assert "l2_leaf_reg" in CATBOOST_PARAM_GRID

    def test_catboost_param_grid_fast_exists(self):
        """Test CATBOOST_PARAM_GRID_FAST is defined for testing."""
        from raglite.forecasting.hybrid import CATBOOST_PARAM_GRID_FAST

        assert "iterations" in CATBOOST_PARAM_GRID_FAST
        # Fast mode should have single values
        assert len(CATBOOST_PARAM_GRID_FAST["iterations"]) == 1

    def test_get_catboost_class_returns_regressor(self):
        """Test lazy-loading CatBoostRegressor class."""
        from raglite.forecasting.hybrid import _get_catboost_class

        CatBoostRegressor = _get_catboost_class()
        assert CatBoostRegressor is not None
        assert CatBoostRegressor.__name__ == "CatBoostRegressor"

    def test_get_catboost_class_caches_result(self):
        """Test that _get_catboost_class returns same class on repeated calls."""
        from raglite.forecasting.hybrid import _get_catboost_class

        cls1 = _get_catboost_class()
        cls2 = _get_catboost_class()
        assert cls1 is cls2


class TestFitCatBoost:
    """Test fit_catboost function (AC1)."""

    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        np.random.seed(42)
        n_samples = 20
        X = pd.DataFrame(
            {
                "feature1": np.random.randn(n_samples),
                "feature2": np.random.randn(n_samples) * 2,
            }
        )
        y = pd.Series(np.random.randn(n_samples) * 100 + 500)
        return X, y

    def test_fit_catboost_returns_model_and_metrics(self, sample_data):
        """Test fit_catboost returns model and metrics dict."""
        from raglite.forecasting.hybrid import fit_catboost

        X, y = sample_data
        model, metrics = fit_catboost(X, y, fast_mode=True)

        # Verify model
        assert model is not None
        assert hasattr(model, "predict")

        # Verify metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "mape" in metrics
        assert "best_params" in metrics

    def test_fit_catboost_metrics_are_positive(self, sample_data):
        """Test that error metrics are non-negative."""
        from raglite.forecasting.hybrid import fit_catboost

        X, y = sample_data
        _, metrics = fit_catboost(X, y, fast_mode=True)

        assert float(metrics["rmse"]) >= 0
        assert float(metrics["mae"]) >= 0
        assert float(metrics["mape"]) >= 0

    def test_fit_catboost_model_can_predict(self, sample_data):
        """Test that fitted model can make predictions."""
        from raglite.forecasting.hybrid import fit_catboost

        X, y = sample_data
        model, _ = fit_catboost(X, y, fast_mode=True)

        predictions = model.predict(X[:5])
        assert len(predictions) == 5
        assert all(np.isfinite(predictions))


class TestFitAndForecastCatBoost:
    """Test _fit_and_forecast_catboost for ThreadPoolExecutor."""

    @pytest.fixture
    def forecast_data(self):
        """Create sample data for forecasting."""
        np.random.seed(42)
        n_samples = 20
        X = pd.DataFrame(
            {
                "feature1": np.random.randn(n_samples),
                "feature2": np.random.randn(n_samples) * 2,
            }
        )
        y = pd.Series(np.random.randn(n_samples) * 100 + 500)
        X_future = pd.DataFrame(
            {
                "feature1": np.random.randn(4),
                "feature2": np.random.randn(4) * 2,
            }
        )
        return X, y, X_future

    def test_fit_and_forecast_returns_dict(self, forecast_data):
        """Test _fit_and_forecast_catboost returns dict with values and metrics."""
        from raglite.forecasting.models.catboost_model import _fit_and_forecast_catboost

        X, y, X_future = forecast_data
        result = _fit_and_forecast_catboost(X, y, X_future, periods_ahead=4, fast_mode=True)

        assert isinstance(result, dict)
        assert "values" in result
        assert "metrics" in result
        assert len(result["values"]) == 4
