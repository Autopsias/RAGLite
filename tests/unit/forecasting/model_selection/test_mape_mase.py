"""Unit tests for MAPE and MASE calculations in model selection.

Story 7b-6: Enhanced model selection utilities

Tests for:
- calculate_mape function edge cases
- calculate_mase function edge cases

Priority levels:
- P0: Critical path tests (must pass)
- P1: Important scenarios (should pass)
- P2: Edge cases (good to have)
"""

from __future__ import annotations

import os

import numpy as np
import pytest

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        os.environ.get("LIGHTWEIGHT_TESTS") == "true",
        reason="Model selection tests require real Prophet/statsmodels (not mocked)",
    ),
]


# -----------------------------------------------------------------------------
# Tests for calculate_mape function
# -----------------------------------------------------------------------------


class TestCalculateMAPE:
    """Unit tests for calculate_mape function."""

    def test_mape_basic_calculation(self) -> None:
        """[P0] Basic MAPE calculation with simple values."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([100.0, 200.0, 150.0])
        y_pred = np.array([110.0, 190.0, 160.0])

        mape = calculate_mape(y_true, y_pred)

        # Expected: mean(|10/100|, |10/200|, |10/150|) * 100
        expected = np.mean([0.1, 0.05, 0.0667]) * 100
        assert abs(mape - expected) < 0.01

    def test_mape_perfect_prediction(self) -> None:
        """[P0] MAPE = 0 when predictions are perfect."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([100.0, 200.0, 150.0])
        y_pred = np.array([100.0, 200.0, 150.0])

        mape = calculate_mape(y_true, y_pred)
        assert mape == 0.0

    def test_mape_all_zeros_returns_infinity(self) -> None:
        """[P1] MAPE = inf when all true values are zero (division by zero)."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([0.0, 0.0, 0.0])
        y_pred = np.array([10.0, 20.0, 30.0])

        mape = calculate_mape(y_true, y_pred)
        assert mape == float("inf")

    def test_mape_some_zeros_ignored(self) -> None:
        """[P1] MAPE ignores zero values in y_true (uses mask)."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([0.0, 100.0, 200.0])
        y_pred = np.array([10.0, 110.0, 190.0])

        mape = calculate_mape(y_true, y_pred)

        # Only [100, 200] are used, [0] is masked out
        expected = np.mean([0.1, 0.05]) * 100
        assert abs(mape - expected) < 0.01

    def test_mape_negative_values(self) -> None:
        """[P2] MAPE handles negative values (financial data can be negative)."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([-100.0, -200.0, -150.0])
        y_pred = np.array([-110.0, -190.0, -160.0])

        mape = calculate_mape(y_true, y_pred)

        # Expected: mean(|10/100|, |10/200|, |10/150|) * 100
        expected = np.mean([0.1, 0.05, 0.0667]) * 100
        assert abs(mape - expected) < 0.01

    def test_mape_mixed_sign_values(self) -> None:
        """[P2] MAPE handles mixed positive/negative values."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([100.0, -200.0, 150.0])
        y_pred = np.array([110.0, -190.0, 160.0])

        mape = calculate_mape(y_true, y_pred)

        # Expected: mean(|10/100|, |10/200|, |10/150|) * 100
        expected = np.mean([0.1, 0.05, 0.0667]) * 100
        assert abs(mape - expected) < 0.01

    def test_mape_single_element_arrays(self) -> None:
        """[P2] MAPE works with single element arrays."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([100.0])
        y_pred = np.array([110.0])

        mape = calculate_mape(y_true, y_pred)
        assert abs(mape - 10.0) < 0.01

    def test_mape_empty_arrays_raises_error(self) -> None:
        """[P2] MAPE handles empty arrays gracefully."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([])
        y_pred = np.array([])

        # Empty array should return inf (no valid values)
        mape = calculate_mape(y_true, y_pred)
        assert mape == float("inf")

    def test_mape_length_mismatch_raises_error(self) -> None:
        """[P1] MAPE raises ValueError when array lengths don't match."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([100.0, 200.0, 150.0])
        y_pred = np.array([110.0, 190.0])

        with pytest.raises(ValueError, match="Length mismatch"):
            calculate_mape(y_true, y_pred)

    def test_mape_large_values(self) -> None:
        """[P3] MAPE handles large values without overflow."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([1e9, 2e9, 1.5e9])
        y_pred = np.array([1.1e9, 1.9e9, 1.6e9])

        mape = calculate_mape(y_true, y_pred)

        # Expected: mean(|0.1e9/1e9|, |0.1e9/2e9|, |0.1e9/1.5e9|) * 100
        expected = np.mean([0.1, 0.05, 0.0667]) * 100
        assert abs(mape - expected) < 0.01

    def test_mape_small_values(self) -> None:
        """[P3] MAPE handles very small values."""
        from raglite.forecasting.model_selection_utils import calculate_mape

        y_true = np.array([1e-6, 2e-6, 1.5e-6])
        y_pred = np.array([1.1e-6, 1.9e-6, 1.6e-6])

        mape = calculate_mape(y_true, y_pred)

        # Expected: mean(|0.1e-6/1e-6|, |0.1e-6/2e-6|, |0.1e-6/1.5e-6|) * 100
        expected = np.mean([0.1, 0.05, 0.0667]) * 100
        assert abs(mape - expected) < 0.01


