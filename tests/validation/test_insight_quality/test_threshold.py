"""Tests for configurable threshold."""

from .validator import InsightQualityValidator


class TestThresholdConfiguration:
    """Tests for configurable threshold."""

    def test_custom_threshold(self):
        """Test validator with custom threshold."""
        strict_validator = InsightQualityValidator(threshold_pct=90.0)
        assert strict_validator.threshold_pct == 90.0

    def test_default_threshold(self):
        """Test validator with default 75% threshold."""
        validator = InsightQualityValidator()
        assert validator.threshold_pct == 75.0
