"""Unit tests for Story 6.4: Model Ensemble Framework.

Tests ensemble forecasting components including:
- Linear Regression fitting (AC3)
- XGBoost fitting with GridSearchCV (AC4)
- Weighted average calculation (AC5)
- Fallback strategies (AC6)
- Settings configuration (AC2)
"""

import os
from typing import TYPE_CHECKING

import pandas as pd
import pytest

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests require real XGBoost/sklearn for ensemble model fitting
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="Ensemble forecasting tests require real XGBoost/sklearn (not mocked)",
)

if TYPE_CHECKING:
    pass


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
        from raglite.forecasting.ensemble import _calculate_weighted_average

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
        from raglite.forecasting.ensemble import _calculate_weighted_average

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
        from raglite.forecasting.ensemble import _calculate_weighted_average

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
        """AC2: Default ensemble weights match story requirements.

        Story 6.12: Added CatBoost with 12% weight
        Story 6.13: Added Chronos-2 with 12% weight
        Story 6.14: Added TFT with 15% weight
        Current weights (all 7 models = 100%):
        - Prophet: 23%
        - Linear: 11%
        - XGBoost: 15%
        - LightGBM: 15%
        - CatBoost: 12%
        - Chronos: 12%
        - TFT: 12%
        """
        from raglite.shared.config import Settings

        # Create fresh settings instance
        settings = Settings()

        # Story 6.14: Updated weights with all 7 models (sum to 1.0)
        assert settings.ensemble_weight_prophet == 0.23
        assert settings.ensemble_weight_linear == 0.11
        assert settings.ensemble_weight_xgboost == 0.15
        assert settings.ensemble_weight_lightgbm == 0.15
        assert settings.ensemble_weight_catboost == 0.12
        assert settings.ensemble_weight_chronos == 0.12
        assert settings.ensemble_weight_tft == 0.12
        assert settings.forecasting_models == "prophet,linear,xgboost,lightgbm,catboost,chronos,tft"

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
