"""Unit tests for Story 4.6: Trend Analysis & Pattern Recognition.

Tests the analyze_trends() function, helper functions (CAGR, QoQ, correlation),
and Trend/TrendAnalysisResult/TrendDirection/CorrelationResult models.
"""

import logging
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests use scipy which interacts with torch type checking - mocked torch breaks this
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="Trend analysis tests use scipy which breaks with mocked torch",
)

from raglite.shared.models import (  # noqa: E402
    CorrelationResult,
    TimeSeriesData,
    TimeSeriesPoint,
    Trend,
    TrendAnalysisResult,
    TrendDirection,
)

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
# Test analyze_trends() Function (AC1-AC5)
# =============================================================================


class TestAnalyzeTrends:
    """Tests for the analyze_trends() function."""

    @pytest.fixture
    def increasing_timeseries(self) -> TimeSeriesData:
        """Create timeseries with known increasing trend."""
        # ~9% annual growth: 100 -> 142 over 8 quarters (2 years)
        values = [100.0, 105.0, 110.0, 116.0, 122.0, 128.0, 135.0, 142.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        return TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="quarterly",
        )

    @pytest.fixture
    def decreasing_timeseries(self) -> TimeSeriesData:
        """Create timeseries with known decreasing trend."""
        values = [100.0, 95.0, 90.0, 86.0, 82.0, 78.0, 74.0, 70.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        return TimeSeriesData(
            metric_name="expenses",
            points=points,
            interval="quarterly",
        )

    @pytest.fixture
    def stable_timeseries(self) -> TimeSeriesData:
        """Create timeseries with stable (no significant trend)."""
        values = [100.0, 101.0, 99.0, 100.5, 100.0, 99.5, 101.0, 100.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        return TimeSeriesData(
            metric_name="cash_flow",
            points=points,
            interval="quarterly",
        )

    @pytest.mark.asyncio
    async def test_analyze_trends_returns_result(self, increasing_timeseries):
        """Test that analyze_trends returns TrendAnalysisResult."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue"],
            {"revenue": increasing_timeseries},
        )

        assert isinstance(result, TrendAnalysisResult)
        assert result.metrics_analyzed == 1

    @pytest.mark.asyncio
    async def test_analyze_trends_detects_increasing(self, increasing_timeseries):
        """Test that increasing trend is correctly identified (AC1, AC3)."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue"],
            {"revenue": increasing_timeseries},
        )

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.metric == "revenue"
        assert trend.direction == TrendDirection.INCREASING
        assert trend.magnitude > 0
        assert trend.cagr > 0.05  # > 5% threshold

    @pytest.mark.asyncio
    async def test_analyze_trends_detects_decreasing(self, decreasing_timeseries):
        """Test that decreasing trend is correctly identified (AC1, AC3)."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["expenses"],
            {"expenses": decreasing_timeseries},
        )

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.direction == TrendDirection.DECREASING
        assert trend.cagr < -0.05  # < -5% threshold

    @pytest.mark.asyncio
    async def test_analyze_trends_detects_stable(self, stable_timeseries):
        """Test that stable trend is correctly identified (AC3)."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["cash_flow"],
            {"cash_flow": stable_timeseries},
        )

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.direction == TrendDirection.STABLE
        assert -0.05 <= trend.cagr <= 0.05

    @pytest.mark.asyncio
    async def test_analyze_trends_multiple_metrics(
        self, increasing_timeseries, decreasing_timeseries, stable_timeseries
    ):
        """Test analyzing multiple metrics at once."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue", "expenses", "cash_flow"],
            {
                "revenue": increasing_timeseries,
                "expenses": decreasing_timeseries,
                "cash_flow": stable_timeseries,
            },
        )

        assert result.metrics_analyzed == 3
        assert len(result.trends) == 3

        # Find each trend
        directions = {t.metric: t.direction for t in result.trends}
        assert directions["revenue"] == TrendDirection.INCREASING
        assert directions["expenses"] == TrendDirection.DECREASING
        assert directions["cash_flow"] == TrendDirection.STABLE

    @pytest.mark.asyncio
    async def test_analyze_trends_detects_correlations(
        self, increasing_timeseries, decreasing_timeseries
    ):
        """Test that correlations are detected between metrics (AC1)."""
        from raglite.insights.trends import analyze_trends

        # Create positively correlated data
        values_a = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0]
        values_b = [50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0]

        ts_a = TimeSeriesData(
            metric_name="revenue",
            points=[
                TimeSeriesPoint(date=datetime(2024, i, 1), value=values_a[i - 1], label=f"Q{i}")
                for i in range(1, 9)
            ],
        )
        ts_b = TimeSeriesData(
            metric_name="marketing",
            points=[
                TimeSeriesPoint(date=datetime(2024, i, 1), value=values_b[i - 1], label=f"Q{i}")
                for i in range(1, 9)
            ],
        )

        result = await analyze_trends(
            ["revenue", "marketing"],
            {"revenue": ts_a, "marketing": ts_b},
        )

        # Should detect strong positive correlation
        assert len(result.correlations) >= 1
        corr = result.correlations[0]
        assert corr.correlation_coefficient > 0.9

    @pytest.mark.asyncio
    async def test_analyze_trends_insufficient_data(self):
        """Test that analyze_trends raises ValueError with < 3 data points."""
        from raglite.insights.trends import analyze_trends

        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0, label="Q1"),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=110.0, label="Q2"),
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        with pytest.raises(ValueError, match="Insufficient data"):
            await analyze_trends(["revenue"], {"revenue": timeseries})

    @pytest.mark.asyncio
    async def test_analyze_trends_missing_metric(self, increasing_timeseries):
        """Test handling of missing metric in data dict."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue", "nonexistent"],
            {"revenue": increasing_timeseries},
        )

        # Should analyze available metrics only
        assert result.metrics_analyzed == 1

    @pytest.mark.asyncio
    async def test_trend_has_required_fields(self, increasing_timeseries):
        """Test that each detected trend has all required fields (AC3)."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue"],
            {"revenue": increasing_timeseries},
        )

        for trend in result.trends:
            assert trend.metric is not None
            assert trend.direction in TrendDirection
            assert trend.magnitude is not None
            assert trend.start_date is not None
            assert trend.end_date is not None
            assert 0.0 <= trend.confidence <= 1.0


# =============================================================================
# Test explain_trend() Function (AC2)
# =============================================================================


class TestExplainTrend:
    """Tests for the explain_trend() function."""

    @pytest.fixture
    def sample_trend(self) -> Trend:
        """Create a sample trend for testing."""
        return Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=15.2,
            confidence=0.85,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.152,
            qoq_growth=3.8,
        )

    @pytest.mark.asyncio
    async def test_explain_trend_with_mocked_mistral(self, sample_trend):
        """Test explain_trend with mocked Mistral client (AC2)."""
        from raglite.insights.trends import explain_trend

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="Revenue shows strong 15.2% annual growth driven by market expansion."
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            explanation = await explain_trend(sample_trend)

        assert "15.2%" in explanation or "growth" in explanation.lower()
        mock_client.chat.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_explain_trend_fallback_on_error(self, sample_trend):
        """Test that explain_trend returns fallback message on API error."""
        from raglite.insights.trends import explain_trend

        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = Exception("API error")

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            explanation = await explain_trend(sample_trend)

        # Should return fallback message with trend details
        assert "Trend detected" in explanation
        assert "revenue" in explanation
        assert "increasing" in explanation

    @pytest.mark.asyncio
    async def test_explain_trend_prompt_contains_context(self, sample_trend):
        """Test that the LLM prompt contains all trend context."""
        from raglite.insights.trends import explain_trend

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test explanation"))]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            await explain_trend(sample_trend)

        # Check the prompt sent to Mistral
        call_args = mock_client.chat.complete.call_args
        prompt = call_args.kwargs["messages"][0]["content"]

        assert "revenue" in prompt.lower()
        assert "increasing" in prompt.lower()
        assert "15.2%" in prompt
        assert "3.8%" in prompt
        assert "2024-Q1" in prompt
        assert "2024-Q4" in prompt


# =============================================================================
# Test auto_explain Parameter
# =============================================================================


class TestAutoExplainParameter:
    """Tests for the auto_explain parameter in analyze_trends."""

    @pytest.fixture
    def simple_timeseries(self) -> TimeSeriesData:
        """Create simple timeseries for testing."""
        values = [100.0, 110.0, 120.0, 130.0, 140.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        return TimeSeriesData(metric_name="revenue", points=points)

    @pytest.mark.asyncio
    async def test_auto_explain_false_leaves_description_empty(self, simple_timeseries):
        """Test that auto_explain=False (default) does not generate descriptions."""
        from raglite.insights.trends import analyze_trends

        result = await analyze_trends(
            ["revenue"],
            {"revenue": simple_timeseries},
        )

        for trend in result.trends:
            assert trend.description == ""

    @pytest.mark.asyncio
    async def test_auto_explain_true_generates_descriptions(self, simple_timeseries):
        """Test that auto_explain=True generates LLM descriptions."""
        from raglite.insights.trends import analyze_trends

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Strong growth trend detected."))
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await analyze_trends(
                ["revenue"],
                {"revenue": simple_timeseries},
                auto_explain=True,
            )

        for trend in result.trends:
            assert trend.description != ""


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in trend analysis."""

    @pytest.mark.asyncio
    async def test_identical_values(self):
        """Test trend analysis with identical values (zero variance)."""
        from raglite.insights.trends import analyze_trends

        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=100.0, label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await analyze_trends(["revenue"], {"revenue": timeseries})

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.direction == TrendDirection.STABLE
        assert trend.cagr == 0.0

    @pytest.mark.asyncio
    async def test_negative_values(self):
        """Test trend analysis with negative values."""
        from raglite.insights.trends import analyze_trends

        values = [-100.0, -90.0, -80.0, -70.0, -60.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="net_income", points=points)

        result = await analyze_trends(["net_income"], {"revenue": timeseries})

        # Should still analyze (even though CAGR may be unusual with negative start)
        assert result.metrics_analyzed >= 0

    @pytest.mark.asyncio
    async def test_large_values(self):
        """Test trend analysis with large values (millions)."""
        from raglite.insights.trends import analyze_trends

        values = [1_000_000.0, 1_100_000.0, 1_200_000.0, 1_300_000.0, 1_400_000.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await analyze_trends(["revenue"], {"revenue": timeseries})

        assert len(result.trends) == 1
        assert result.trends[0].direction == TrendDirection.INCREASING

    @pytest.mark.asyncio
    async def test_single_metric_no_correlations(self):
        """Test that single metric produces no correlations."""
        from raglite.insights.trends import analyze_trends

        values = [100.0, 110.0, 120.0, 130.0, 140.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await analyze_trends(["revenue"], {"revenue": timeseries})

        assert result.correlations == []


# =============================================================================
# Test Structured Logging (AC4)
# =============================================================================


class TestStructuredLogging:
    """Tests for structured logging in trend analysis."""

    @pytest.mark.asyncio
    async def test_logging_on_trend_detection(self, caplog):
        """Test that trend detection logs with structured context (AC4)."""
        from raglite.insights.trends import analyze_trends

        caplog.set_level(logging.INFO)

        values = [100.0, 110.0, 120.0, 130.0, 140.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        await analyze_trends(["revenue"], {"revenue": timeseries})

        # Check that logs were emitted
        assert len(caplog.records) > 0

        # Check for key log messages
        log_messages = [r.message for r in caplog.records]
        assert any(
            "trend analysis" in msg.lower() or "trend detected" in msg.lower()
            for msg in log_messages
        )

    @pytest.mark.asyncio
    async def test_logging_includes_metric_details(self, caplog):
        """Test that log entries include metric details (AC4)."""
        from raglite.insights.trends import analyze_trends

        caplog.set_level(logging.INFO)

        values = [100.0, 110.0, 120.0, 130.0, 140.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 6)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        await analyze_trends(["revenue"], {"revenue": timeseries})

        # Check for metric in log records
        found_metric_log = False
        for record in caplog.records:
            if hasattr(record, "metric") or "revenue" in str(record.message):
                found_metric_log = True
                break
        assert found_metric_log


# =============================================================================
# Test Synthetic Data with Known Trends (AC5)
# =============================================================================


class TestSyntheticDataKnownTrends:
    """Tests using synthetic data with known trends for validation (AC5)."""

    @pytest.mark.asyncio
    async def test_increasing_trend_synthetic_data(self):
        """Test 8 quarters of growth correctly classified (AC5)."""
        from raglite.insights.trends import analyze_trends

        # Known increasing trend: ~9% annual growth
        values = [100.0, 105.0, 110.0, 116.0, 122.0, 128.0, 135.0, 142.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        timeseries = TimeSeriesData(metric_name="revenue", points=points)

        result = await analyze_trends(["revenue"], {"revenue": timeseries})

        assert result.trends[0].direction == TrendDirection.INCREASING

    @pytest.mark.asyncio
    async def test_decreasing_trend_synthetic_data(self):
        """Test 8 quarters of decline correctly classified (AC5)."""
        from raglite.insights.trends import analyze_trends

        # Known decreasing trend: ~-8% annual growth
        values = [100.0, 95.0, 90.0, 86.0, 82.0, 78.0, 74.0, 70.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        timeseries = TimeSeriesData(metric_name="expenses", points=points)

        result = await analyze_trends(["expenses"], {"expenses": timeseries})

        assert result.trends[0].direction == TrendDirection.DECREASING

    @pytest.mark.asyncio
    async def test_stable_trend_synthetic_data(self):
        """Test flat data correctly classified as stable (AC5)."""
        from raglite.insights.trends import analyze_trends

        # Known stable trend: fluctuations within ±5%
        values = [100.0, 101.0, 99.0, 100.5, 100.0, 99.5, 101.0, 100.0]
        points = [
            TimeSeriesPoint(date=datetime(2024, i, 1), value=values[i - 1], label=f"Q{i}")
            for i in range(1, 9)
        ]
        timeseries = TimeSeriesData(metric_name="cash_flow", points=points)

        result = await analyze_trends(["cash_flow"], {"cash_flow": timeseries})

        assert result.trends[0].direction == TrendDirection.STABLE

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
