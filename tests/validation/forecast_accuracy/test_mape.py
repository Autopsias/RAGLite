"""Tests for MAPE calculation (Story 4.10 AC1)."""

import pytest

from tests.validation.forecast_accuracy.validator import ForecastAccuracyValidator


@pytest.fixture
def validator() -> ForecastAccuracyValidator:
    """Create validator instance for tests."""
    return ForecastAccuracyValidator(threshold_pct=15.0)


class TestMAPECalculation:
    """Tests for MAPE calculation (Story 4.10 AC1)."""

    def test_mape_known_values(self, validator: ForecastAccuracyValidator):
        """Test MAPE with known inputs/outputs.

        Story 4.10 Test Idea: actuals=[100,110,120], predictions=[105,115,125] → MAPE~4.5%
        """
        actuals = [100.0, 110.0, 120.0]
        predictions = [105.0, 115.0, 125.0]

        mape = validator.calculate_mape(actuals, predictions)

        # Expected: (5/100 + 5/110 + 5/120) / 3 * 100 ≈ 4.38%
        expected_mape = (5 / 100 + 5 / 110 + 5 / 120) / 3 * 100
        assert abs(mape - expected_mape) < 0.01

    def test_mape_perfect_predictions(self, validator: ForecastAccuracyValidator):
        """Test MAPE is 0 for perfect predictions."""
        actuals = [100.0, 200.0, 300.0]
        predictions = [100.0, 200.0, 300.0]

        mape = validator.calculate_mape(actuals, predictions)

        assert mape == 0.0

    def test_mape_handles_zero_actuals(self, validator: ForecastAccuracyValidator):
        """Test MAPE handles zero values gracefully (SMAPE fallback)."""
        actuals = [0.0, 100.0, 200.0]
        predictions = [10.0, 100.0, 200.0]

        # Should use SMAPE for zero values, MAPE for non-zero
        mape = validator.calculate_mape(actuals, predictions)

        # Non-zero: (0/100 + 0/200) / 2 = 0%
        assert mape == 0.0

    def test_mape_all_zeros_actuals(self, validator: ForecastAccuracyValidator):
        """Test MAPE with all zero actuals uses SMAPE."""
        actuals = [0.0, 0.0, 0.0]
        predictions = [10.0, 20.0, 30.0]

        # Should fall back to SMAPE
        mape = validator.calculate_mape(actuals, predictions)

        # SMAPE: 2 * |0-p| / (0 + |p|) = 2 for all, * 100 = 200%
        assert mape == 200.0

    def test_mape_empty_arrays_raises(self, validator: ForecastAccuracyValidator):
        """Test MAPE raises on empty arrays."""
        with pytest.raises(ValueError, match="empty arrays"):
            validator.calculate_mape([], [])

    def test_mape_mismatched_lengths_raises(self, validator: ForecastAccuracyValidator):
        """Test MAPE raises on mismatched array lengths."""
        with pytest.raises(ValueError, match="same length"):
            validator.calculate_mape([100, 200], [100])

    def test_mape_single_value(self, validator: ForecastAccuracyValidator):
        """Test MAPE with single data point."""
        actuals = [100.0]
        predictions = [110.0]

        mape = validator.calculate_mape(actuals, predictions)

        assert mape == 10.0  # 10% error
