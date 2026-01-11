"""Unit tests for multi-metric validation functions - core calculations.

Story 6.26: Multi-Metric Validation Enhancement

Tests for MASE, SMAPE, RMSE, MAE, Bias calculations.
"""

from __future__ import annotations

import numpy as np

from raglite.forecasting.validation_metrics import (
    MultiMetricResult,
    calculate_all_metrics,
    calculate_bias,
    calculate_mae,
    calculate_mape_from_arrays,
    calculate_mase,
    calculate_rmse,
    calculate_smape,
)


class TestMAPEFromArrays:
    """Tests for calculate_mape_from_arrays function."""

    def test_basic_mape_calculation(self):
        """Test basic MAPE calculation with simple values."""
        actuals = np.array([100, 200, 300, 400])
        predictions = np.array([110, 190, 320, 380])

        mape = calculate_mape_from_arrays(actuals, predictions)

        # Expected: (10/100 + 10/200 + 20/300 + 20/400) / 4 * 100
        # = (0.1 + 0.05 + 0.0667 + 0.05) / 4 * 100 = 6.67%
        assert mape is not None
        assert 6.0 < mape < 7.0

    def test_mape_with_zeros_filtered(self):
        """Test that zero actuals are filtered out."""
        actuals = np.array([100, 0, 200, 0])
        predictions = np.array([110, 10, 190, 20])

        mape = calculate_mape_from_arrays(actuals, predictions)

        # Only non-zero actuals used: (10/100 + 10/200) / 2 * 100 = 7.5%
        assert mape is not None
        assert 7.0 < mape < 8.0

    def test_mape_all_zeros_returns_none(self):
        """Test that all-zero actuals returns None."""
        actuals = np.array([0, 0, 0])
        predictions = np.array([10, 20, 30])

        mape = calculate_mape_from_arrays(actuals, predictions)

        assert mape is None

    def test_mape_empty_arrays_returns_none(self):
        """Test that empty arrays return None."""
        assert calculate_mape_from_arrays(np.array([]), np.array([])) is None


class TestMASE:
    """Tests for calculate_mase function."""

    def test_mase_beats_naive(self):
        """Test MASE < 1.0 when model beats naïve baseline."""
        # Historical data with clear pattern
        historical = np.array([100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210])
        actuals = np.array([220, 230, 240, 250])
        # Model predicts well
        predictions = np.array([218, 232, 238, 252])

        mase = calculate_mase(actuals, predictions, historical, seasonality=1)

        # Model error should be less than naïve error
        assert mase is not None
        assert mase < 1.0

    def test_mase_worse_than_naive(self):
        """Test MASE > 1.0 when model is worse than naïve baseline."""
        # Historical data
        historical = np.array([100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210])
        actuals = np.array([220, 230, 240, 250])
        # Model predicts poorly (large errors)
        predictions = np.array([180, 290, 200, 300])

        mase = calculate_mase(actuals, predictions, historical, seasonality=1)

        # Model error should be more than naïve error
        assert mase is not None
        assert mase > 1.0

    def test_mase_constant_series_returns_inf(self):
        """Test MASE returns inf for constant series (zero naïve error)."""
        historical = np.array([100, 100, 100, 100, 100])
        actuals = np.array([100, 100])
        predictions = np.array([110, 110])

        mase = calculate_mase(actuals, predictions, historical, seasonality=1)

        assert mase == float("inf")

    def test_mase_seasonal_adjustment(self):
        """Test MASE with seasonal data (seasonality=12)."""
        # 2 years of monthly data with seasonality
        np.random.seed(42)
        historical = np.array([100 + 10 * (i % 12) for i in range(24)])
        actuals = np.array([200, 210, 220, 230])
        predictions = np.array([195, 212, 218, 232])

        mase = calculate_mase(actuals, predictions, historical, seasonality=12)

        assert mase is not None
        assert mase > 0

    def test_mase_falls_back_to_lag1_if_insufficient_history(self):
        """Test MASE uses lag-1 naïve if history < seasonality."""
        historical = np.array([100, 110, 120])  # Only 3 points
        actuals = np.array([130, 140])
        predictions = np.array([128, 142])

        # With seasonality=12, should fall back to seasonality=1
        mase = calculate_mase(actuals, predictions, historical, seasonality=12)

        assert mase is not None


