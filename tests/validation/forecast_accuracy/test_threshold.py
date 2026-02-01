"""Tests for configurable threshold."""

from tests.validation.forecast_accuracy.validator import ForecastAccuracyValidator


class TestThresholdConfiguration:
    """Tests for configurable threshold."""

    def test_custom_threshold(self):
        """Test validator with custom threshold."""
        strict_validator = ForecastAccuracyValidator(threshold_pct=10.0)
        assert strict_validator.threshold_pct == 10.0

    def test_default_threshold(self):
        """Test validator with default ±15% threshold."""
        validator = ForecastAccuracyValidator()
        assert validator.threshold_pct == 15.0
