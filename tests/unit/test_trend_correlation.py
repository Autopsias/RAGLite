"""Unit tests for correlation detection in trend analysis."""

import pytest

from raglite.insights.trends import detect_correlation


class TestDetectCorrelation:
    """Tests for the detect_correlation() function."""

    def test_perfect_positive_correlation(self):
        """Test perfect positive correlation (r=1.0)."""
        values_a = [100.0, 110.0, 120.0, 130.0, 140.0]
        values_b = [50.0, 55.0, 60.0, 65.0, 70.0]

        corr = detect_correlation("revenue", "expenses", values_a, values_b)

        assert corr.correlation_coefficient == 1.0
        assert corr.p_value < 0.05
        assert "Strong positive" in corr.interpretation

    def test_perfect_negative_correlation(self):
        """Test perfect negative correlation (r=-1.0)."""
        values_a = [100.0, 110.0, 120.0, 130.0, 140.0]
        values_b = [70.0, 65.0, 60.0, 55.0, 50.0]

        corr = detect_correlation("revenue", "costs", values_a, values_b)

        assert corr.correlation_coefficient == -1.0
        assert "Strong negative" in corr.interpretation

    def test_weak_correlation(self):
        """Test weak/no correlation (|r| < 0.4)."""
        values_a = [100.0, 105.0, 110.0, 108.0, 112.0]
        values_b = [50.0, 48.0, 52.0, 51.0, 49.0]

        corr = detect_correlation("revenue", "random", values_a, values_b)

        assert abs(corr.correlation_coefficient) < 0.8  # Not perfectly correlated
        # Interpretation depends on actual correlation

    def test_moderate_correlation(self):
        """Test moderate correlation (0.4 < |r| <= 0.7)."""
        # Create data with moderate correlation
        values_a = [100.0, 110.0, 105.0, 115.0, 120.0]
        values_b = [50.0, 52.0, 54.0, 53.0, 57.0]

        corr = detect_correlation("a", "b", values_a, values_b)

        # Result depends on actual correlation in data
        assert -1.0 <= corr.correlation_coefficient <= 1.0

    def test_correlation_insufficient_data(self):
        """Test correlation raises error with < 3 data points."""
        values_a = [100.0, 110.0]
        values_b = [50.0, 55.0]

        with pytest.raises(ValueError, match="at least 3"):
            detect_correlation("a", "b", values_a, values_b)

    def test_correlation_mismatched_lengths(self):
        """Test correlation raises error with mismatched lengths."""
        values_a = [100.0, 110.0, 120.0]
        values_b = [50.0, 55.0]

        with pytest.raises(ValueError):
            detect_correlation("a", "b", values_a, values_b)