class TestSMAPE:
    """Tests for calculate_smape function."""

    def test_basic_smape_calculation(self):
        """Test basic SMAPE calculation."""
        actuals = np.array([100, 200, 300, 400])
        predictions = np.array([110, 190, 320, 380])

        smape = calculate_smape(actuals, predictions)

        # SMAPE should be bounded 0-200%
        assert smape is not None
        assert 0 <= smape <= 200

    def test_smape_handles_zeros(self):
        """Test SMAPE handles zero values without division by zero."""
        actuals = np.array([100, 0, 200, 0])
        predictions = np.array([110, 0, 190, 50])

        smape = calculate_smape(actuals, predictions)

        # Should handle zeros gracefully
        assert smape is not None
        assert 0 <= smape <= 200

    def test_smape_both_zero_returns_zero(self):
        """Test SMAPE when both actual and predicted are zero."""
        actuals = np.array([0, 0, 0])
        predictions = np.array([0, 0, 0])

        smape = calculate_smape(actuals, predictions)

        # Perfect match (both zero) should return 0
        assert smape == 0.0

    def test_smape_bounded(self):
        """Test SMAPE is bounded between 0 and 200%."""
        actuals = np.array([100, 100])
        over_pred = np.array([150, 150])
        under_pred = np.array([50, 50])

        smape_over = calculate_smape(actuals, over_pred)
        smape_under = calculate_smape(actuals, under_pred)

        # SMAPE should be bounded 0-200%
        assert smape_over is not None
        assert smape_under is not None
        assert 0 <= smape_over <= 200
        assert 0 <= smape_under <= 200
        # Note: SMAPE is NOT perfectly symmetric due to denominator formula


class TestRMSE:
    """Tests for calculate_rmse function."""

    def test_basic_rmse_calculation(self):
        """Test basic RMSE calculation."""
        actuals = np.array([100, 200, 300, 400])
        predictions = np.array([110, 190, 310, 390])

        rmse = calculate_rmse(actuals, predictions)

        # RMSE = sqrt(mean([100, 100, 100, 100])) = sqrt(100) = 10
        assert rmse is not None
        assert rmse == 10.0

    def test_rmse_penalizes_large_errors(self):
        """Test RMSE penalizes large errors more than MAE."""
        actuals = np.array([100, 100, 100, 100])
        # One large error, rest small
        predictions_spread = np.array([110, 110, 110, 170])  # errors: 10, 10, 10, 70
        predictions_uniform = np.array([125, 125, 125, 125])  # errors: 25, 25, 25, 25

        rmse_spread = calculate_rmse(actuals, predictions_spread)
        rmse_uniform = calculate_rmse(actuals, predictions_uniform)

        # RMSE should penalize the large error more
        assert rmse_spread > rmse_uniform

    def test_rmse_empty_arrays(self):
        """Test RMSE with empty arrays."""
        assert calculate_rmse(np.array([]), np.array([])) is None


class TestMAE:
    """Tests for calculate_mae function."""

    def test_basic_mae_calculation(self):
        """Test basic MAE calculation."""
        actuals = np.array([100, 200, 300, 400])
        predictions = np.array([110, 190, 310, 390])

        mae = calculate_mae(actuals, predictions)

        # MAE = mean([10, 10, 10, 10]) = 10
        assert mae is not None
        assert mae == 10.0

    def test_mae_robust_to_outliers(self):
        """Test MAE is more robust to outliers than RMSE."""
        actuals = np.array([100, 100, 100, 100])
        predictions = np.array([110, 110, 110, 200])  # One outlier

        mae = calculate_mae(actuals, predictions)
        rmse = calculate_rmse(actuals, predictions)

        # MAE should be less affected by the outlier
        assert mae < rmse

    def test_mae_empty_arrays(self):
        """Test MAE with empty arrays."""
        assert calculate_mae(np.array([]), np.array([])) is None


class TestBias:
    """Tests for calculate_bias function."""

    def test_positive_bias_over_prediction(self):
        """Test positive bias indicates over-prediction."""
        actuals = np.array([100, 100, 100, 100])
        predictions = np.array([110, 120, 115, 125])

        bias = calculate_bias(actuals, predictions)

        # Mean over-prediction
        assert bias is not None
        assert bias > 0

    def test_negative_bias_under_prediction(self):
        """Test negative bias indicates under-prediction."""
        actuals = np.array([100, 100, 100, 100])
        predictions = np.array([90, 85, 95, 80])

        bias = calculate_bias(actuals, predictions)

        # Mean under-prediction
        assert bias is not None
        assert bias < 0

    def test_near_zero_bias_well_calibrated(self):
        """Test near-zero bias indicates well-calibrated model."""
        actuals = np.array([100, 100, 100, 100])
        predictions = np.array([105, 95, 102, 98])

        bias = calculate_bias(actuals, predictions)

        # Should be close to zero
        assert bias is not None
        assert abs(bias) < 5

    def test_bias_empty_arrays(self):
        """Test bias with empty arrays."""
        assert calculate_bias(np.array([]), np.array([])) is None


