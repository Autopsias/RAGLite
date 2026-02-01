"""Unit tests for Story 4.6: Trend Model and Enum Definitions.

Tests TrendDirection enum, Trend, CorrelationResult, and TrendAnalysisResult models.
Split from test_trend_analysis.py as part of Story 8.4a-2.
"""

import os

import pytest

from raglite.shared.models import (
    CorrelationResult,
    Trend,
    TrendAnalysisResult,
    TrendDirection,
)

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
# Test TrendDirection Enum (AC3)
# =============================================================================


class TestTrendDirection:
    """Tests for the TrendDirection enum."""

    def test_direction_values(self):
        """Test that TrendDirection has INCREASING, DECREASING, STABLE, CYCLICAL values."""
        assert TrendDirection.INCREASING.value == "increasing"
        assert TrendDirection.DECREASING.value == "decreasing"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.CYCLICAL.value == "cyclical"

    def test_direction_is_string_enum(self):
        """Test that TrendDirection is a string enum."""
        assert isinstance(TrendDirection.INCREASING, str)
        assert TrendDirection.INCREASING == "increasing"

    def test_all_direction_values(self):
        """Test iterating over all direction values."""
        directions = list(TrendDirection)
        assert len(directions) == 4
        assert TrendDirection.INCREASING in directions
        assert TrendDirection.DECREASING in directions
        assert TrendDirection.STABLE in directions
        assert TrendDirection.CYCLICAL in directions


# =============================================================================
# Test Trend Model (AC1, AC3)
# =============================================================================


class TestTrendModel:
    """Tests for the Trend model."""

    def test_trend_with_all_fields(self):
        """Test creating Trend with all fields populated."""
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=15.2,
            confidence=0.85,
            start_date="2024-Q1",
            end_date="2024-Q4",
            description="Strong growth driven by new product launches",
            cagr=0.152,
            qoq_growth=3.8,
        )

        assert trend.metric == "revenue"
        assert trend.direction == TrendDirection.INCREASING
        assert trend.magnitude == 15.2
        assert trend.confidence == 0.85
        assert trend.start_date == "2024-Q1"
        assert trend.end_date == "2024-Q4"
        assert "product launches" in trend.description
        assert trend.cagr == 0.152
        assert trend.qoq_growth == 3.8

    def test_trend_default_values(self):
        """Test Trend default values for optional fields."""
        trend = Trend(
            metric="expenses",
            direction=TrendDirection.STABLE,
            magnitude=2.5,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        assert trend.confidence == 0.0
        assert trend.description == ""
        assert trend.cagr == 0.0
        assert trend.qoq_growth == 0.0

    def test_trend_serialization(self):
        """Test that Trend can be serialized to dict."""
        trend = Trend(
            metric="cash_flow",
            direction=TrendDirection.DECREASING,
            magnitude=8.5,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        data = trend.model_dump()
        assert data["metric"] == "cash_flow"
        assert data["direction"] == "decreasing"
        assert data["magnitude"] == 8.5
        assert data["start_date"] == "2024-Q1"

    def test_trend_confidence_bounds(self):
        """Test that confidence is bounded 0-1."""
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=10.0,
            confidence=0.95,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )
        assert 0.0 <= trend.confidence <= 1.0

    def test_trend_required_fields(self):
        """Test that required fields raise error if missing."""
        with pytest.raises(ValueError):
            Trend(
                metric="revenue",
                # Missing required fields
            )


# =============================================================================
# Test CorrelationResult Model (AC1)
# =============================================================================


class TestCorrelationResultModel:
    """Tests for the CorrelationResult model."""

    def test_correlation_with_all_fields(self):
        """Test creating CorrelationResult with all fields."""
        corr = CorrelationResult(
            metric_a="revenue",
            metric_b="expenses",
            correlation_coefficient=0.85,
            p_value=0.002,
            interpretation="Strong positive correlation",
        )

        assert corr.metric_a == "revenue"
        assert corr.metric_b == "expenses"
        assert corr.correlation_coefficient == 0.85
        assert corr.p_value == 0.002
        assert "Strong positive" in corr.interpretation

    def test_correlation_coefficient_bounds(self):
        """Test that correlation coefficient is bounded -1 to 1."""
        corr = CorrelationResult(
            metric_a="a",
            metric_b="b",
            correlation_coefficient=-0.95,
            p_value=0.01,
        )
        assert -1.0 <= corr.correlation_coefficient <= 1.0

    def test_correlation_serialization(self):
        """Test that CorrelationResult can be serialized."""
        corr = CorrelationResult(
            metric_a="revenue",
            metric_b="marketing_spend",
            correlation_coefficient=0.72,
            p_value=0.008,
            interpretation="Strong positive correlation",
        )

        data = corr.model_dump()
        assert data["metric_a"] == "revenue"
        assert data["metric_b"] == "marketing_spend"
        assert data["correlation_coefficient"] == 0.72


# =============================================================================
# Test TrendAnalysisResult Model (AC1)
# =============================================================================


class TestTrendAnalysisResultModel:
    """Tests for the TrendAnalysisResult model."""

    def test_result_with_all_fields(self):
        """Test creating TrendAnalysisResult with all fields."""
        trends = [
            Trend(
                metric="revenue",
                direction=TrendDirection.INCREASING,
                magnitude=15.0,
                start_date="Q1",
                end_date="Q4",
            ),
        ]
        correlations = [
            CorrelationResult(
                metric_a="revenue",
                metric_b="expenses",
                correlation_coefficient=0.8,
                p_value=0.01,
            ),
        ]

        result = TrendAnalysisResult(
            trends=trends,
            correlations=correlations,
            metrics_analyzed=2,
            analysis_method="Statistical analysis (CAGR, QoQ, Pearson correlation)",
        )

        assert len(result.trends) == 1
        assert len(result.correlations) == 1
        assert result.metrics_analyzed == 2
        assert "CAGR" in result.analysis_method

    def test_result_default_values(self):
        """Test TrendAnalysisResult default values."""
        result = TrendAnalysisResult(metrics_analyzed=3)

        assert result.trends == []
        assert result.correlations == []
        assert "Statistical analysis" in result.analysis_method