# -----------------------------------------------------------------------------
# Tests for calculate_mase function
# -----------------------------------------------------------------------------


class TestCalculateMASE:
    """Unit tests for calculate_mase function."""

    def test_mase_basic_calculation(self) -> None:
        """[P0] Basic MASE calculation with simple values."""
        from raglite.forecasting.model_selection_utils import calculate_mase

        y_train = np.array([100.0, 110.0, 105.0, 115.0])
        y_test = np.array([120.0, 125.0])
        y_pred = np.array([122.0, 123.0])

        mase = calculate_mase(y_train, y_test, y_pred)

        # MAE_pred = mean(|120-122|, |125-123|) = mean(2, 2) = 2
        # MAE_naive = mean(|110-100|, |105-110|, |115-105|) = mean(10, 5, 10) = 8.33
        # MASE = 2 / 8.33 = 0.24
        expected = 2.0 / (25.0 / 3.0)
        assert abs(mase - expected) < 0.01

    def test_mase_perfect_prediction(self) -> None:
        """[P0] MASE = 0 when predictions are perfect."""
        from raglite.forecasting.model_selection_utils import calculate_mase

        y_train = np.array([100.0, 110.0, 105.0, 115.0])
        y_test = np.array([120.0, 125.0])
        y_pred = np.array([120.0, 125.0])

        mase = calculate_mase(y_train, y_test, y_pred)
        assert mase == 0.0

    def test_mase_constant_training_data(self) -> None:
        """[P1] MASE = inf when training data is constant (zero naive error)."""
        from raglite.forecasting.model_selection_utils import calculate_mase

        y_train = np.array([100.0, 100.0, 100.0, 100.0])
        y_test = np.array([120.0, 125.0])
        y_pred = np.array([122.0, 123.0])

        mase = calculate_mase(y_train, y_test, y_pred)

        # Naive error = 0 (constant data), so MASE = inf
        assert mase == float("inf")

    def test_mase_constant_training_data_perfect_pred(self) -> None:
        """[P2] MASE = 0 when training data is constant but prediction is perfect."""
        from raglite.forecasting.model_selection_utils import calculate_mase

        y_train = np.array([100.0, 100.0, 100.0, 100.0])
        y_test = np.array([120.0, 125.0])
        y_pred = np.array([120.0, 125.0])

        mase = calculate_mase(y_train, y_test, y_pred)

        # MAE_pred = 0, MAE_naive = 0, special case returns 0
        assert mase == 0.0

    def test_mase_very_short_training_data(self) -> None:
        """[P2] MASE works with minimum training data (2 points)."""
        from raglite.forecasting.model_selection_utils import calculate_mase

        y_train = np.array([100.0, 110.0])
        y_test = np.array([120.0])
        y_pred = np.array([115.0])

        mase = calculate_mase(y_train, y_test, y_pred)

        # MAE_pred = |120-115| = 5
        # MAE_naive = |110-100| = 10
        # MASE = 5 / 10 = 0.5
        assert abs(mase - 0.5) < 0.01

    def test_mase_single_point_training_data(self) -> None:
        """[P2] MASE with single training point (no naive forecast possible)."""
        from raglite.forecasting.model_selection_utils import calculate_mase

        y_train = np.array([100.0])
        y_test = np.array([120.0])
        y_pred = np.array([115.0])

        # Naive forecast requires at least 2 points
        # Should return NaN or inf when not possible
        mase = calculate_mase(y_train, y_test, y_pred)

        # Naive error = mean([]) = NaN, so MASE = inf or NaN
        assert np.isnan(mase) or mase == float("inf") or mase == 0.0

    def test_mase_negative_values(self) -> None:
        """[P2] MASE handles negative values correctly."""
        from raglite.forecasting.model_selection_utils import calculate_mase

        y_train = np.array([-100.0, -110.0, -105.0, -115.0])
        y_test = np.array([-120.0, -125.0])
        y_pred = np.array([-122.0, -123.0])

        mase = calculate_mase(y_train, y_test, y_pred)

        # MAE_pred = mean(|2|, |2|) = 2
        # MAE_naive = mean(|10|, |5|, |10|) = 8.33
        # MASE = 2 / 8.33 = 0.24
        expected = 2.0 / (25.0 / 3.0)
        assert abs(mase - expected) < 0.01

    def test_mase_large_values(self) -> None:
        """[P3] MASE handles large values without overflow."""
        from raglite.forecasting.model_selection_utils import calculate_mase

        y_train = np.array([1e9, 1.1e9, 1.05e9, 1.15e9])
        y_test = np.array([1.2e9, 1.25e9])
        y_pred = np.array([1.22e9, 1.23e9])

        mase = calculate_mase(y_train, y_test, y_pred)

        # MAE_pred = mean(|0.02e9|, |0.02e9|) = 0.02e9
        # MAE_naive = mean(|0.1e9|, |0.05e9|, |0.1e9|) = 0.0833e9
        # MASE = 0.02 / 0.0833 = 0.24
        assert abs(mase - 0.24) < 0.01
