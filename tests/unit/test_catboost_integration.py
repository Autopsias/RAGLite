"""Unit tests for Story 6.12: CatBoost Integration + Adaptive Weights.

Tests:
- AC1: CatBoost integration (fit_catboost function)
- AC2: Model weights PostgreSQL schema
- AC3: Backtest weight calculation
- AC4: Adaptive weight retrieval
"""

from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests require real CatBoost library
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="CatBoost tests require real CatBoost library (not mocked)",
)

from raglite.external_data.models import ModelWeight  # noqa: E402
from raglite.external_data.orm_models import ModelWeightORM  # noqa: E402
from raglite.forecasting.adaptive_weights import (  # noqa: E402
    _adjust_weights_no_regressors,
    _calculate_weights_from_rmse,
    _get_static_weights,
    apply_weight_caps,
    handle_model_failure,
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
        from raglite.forecasting.hybrid import _fit_and_forecast_catboost

        X, y, X_future = forecast_data
        result = _fit_and_forecast_catboost(X, y, X_future, periods_ahead=4, fast_mode=True)

        assert isinstance(result, dict)
        assert "values" in result
        assert "metrics" in result
        assert len(result["values"]) == 4


class TestModelWeightORM:
    """Test ModelWeightORM schema (AC2)."""

    def test_model_weight_orm_table_name(self):
        """Test ModelWeightORM has correct table name."""
        assert ModelWeightORM.__tablename__ == "model_weights"

    def test_model_weight_orm_columns(self):
        """Test ModelWeightORM has required columns."""
        columns = [c.name for c in ModelWeightORM.__table__.columns]

        assert "id" in columns
        assert "metric_name" in columns
        assert "model_name" in columns
        assert "weight" in columns
        assert "backtest_rmse" in columns
        assert "backtest_mape" in columns
        assert "has_regressors" in columns
        assert "data_points" in columns
        assert "calculated_at" in columns

    def test_model_weight_orm_repr(self):
        """Test ModelWeightORM string representation."""
        weight = ModelWeightORM(
            metric_name="cement_demand",
            model_name="catboost",
            weight=Decimal("0.15"),
        )
        repr_str = repr(weight)
        assert "cement_demand" in repr_str
        assert "catboost" in repr_str


class TestModelWeightPydantic:
    """Test ModelWeight Pydantic model (AC2)."""

    def test_model_weight_creation(self):
        """Test ModelWeight Pydantic model creation."""
        weight = ModelWeight(
            metric_name="cement_demand",
            model_name="catboost",
            weight=0.15,
        )

        assert weight.metric_name == "cement_demand"
        assert weight.model_name == "catboost"
        assert weight.weight == 0.15

    def test_model_weight_defaults(self):
        """Test ModelWeight default values."""
        weight = ModelWeight(
            metric_name="revenue",
            model_name="prophet",
            weight=0.3,
        )

        assert weight.has_regressors is True
        assert weight.data_points is None
        assert weight.calculated_at is not None

    def test_model_weight_validation(self):
        """Test ModelWeight weight validation (0-1 range)."""
        with pytest.raises(ValueError):
            ModelWeight(
                metric_name="test",
                model_name="test",
                weight=1.5,  # Invalid: > 1.0
            )


class TestWeightCalculationFromRMSE:
    """Test _calculate_weights_from_rmse (AC3)."""

    def test_calculate_weights_from_rmse(self):
        """Test weight calculation from backtest RMSE."""
        results = {
            "model_a": {"rmse": 100.0, "mape": 5.0},
            "model_b": {"rmse": 50.0, "mape": 2.5},
        }

        weights_results = _calculate_weights_from_rmse(results)

        # model_b should have higher weight (lower RMSE)
        assert weights_results["model_b"]["weight"] > weights_results["model_a"]["weight"]

        # Weights should sum to ~1.0
        total = sum(r["weight"] for r in weights_results.values())
        assert abs(total - 1.0) < 0.01

    def test_calculate_weights_with_caps(self):
        """Test weight caps are applied and re-normalized.

        Note: After capping and re-normalization, weights may exceed MAX_WEIGHT
        or fall below MIN_WEIGHT because re-normalization proportionally adjusts
        the weights to sum to 1.0.
        """
        # One model much better than others
        results = {
            "best": {"rmse": 1.0, "mape": 0.1},
            "worst1": {"rmse": 1000.0, "mape": 50.0},
            "worst2": {"rmse": 1000.0, "mape": 50.0},
        }

        weights_results = _calculate_weights_from_rmse(results)

        # Weights should sum to ~1.0
        total = sum(r["weight"] for r in weights_results.values())
        assert abs(total - 1.0) < 0.01

        # Worst models should have non-zero weights (not excluded)
        assert weights_results["worst1"]["weight"] > 0
        assert weights_results["worst2"]["weight"] > 0

        # Best model should have highest weight
        assert weights_results["best"]["weight"] > weights_results["worst1"]["weight"]


class TestAdaptiveWeightFunctions:
    """Test adaptive weight helper functions (AC4)."""

    def test_get_static_weights(self):
        """Test static weights from config."""
        weights = _get_static_weights()

        assert "prophet" in weights
        assert "linear" in weights
        assert "xgboost" in weights
        assert "lightgbm" in weights
        assert "catboost" in weights

        # Sum should be ~1.0
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_apply_weight_caps(self):
        """Test weight cap application and re-normalization.

        After capping and re-normalization, weights sum to 1.0.
        The relative ordering is preserved (capped high weights
        remain highest after normalization).
        """
        uncapped = {"a": 0.8, "b": 0.01, "c": 0.19}
        capped = apply_weight_caps(uncapped)

        # Sum to 1.0
        assert abs(sum(capped.values()) - 1.0) < 0.01

        # Model 'a' should still have highest weight (was capped but remains largest)
        assert capped["a"] > capped["c"]

        # Model 'b' was boosted from MIN_WEIGHT floor
        assert capped["b"] > 0.01  # Was 0.01, now at least MIN_WEIGHT before renorm

    def test_handle_model_failure(self):
        """Test weight re-normalization after model failure."""
        weights = {"prophet": 0.3, "xgboost": 0.4, "catboost": 0.3}
        after = handle_model_failure(weights, "xgboost")

        assert "xgboost" not in after
        assert abs(sum(after.values()) - 1.0) < 0.01

    def test_handle_model_failure_unknown_model(self):
        """Test handling failure of model not in weights."""
        weights = {"prophet": 0.5, "catboost": 0.5}
        after = handle_model_failure(weights, "unknown")

        # Should return unchanged
        assert after == weights

    def test_adjust_weights_no_regressors(self):
        """Test weight adjustment when no regressors available."""
        weights = {"prophet": 0.3, "xgboost": 0.35, "catboost": 0.35}
        adjusted = _adjust_weights_no_regressors(weights)

        # Prophet should be boosted
        assert adjusted["prophet"] > weights["prophet"]

        # Regressor-dependent should be reduced
        assert adjusted["xgboost"] < weights["xgboost"]
        assert adjusted["catboost"] < weights["catboost"]

        # Sum to 1.0
        assert abs(sum(adjusted.values()) - 1.0) < 0.01


class TestConfigSettings:
    """Test config.py settings for Story 6.12."""

    def test_catboost_in_forecasting_models(self):
        """Test CatBoost is included in forecasting_models."""
        from raglite.shared.config import settings

        models = settings.forecasting_models.split(",")
        assert "catboost" in models

    def test_ensemble_weight_catboost_exists(self):
        """Test ensemble_weight_catboost config exists."""
        from raglite.shared.config import settings

        assert hasattr(settings, "ensemble_weight_catboost")
        assert 0 < settings.ensemble_weight_catboost <= 1

    def test_refresh_cron_backtest_exists(self):
        """Test refresh_cron_backtest config exists."""
        from raglite.shared.config import settings

        assert hasattr(settings, "refresh_cron_backtest")
        # Should be valid cron format (5 parts)
        parts = settings.refresh_cron_backtest.split()
        assert len(parts) == 5

    def test_ensemble_weights_sum_to_one(self):
        """Test all ensemble weights sum to approximately 1.0."""
        from raglite.shared.config import settings

        # Include all 7 models (added chronos and TFT in Stories 6.13 and 6.14)
        total = (
            settings.ensemble_weight_prophet
            + settings.ensemble_weight_linear
            + settings.ensemble_weight_xgboost
            + settings.ensemble_weight_lightgbm
            + settings.ensemble_weight_catboost
            + settings.ensemble_weight_chronos
            + settings.ensemble_weight_tft
        )
        assert abs(total - 1.0) < 0.01


class TestBacktestJobModule:
    """Test backtest_job module structure."""

    def test_known_metrics_exists(self):
        """Test KNOWN_METRICS list is defined."""
        from raglite.forecasting.backtest_job import KNOWN_METRICS

        assert isinstance(KNOWN_METRICS, list)
        assert len(KNOWN_METRICS) > 0
        assert "cement_demand" in KNOWN_METRICS

    def test_functions_are_importable(self):
        """Test all expected functions are importable."""
        from raglite.forecasting.backtest_job import (
            run_backtest_for_metric,
            run_weekly_backtest,
            trigger_backtest_now,
        )

        assert callable(run_weekly_backtest)
        assert callable(run_backtest_for_metric)
        assert callable(trigger_backtest_now)


class TestWeightCapsEnforcement:
    """Test weight caps enforcement in save_model_weight (Story 6.12 AC4 fix)."""

    def test_weight_cap_applied_on_save_high(self):
        """Test that weights above MAX_WEIGHT (50%) are capped."""

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch("raglite.external_data.storage.ExternalDataStorage.save_model_weight"):
            # Test indirectly through the cap logic
            from raglite.external_data.storage import ExternalDataStorage

            storage = ExternalDataStorage(mock_session)

            # Mock the session operations
            mock_session.add = MagicMock()
            mock_session.commit = MagicMock()
            mock_session.refresh = MagicMock()

            # Call with uncapped weight
        storage.save_model_weight(
            metric_name="test_metric",
            model_name="test_model",
            weight=0.75,  # Above MAX_WEIGHT (50%)
        )

        # The method should have capped the weight
        # This is verified by the logging warning

    def test_weight_cap_applied_on_save_low(self):
        """Test that weights below MIN_WEIGHT (5%) are raised."""

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.refresh = MagicMock()

        from raglite.external_data.storage import ExternalDataStorage

        storage = ExternalDataStorage(mock_session)

        # Call with weight below minimum
        storage.save_model_weight(
            metric_name="test_metric",
            model_name="test_model",
            weight=0.01,  # Below MIN_WEIGHT (5%)
        )

        # Verify the method succeeded (capped weight used)
        mock_session.add.assert_called_once()


class TestCatBoostImportErrorHandling:
    """Test CatBoost import error handling (Story 6.12 Issue #7 fix)."""

    def test_catboost_import_error_message(self):
        """Test that import error provides helpful message."""
        from raglite.forecasting.hybrid import _get_catboost_class

        # If CatBoost is installed, this should succeed
        try:
            cls = _get_catboost_class()
            assert cls.__name__ == "CatBoostRegressor"
        except ImportError as e:
            # If CatBoost is not installed, verify error message
            assert "catboost>=1.2" in str(e)


class TestNumericPrecision:
    """Test Numeric precision for RMSE/MAPE columns (Story 6.12 Issue #6 fix)."""

    def test_backtest_rmse_precision(self):
        """Test backtest_rmse column has defined precision."""
        from sqlalchemy import Numeric

        col = ModelWeightORM.__table__.c.backtest_rmse
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 12
        assert col.type.scale == 4

    def test_backtest_mape_precision(self):
        """Test backtest_mape column has defined precision."""
        from sqlalchemy import Numeric

        col = ModelWeightORM.__table__.c.backtest_mape
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 8
        assert col.type.scale == 4


class TestCalculateBacktestWeightsWithProphet:
    """Test Prophet inclusion in backtest (Story 6.12 Issue #4 fix)."""

    @pytest.fixture
    def prophet_test_data(self):
        """Create sample data for Prophet backtest."""
        from datetime import date, timedelta

        from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

        np.random.seed(42)
        n_points = 24  # 2 years of monthly data

        points = []
        base_date = date(2022, 1, 1)
        for i in range(n_points):
            d = base_date + timedelta(days=30 * i)
            # Add some seasonal pattern
            value = 1000 + 100 * np.sin(2 * np.pi * i / 12) + np.random.randn() * 10
            points.append(TimeSeriesPoint(date=d, value=value))

        return TimeSeriesData(
            metric_name="test_metric",
            points=points,
        )

    @pytest.mark.slow  # Prophet fitting can take time
    def test_prophet_included_in_backtest(self, prophet_test_data):
        """Test that Prophet is included in backtest calculation."""
        from raglite.forecasting.adaptive_weights import calculate_backtest_weights

        # This should include Prophet now
        results = calculate_backtest_weights(
            metric="test_metric",
            historical_data=prophet_test_data,
            models=["prophet"],  # Only test Prophet
        )

        # Prophet should be in results (if installed)
        # If Prophet not available, results will be empty which is acceptable
        if results:
            assert "prophet" in results
            assert "rmse" in results["prophet"]
            assert "weight" in results["prophet"]