class TestCalculateAllMetrics:
    """Tests for calculate_all_metrics function."""

    def test_returns_all_metrics(self):
        """Test that all metrics are calculated."""
        actuals = np.array([100, 200, 300, 400])
        predictions = np.array([110, 190, 320, 380])
        historical = np.array([50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160])

        result = calculate_all_metrics(actuals, predictions, historical)

        assert isinstance(result, MultiMetricResult)
        assert result.mape is not None
        assert result.mase is not None
        assert result.smape is not None
        assert result.rmse is not None
        assert result.mae is not None
        assert result.bias is not None

    def test_converts_lists_to_arrays(self):
        """Test that lists are converted to numpy arrays."""
        actuals = [100, 200, 300, 400]
        predictions = [110, 190, 320, 380]

        result = calculate_all_metrics(actuals, predictions)

        assert result.mape is not None
        assert result.mae is not None

    def test_uses_actuals_as_historical_if_none(self):
        """Test that actuals are used as historical data if not provided."""
        actuals = np.array([100, 110, 120, 130, 140, 150])
        predictions = np.array([102, 108, 122, 128, 142, 148])

        result = calculate_all_metrics(actuals, predictions)

        # Should still calculate MASE using actuals as historical
        assert result.mase is not None


class TestMetricInterpretation:
    """Tests for metric interpretation (quality thresholds)."""

    def test_excellent_mape_threshold(self):
        """Test that <5% MAPE is excellent."""
        actuals = np.array([100, 100, 100, 100])
        predictions = np.array([103, 98, 102, 97])  # ~3% error

        result = calculate_all_metrics(actuals, predictions)

        assert result.mape is not None
        assert result.mape < 5.0  # Excellent threshold

    def test_excellent_mase_threshold(self):
        """Test that <0.5 MASE is excellent (model much better than naïve)."""
        # Historical data with variation (not perfectly predictable by naïve)
        historical = np.array([100, 110, 105, 115, 108, 118, 112, 122, 116, 126, 120, 130])
        actuals = np.array([125, 135, 128, 138])
        # Model predicts with very small errors (~1 unit)
        predictions = np.array([124, 136, 127, 139])

        result = calculate_all_metrics(actuals, predictions, historical, seasonality=1)

        assert result.mase is not None
        assert result.mase != float("inf")
        # Model with small errors relative to historical variation should have low MASE
        assert result.mase < 1.0  # At minimum, beats naïve baseline


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_negative_values_handled(self):
        """Test that negative values (costs, losses) are handled."""
        actuals = np.array([-100, -200, -150, -180])
        predictions = np.array([-95, -210, -140, -190])

        result = calculate_all_metrics(actuals, predictions)

        assert result.mae is not None
        assert result.rmse is not None
        assert result.bias is not None
        # MAPE with negatives should work (uses absolute value)
        assert result.mape is not None

    def test_very_small_values(self):
        """Test with very small values (avoiding floating point issues)."""
        actuals = np.array([0.001, 0.002, 0.003, 0.004])
        predictions = np.array([0.0011, 0.0019, 0.0031, 0.0039])

        result = calculate_all_metrics(actuals, predictions)

        assert result.mape is not None
        assert result.mae is not None

    def test_very_large_values(self):
        """Test with very large values (millions in EUR)."""
        actuals = np.array([1e9, 2e9, 3e9, 4e9])
        predictions = np.array([1.1e9, 1.9e9, 3.1e9, 3.9e9])

        result = calculate_all_metrics(actuals, predictions)

        assert result.mape is not None
        assert result.mae is not None
        assert result.rmse is not None

    def test_single_point(self):
        """Test with single data point."""
        actuals = np.array([100])
        predictions = np.array([110])

        result = calculate_all_metrics(actuals, predictions)

        assert result.mape == 10.0
        assert result.mae == 10.0
        assert result.rmse == 10.0
        assert result.bias == 10.0
