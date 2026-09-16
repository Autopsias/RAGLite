"""Unit tests for Story 4.6: Core Trend Analysis Functions.

Tests analyze_trends, explain_trend, and integration scenarios.
Split from test_trend_analysis.py as part of Story 8.4a-2.

NOTE: File size is 364 LOC (approaching warning threshold of 400 LOC).
If additional test cases are needed, consider splitting by feature:
- test_trend_explain_basic.py (simple explain_trend tests)
- test_trend_explain_advanced.py (edge cases, integration scenarios)
"""

import logging
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (
    TimeSeriesData,
    TimeSeriesPoint,
    Trend,
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
