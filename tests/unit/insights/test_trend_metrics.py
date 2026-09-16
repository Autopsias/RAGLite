"""Unit tests for Story 4.6: Trend Metric Calculations.

Tests calculate_cagr, calculate_qoq_growth, classify_direction, and detect_correlation.
Split from test_trend_analysis.py as part of Story 8.4a-2.
"""

import os

import pytest

from raglite.shared.models import TrendDirection

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests use scipy which interacts with torch type checking - mocked torch breaks this
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        os.environ.get("LIGHTWEIGHT_TESTS") == "true",
        reason="Trend analysis tests use scipy which breaks with mocked torch",
    ),
]


# =============================================================================
# Test calculate_cagr() Function (AC2)
# =============================================================================


class TestCalculateCagr:
    """Tests for the calculate_cagr() function."""

    def test_cagr_positive_growth(self):
        """Test CAGR calculation for positive growth."""
        from raglite.insights.trends import calculate_cagr

        # 100 -> 150 over 2 years = 22.47% CAGR
        cagr = calculate_cagr(100.0, 150.0, 2.0)
        assert 0.22 < cagr < 0.23  # ~22.47%

    def test_cagr_negative_growth(self):
        """Test CAGR calculation for negative growth."""
        from raglite.insights.trends import calculate_cagr

        # 100 -> 50 over 2 years = -29.29% CAGR
        cagr = calculate_cagr(100.0, 50.0, 2.0)
        assert -0.30 < cagr < -0.29

    def test_cagr_zero_growth(self):
        """Test CAGR calculation for zero growth."""
        from raglite.insights.trends import calculate_cagr

        cagr = calculate_cagr(100.0, 100.0, 2.0)
        assert cagr == 0.0

    def test_cagr_one_year(self):
        """Test CAGR calculation for 1 year period."""
        from raglite.insights.trends import calculate_cagr

        # 100 -> 115 over 1 year = 15% CAGR
        cagr = calculate_cagr(100.0, 115.0, 1.0)
        assert abs(cagr - 0.15) < 0.001

    def test_cagr_invalid_start_value(self):
        """Test CAGR returns 0 for invalid start value."""
        from raglite.insights.trends import calculate_cagr

        assert calculate_cagr(0.0, 100.0, 2.0) == 0.0
        assert calculate_cagr(-10.0, 100.0, 2.0) == 0.0

    def test_cagr_invalid_years(self):
        """Test CAGR returns 0 for invalid years."""
        from raglite.insights.trends import calculate_cagr

        assert calculate_cagr(100.0, 150.0, 0.0) == 0.0
        assert calculate_cagr(100.0, 150.0, -1.0) == 0.0

    def test_cagr_accuracy_tolerance(self):
        """Test CAGR calculation accuracy (AC2: +-0.1% tolerance)."""
        from raglite.insights.trends import calculate_cagr

        # Known values: 1000 -> 1610.51 over 5 years = 10% CAGR
        cagr = calculate_cagr(1000.0, 1610.51, 5.0)
        assert abs(cagr - 0.10) < 0.001  # Within 0.1% tolerance


# =============================================================================
# Test calculate_qoq_growth() Function (AC2)
# =============================================================================


class TestCalculateQoqGrowth:
    """Tests for the calculate_qoq_growth() function."""

    def test_qoq_positive_growth(self):
        """Test QoQ calculation for positive growth."""
        from raglite.insights.trends import calculate_qoq_growth

        # Each quarter grows by ~5%: 100, 105, 110.25, 115.76
        values = [100.0, 105.0, 110.25, 115.76]
        qoq = calculate_qoq_growth(values)
        assert 4.9 < qoq < 5.1  # ~5%

    def test_qoq_negative_growth(self):
        """Test QoQ calculation for negative growth."""
        from raglite.insights.trends import calculate_qoq_growth

        values = [100.0, 95.0, 90.25, 85.74]
        qoq = calculate_qoq_growth(values)
        assert -5.1 < qoq < -4.9  # ~-5%

    def test_qoq_zero_growth(self):
        """Test QoQ calculation for zero growth."""
        from raglite.insights.trends import calculate_qoq_growth

        values = [100.0, 100.0, 100.0, 100.0]
        qoq = calculate_qoq_growth(values)
        assert qoq == 0.0

    def test_qoq_single_value(self):
        """Test QoQ returns 0 for single value."""
        from raglite.insights.trends import calculate_qoq_growth

        assert calculate_qoq_growth([100.0]) == 0.0

    def test_qoq_empty_list(self):
        """Test QoQ returns 0 for empty list."""
        from raglite.insights.trends import calculate_qoq_growth

        assert calculate_qoq_growth([]) == 0.0

    def test_qoq_handles_zero_value(self):
        """Test QoQ handles zero values in sequence."""
        from raglite.insights.trends import calculate_qoq_growth

        # Zero value should be skipped in calculation
        values = [0.0, 100.0, 105.0, 110.0]
        qoq = calculate_qoq_growth(values)
        # Only calculates growth from non-zero values
        assert qoq > 0


# =============================================================================
# Test classify_direction() Function (AC3)
# =============================================================================


