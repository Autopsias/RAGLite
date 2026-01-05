"""Unit tests for Story 4.6: Trend Analysis & Pattern Recognition.

Tests the analyze_trends() function, explain_trend() function, and auto_explain parameter.

Refactored: Model tests moved to test_trend_models.py
Refactored: Calculation tests moved to test_trend_calculations.py
Refactored: Correlation tests moved to test_trend_correlation.py
Refactored: Edge case tests moved to test_trend_edge_cases.py
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (  # noqa: E402
    TimeSeriesData,
    TimeSeriesPoint,
    Trend,
    TrendAnalysisResult,
    TrendDirection,
)

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests use scipy which interacts with torch type checking - mocked torch breaks this
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="Trend analysis tests use scipy which breaks with mocked torch",
)


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
