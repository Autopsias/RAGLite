"""Unit tests for multi-variate forecasting functions.

Story 6.3: Prophet Multi-Variate Forecasting (AC9)

Tests for regressor selection, preparation, accuracy calculation,
and future regressor generation.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests require real Prophet for multi-variate forecasting
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="Multi-variate forecasting tests require real Prophet (not mocked)",
)

from raglite.forecasting.hybrid import (  # noqa: E402
    _generate_future_regressors,
    calculate_accuracy,
    get_baseline_rmse,
    prepare_regressors,
    select_regressors,
)


class TestSelectRegressors:
    """Tests for select_regressors() function."""

    def test_select_regressors_empty_candidates(self) -> None:
        """Test with no candidate regressors."""
        target = pd.Series([1, 2, 3, 4, 5])
        result = select_regressors(target, {})
        assert result == []

    def test_select_regressors_perfectly_correlated(self) -> None:
        """Test with perfectly correlated regressor."""
        dates = pd.date_range("2024-01-01", periods=10, freq="ME")
        target = pd.Series(range(10), index=dates)
        candidates = {
            "perfect": pd.Series(range(10), index=dates),  # r=1.0
            "weak": pd.Series([1, 1, 1, 1, 1, 1.1, 1.1, 1.1, 1.1, 1.1], index=dates),  # r<0.5
        }

        result = select_regressors(target, candidates, min_correlation=0.5)

        assert "perfect" in result
        # "weak" might be filtered out if correlation is truly low
        # The test validates that "perfect" is selected

    def test_select_regressors_negative_correlation(self) -> None:
        """Test that negative correlation is also selected."""
        dates = pd.date_range("2024-01-01", periods=10, freq="ME")
        target = pd.Series(range(10), index=dates)
        candidates = {
            "negative": pd.Series(range(9, -1, -1), index=dates),  # r=-1.0
        }

        result = select_regressors(target, candidates, min_correlation=0.5)

        assert "negative" in result  # abs(r) >= 0.5

    def test_select_regressors_top_n_limit(self) -> None:
        """Test that only top N regressors are selected."""
        dates = pd.date_range("2024-01-01", periods=10, freq="ME")
        target = pd.Series(range(10), index=dates)

        # Create 5 candidates with varying correlations
        candidates = {f"reg_{i}": pd.Series(range(i, 10 + i), index=dates) for i in range(5)}

        result = select_regressors(target, candidates, top_n=2, min_correlation=0.3)

        assert len(result) <= 2

    def test_select_regressors_handles_nan(self) -> None:
        """Test handling of NaN values in candidates."""
        dates = pd.date_range("2024-01-01", periods=10, freq="ME")
        target = pd.Series(range(10), index=dates)
        candidates = {
            "with_nan": pd.Series([1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10], index=dates),
        }

        # Should not raise, but may or may not select depending on correlation
        result = select_regressors(target, candidates)
        assert isinstance(result, list)


class TestPrepareRegressors:
    """Tests for prepare_regressors() function."""

    def test_prepare_regressors_aligned(self) -> None:
        """Test regressors already aligned to target index."""
        target_index = pd.date_range("2024-01-01", periods=5, freq="ME")
        regressors = {
            "aligned": pd.Series([1, 2, 3, 4, 5], index=target_index),
        }

        result = prepare_regressors(regressors, target_index)

        assert "aligned" in result
        assert len(result["aligned"]) == 5
        assert not result["aligned"].isna().any()

    def test_prepare_regressors_needs_interpolation(self) -> None:
        """Test regressors with missing values get interpolated."""
        # Use 20 periods so 1 NaN = 5% missing (under 10% threshold)
        target_index = pd.date_range("2024-01-01", periods=20, freq="ME")
        values = list(range(1, 21))
        values[5] = np.nan  # 1 out of 20 = 5% missing
        regressors = {
            "sparse": pd.Series(values, index=target_index),
        }

        result = prepare_regressors(regressors, target_index)

        assert not result["sparse"].isna().any()
        # Check interpolation worked (linear between 5 and 7)
        assert result["sparse"].iloc[5] == 6.0  # interpolated

    def test_prepare_regressors_exceeds_missing_threshold(self) -> None:
        """Test that >30% missing skips regressor (Story 6.10.4 behavior change).

        Story 6.10.4: Changed from raising ValueError to skipping regressors
        with too much missing data. This allows forecasting to continue with
        available regressors instead of failing entirely.

        Note: MAX_MISSING_RATIO was increased from 10% to 30% in Story 6.10.4
        to tolerate date range mismatches between external and SECIL data.
        """
        target_index = pd.date_range("2024-01-01", periods=10, freq="ME")
        # 4 out of 10 = 40% missing > 30% threshold
        regressors = {
            "too_sparse": pd.Series(
                [1, np.nan, np.nan, np.nan, np.nan, 6, 7, 8, 9, 10], index=target_index
            ),
        }

        # Story 6.10.4: Now skips regressor instead of raising
        result = prepare_regressors(regressors, target_index)
        assert "too_sparse" not in result  # Regressor should be skipped

    def test_prepare_regressors_different_index(self) -> None:
        """Test regressors with non-overlapping index are skipped (Story 6.10.4 behavior change).

        Story 6.10.4: Changed from raising ValueError to skipping regressors
        with non-overlapping indices. This allows forecasting to continue with
        available regressors instead of failing entirely.
        """
        target_index = pd.date_range("2024-01-01", periods=10, freq="ME")
        # Completely non-overlapping dates - will result in 100% missing
        regressor_index = pd.date_range("2025-01-01", periods=5, freq="ME")

        regressors = {
            "misaligned": pd.Series([1, 2, 3, 4, 5], index=regressor_index),
        }

        # Story 6.10.4: Now skips regressor instead of raising
        result = prepare_regressors(regressors, target_index)
        assert "misaligned" not in result  # Regressor should be skipped


class TestCalculateAccuracy:
    """Tests for calculate_accuracy() function."""

    def test_calculate_accuracy_insufficient_data(self) -> None:
        """Test returns zeros with insufficient data."""
        from unittest.mock import MagicMock

        mock_model = MagicMock()
        df = pd.DataFrame({"ds": pd.date_range("2024-01-01", periods=5, freq="ME"), "y": range(5)})

        result = calculate_accuracy(mock_model, df)

        assert result == {"rmse": 0.0, "mae": 0.0, "mape": 0.0}

    def test_calculate_accuracy_returns_dict(self) -> None:
        """Test returns dictionary with required keys."""
        from unittest.mock import MagicMock, patch

        mock_model = MagicMock()
        df = pd.DataFrame(
            {"ds": pd.date_range("2024-01-01", periods=24, freq="ME"), "y": range(24)}
        )

        # Mock cross_validation and performance_metrics from prophet.diagnostics
        with (
            patch("prophet.diagnostics.cross_validation") as mock_cv,
            patch("prophet.diagnostics.performance_metrics") as mock_pm,
        ):
            mock_cv.return_value = pd.DataFrame()
            mock_pm.return_value = pd.DataFrame({"rmse": [10.0], "mae": [8.0], "mape": [0.15]})

            result = calculate_accuracy(mock_model, df)

        assert "rmse" in result
        assert "mae" in result
        assert "mape" in result


class TestGetBaselineRMSE:
    """Tests for get_baseline_rmse() function."""

    def test_get_baseline_rmse_from_env(self, monkeypatch) -> None:
        """Test fetching baseline from environment variable."""
        monkeypatch.setenv("BASELINE_RMSE_REVENUE", "12.5")

        result = get_baseline_rmse("revenue")

        assert result == 12.5

    def test_get_baseline_rmse_not_found(self) -> None:
        """Test returns None when baseline not found."""
        result = get_baseline_rmse("nonexistent_metric_xyz")

        assert result is None

    def test_get_baseline_rmse_invalid_env(self, monkeypatch) -> None:
        """Test handles invalid environment variable value."""
        monkeypatch.setenv("BASELINE_RMSE_REVENUE", "not_a_number")

        result = get_baseline_rmse("revenue")

        # Should fall through to file check, likely None
        assert result is None or isinstance(result, float)


class TestGenerateFutureRegressors:
    """Tests for _generate_future_regressors() function."""

    def test_future_regressors_constant_strategy(self) -> None:
        """Test constant strategy uses last value."""
        historical_dates = pd.date_range("2024-01-01", periods=5, freq="ME")
        future_dates = pd.date_range("2024-06-01", periods=3, freq="ME")

        regressors = {
            "reg1": pd.Series([1, 2, 3, 4, 5], index=historical_dates),
        }

        result = _generate_future_regressors(regressors, future_dates, strategy="constant")

        # Future values should all be 5 (last historical value)
        future_values = result["reg1"].reindex(future_dates)
        assert all(future_values == 5)

    def test_future_regressors_extrapolate_strategy(self) -> None:
        """Test extrapolate strategy uses linear extrapolation."""
        historical_dates = pd.date_range("2024-01-01", periods=5, freq="ME")
        future_dates = pd.date_range("2024-06-01", periods=3, freq="ME")

        # Linear series: 1, 2, 3, 4, 5 -> should extrapolate to 6, 7, 8
        regressors = {
            "linear": pd.Series([1, 2, 3, 4, 5], index=historical_dates),
        }

        result = _generate_future_regressors(regressors, future_dates, strategy="extrapolate")

        future_values = result["linear"].reindex(future_dates)
        # Should be approximately 6, 7, 8 (linear extrapolation)
        assert future_values.iloc[0] > 5  # Greater than last historical

    def test_future_regressors_provided_strategy_missing(self) -> None:
        """Test provided strategy raises when future values missing."""
        historical_dates = pd.date_range("2024-01-01", periods=5, freq="ME")
        future_dates = pd.date_range("2024-06-01", periods=3, freq="ME")

        regressors = {
            "incomplete": pd.Series([1, 2, 3, 4, 5], index=historical_dates),
        }

        with pytest.raises(ValueError, match="requires future values"):
            _generate_future_regressors(regressors, future_dates, strategy="provided")

    def test_future_regressors_provided_strategy_complete(self) -> None:
        """Test provided strategy works with complete future values."""
        historical_dates = pd.date_range("2024-01-01", periods=5, freq="ME")
        future_dates = pd.date_range("2024-06-01", periods=3, freq="ME")
        # Use union to combine without duplicates
        all_dates = historical_dates.union(future_dates)

        # Include future values
        regressors = {
            "complete": pd.Series([1, 2, 3, 4, 5, 6, 7, 8], index=all_dates),
        }

        result = _generate_future_regressors(regressors, future_dates, strategy="provided")

        future_values = result["complete"].reindex(future_dates)
        assert list(future_values) == [6, 7, 8]

    def test_future_regressors_invalid_strategy(self) -> None:
        """Test invalid strategy raises ValueError."""
        future_dates = pd.date_range("2024-06-01", periods=3, freq="ME")
        regressors = {"reg1": pd.Series([1, 2, 3])}

        with pytest.raises(ValueError, match="Unknown future regressor strategy"):
            _generate_future_regressors(regressors, future_dates, strategy="invalid")


class TestForecastResultMultiVariateFields:
    """Tests for new multi-variate fields in ForecastResult."""

    def test_forecast_result_default_model_type(self) -> None:
        """Test default model_type is univariate."""
        from raglite.shared.models import ForecastResult

        result = ForecastResult(metric_name="revenue")

        assert result.model_type == "prophet_univariate"

    def test_forecast_result_multivariate_model_type(self) -> None:
        """Test setting multivariate model_type."""
        from raglite.shared.models import ForecastResult

        result = ForecastResult(
            metric_name="revenue",
            model_type="prophet_multivariate",
        )

        assert result.model_type == "prophet_multivariate"

    def test_forecast_result_accuracy_metrics(self) -> None:
        """Test accuracy_metrics field."""
        from raglite.shared.models import ForecastResult

        metrics = {"rmse": 10.5, "mae": 8.2, "mape": 0.12}
        result = ForecastResult(
            metric_name="revenue",
            accuracy_metrics=metrics,
        )

        assert result.accuracy_metrics == metrics

    def test_forecast_result_regressors_used(self) -> None:
        """Test regressors_used field."""
        from raglite.shared.models import ForecastResult

        regressors = ["electricity_price", "cement_consumption", "building_permits"]
        result = ForecastResult(
            metric_name="revenue",
            regressors_used=regressors,
        )

        assert result.regressors_used == regressors

    def test_forecast_result_improvement_vs_baseline(self) -> None:
        """Test improvement_vs_baseline field."""
        from raglite.shared.models import ForecastResult

        result = ForecastResult(
            metric_name="revenue",
            improvement_vs_baseline=15.5,  # 15.5% improvement
        )

        assert result.improvement_vs_baseline == 15.5

    def test_forecast_result_all_multivariate_fields(self) -> None:
        """Test all multi-variate fields together."""
        from raglite.shared.models import ForecastResult

        result = ForecastResult(
            metric_name="cement_sales",
            model_type="prophet_multivariate",
            accuracy_metrics={"rmse": 8.5, "mae": 6.0, "mape": 0.08},
            regressors_used=["electricity_price", "diesel_price", "temperature"],
            improvement_vs_baseline=22.3,
        )

        assert result.model_type == "prophet_multivariate"
        assert result.accuracy_metrics["rmse"] == 8.5
        assert len(result.regressors_used) == 3
        assert result.improvement_vs_baseline == 22.3