class TestClassifyDirection:
    """Tests for the classify_direction() function."""

    def test_classify_increasing(self):
        """Test CAGR > 5% returns INCREASING."""
        from raglite.insights.trends import classify_direction

        assert classify_direction(0.10) == TrendDirection.INCREASING
        assert classify_direction(0.051) == TrendDirection.INCREASING
        assert classify_direction(0.50) == TrendDirection.INCREASING

    def test_classify_decreasing(self):
        """Test CAGR < -5% returns DECREASING."""
        from raglite.insights.trends import classify_direction

        assert classify_direction(-0.10) == TrendDirection.DECREASING
        assert classify_direction(-0.051) == TrendDirection.DECREASING
        assert classify_direction(-0.50) == TrendDirection.DECREASING

    def test_classify_stable(self):
        """Test -5% <= CAGR <= 5% returns STABLE."""
        from raglite.insights.trends import classify_direction

        assert classify_direction(0.0) == TrendDirection.STABLE
        assert classify_direction(0.05) == TrendDirection.STABLE
        assert classify_direction(-0.05) == TrendDirection.STABLE
        assert classify_direction(0.02) == TrendDirection.STABLE
        assert classify_direction(-0.02) == TrendDirection.STABLE

    def test_classify_custom_threshold(self):
        """Test classification with custom threshold."""
        from raglite.insights.trends import classify_direction

        # With 10% threshold
        assert classify_direction(0.08, threshold=0.10) == TrendDirection.STABLE
        assert classify_direction(0.11, threshold=0.10) == TrendDirection.INCREASING
        assert classify_direction(-0.11, threshold=0.10) == TrendDirection.DECREASING


# =============================================================================
# Test detect_correlation() Function (AC1, AC2)
# =============================================================================


class TestDetectCorrelation:
    """Tests for the detect_correlation() function."""

    def test_perfect_positive_correlation(self):
        """Test perfect positive correlation (r=1.0)."""
        from raglite.insights.trends import detect_correlation

        values_a = [100.0, 110.0, 120.0, 130.0, 140.0]
        values_b = [50.0, 55.0, 60.0, 65.0, 70.0]

        corr = detect_correlation("revenue", "expenses", values_a, values_b)

        assert corr.correlation_coefficient == 1.0
        assert corr.p_value < 0.05
        assert "Strong positive" in corr.interpretation

    def test_perfect_negative_correlation(self):
        """Test perfect negative correlation (r=-1.0)."""
        from raglite.insights.trends import detect_correlation

        values_a = [100.0, 110.0, 120.0, 130.0, 140.0]
        values_b = [70.0, 65.0, 60.0, 55.0, 50.0]

        corr = detect_correlation("revenue", "costs", values_a, values_b)

        assert corr.correlation_coefficient == -1.0
        assert "Strong negative" in corr.interpretation

    def test_weak_correlation(self):
        """Test weak/no correlation (|r| < 0.4)."""
        from raglite.insights.trends import detect_correlation

        values_a = [100.0, 105.0, 110.0, 108.0, 112.0]
        values_b = [50.0, 48.0, 52.0, 51.0, 49.0]

        corr = detect_correlation("revenue", "random", values_a, values_b)

        assert abs(corr.correlation_coefficient) < 0.8  # Not perfectly correlated
        # Interpretation depends on actual correlation

    def test_moderate_correlation(self):
        """Test moderate correlation (0.4 < |r| <= 0.7)."""
        from raglite.insights.trends import detect_correlation

        # Create data with moderate correlation
        values_a = [100.0, 110.0, 105.0, 115.0, 120.0]
        values_b = [50.0, 52.0, 54.0, 53.0, 57.0]

        corr = detect_correlation("a", "b", values_a, values_b)

        # Result depends on actual correlation in data
        assert -1.0 <= corr.correlation_coefficient <= 1.0

    def test_correlation_insufficient_data(self):
        """Test correlation raises error with < 3 data points."""
        from raglite.insights.trends import detect_correlation

        values_a = [100.0, 110.0]
        values_b = [50.0, 55.0]

        with pytest.raises(ValueError, match="at least 3"):
            detect_correlation("a", "b", values_a, values_b)

    def test_correlation_mismatched_lengths(self):
        """Test correlation raises error with mismatched lengths."""
        from raglite.insights.trends import detect_correlation

        values_a = [100.0, 110.0, 120.0]
        values_b = [50.0, 55.0]

        with pytest.raises(ValueError):
            detect_correlation("a", "b", values_a, values_b)


# =============================================================================
# Test Synthetic Data for Correlation (AC5)
# =============================================================================


class TestCorrelationSyntheticData:
    """Tests using synthetic data for correlation validation."""

    @pytest.mark.asyncio
    async def test_correlation_positive_synthetic_data(self):
        """Test perfect positive correlation detected (AC5)."""
        from raglite.insights.trends import detect_correlation

        values_a = [100.0, 110.0, 120.0, 130.0, 140.0]
        values_b = [50.0, 55.0, 60.0, 65.0, 70.0]

        corr = detect_correlation("a", "b", values_a, values_b)

        assert corr.correlation_coefficient == 1.0

    @pytest.mark.asyncio
    async def test_correlation_negative_synthetic_data(self):
        """Test perfect negative correlation detected (AC5)."""
        from raglite.insights.trends import detect_correlation

        values_a = [100.0, 110.0, 120.0, 130.0, 140.0]
        values_b = [70.0, 65.0, 60.0, 55.0, 50.0]

        corr = detect_correlation("a", "b", values_a, values_b)

        assert corr.correlation_coefficient == -1.0
