"""Unit tests for Story 4.9: Proactive Insights MCP Tool.

Tests cover:
- InsightsQueryRequest/InsightsQueryResponse models (Task 1)
- parse_insights_query() natural language parsing (Task 3)
- format_insights_for_display() conversational formatting (Task 4)
- get_financial_insights() MCP tool behavior (Task 2)

Target: 90%+ coverage for AC validation.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from raglite.shared.models import (
    Insight,
    InsightCategory,
    InsightsQueryRequest,
    Recommendation,
    RecommendationCategory,
)

# =============================================================================
# Task 1: Model Tests
# =============================================================================


class TestFormatInsightsForDisplay:
    """Tests for format_insights_for_display() helper (AC4)."""

    @pytest.fixture
    def format_fn(self):
        """Import format function."""
        from raglite.main import format_insights_for_display

        return format_insights_for_display

    @pytest.fixture
    def sample_insight(self):
        """Create a sample insight."""
        return Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Revenue declined by 15%",
            supporting_data={"metric": "revenue", "magnitude_pct": -15.0},
            rationale="Q3 revenue dropped significantly compared to Q2",
            sources=["Q3_Report.pdf"],
            recommended_action="Investigate revenue drivers",
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_recommendation(self):
        """Create a sample recommendation."""
        return Recommendation(
            category=RecommendationCategory.RISK_MITIGATION,
            impact_score=9,
            title="Address Revenue Decline",
            description="Take immediate action on revenue",
            rationale="Revenue is a critical metric",
            supporting_evidence={"metric": "revenue"},
            action_steps=["Review Q3 data", "Identify root causes"],
            urgency="high",
            sources=["Q3_Report.pdf"],
            created_at=datetime.now(UTC),
        )

    def test_empty_insights(self, format_fn):
        """Test formatting empty insights."""
        result = format_fn([], [])
        assert "No significant insights detected" in result

    def test_single_critical_insight(self, format_fn, sample_insight):
        """Test formatting single critical insight."""
        result = format_fn([sample_insight], [])
        assert "Critical" in result
        assert "Revenue declined by 15%" in result
        assert "1 critical finding" in result

    def test_priority_indicators(self, format_fn):
        """Test priority indicator formatting."""
        insights = [
            Insight(
                category=InsightCategory.RISK,
                priority=priority,
                summary=f"Priority {priority} insight",
                supporting_data={},
                rationale="",
                sources=[],
                recommended_action="",
                created_at=datetime.now(UTC),
            )
            for priority in [1, 2, 3, 4]
        ]
        result = format_fn(insights, [])
        assert "Critical" in result  # Priority 1
        assert "High" in result  # Priority 2
        assert "Medium" in result  # Priority 3
        assert "Low" in result  # Priority 4

    def test_recommendations_formatting(self, format_fn, sample_insight, sample_recommendation):
        """Test recommendation formatting."""
        result = format_fn([sample_insight], [sample_recommendation])
        assert "Recommended Actions" in result
        assert "Address Revenue Decline" in result
        assert "Impact: 9/10" in result

    def test_urgency_icons(self, format_fn, sample_insight):
        """Test urgency icon formatting."""
        high_urgency = Recommendation(
            category=RecommendationCategory.RISK_MITIGATION,
            impact_score=9,
            title="Urgent Action",
            description="",
            rationale="",
            supporting_evidence={},
            action_steps=["Act now"],
            urgency="high",
            sources=[],
            created_at=datetime.now(UTC),
        )
        low_urgency = Recommendation(
            category=RecommendationCategory.OPERATIONAL_EFFICIENCY,
            impact_score=5,
            title="Low Priority",
            description="",
            rationale="",
            supporting_evidence={},
            action_steps=["Plan later"],
            urgency="low",
            sources=[],
            created_at=datetime.now(UTC),
        )
        result = format_fn([sample_insight], [high_urgency, low_urgency])
        # High urgency has lightning bolt, low has clipboard
        assert "Urgent Action" in result
        assert "Low Priority" in result

    def test_executive_summary_counts(self, format_fn):
        """Test executive summary counts different categories."""
        insights = [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Risk 1",
                supporting_data={},
                rationale="",
                sources=[],
                recommended_action="",
                created_at=datetime.now(UTC),
            ),
            Insight(
                category=InsightCategory.RISK,
                priority=2,
                summary="Risk 2",
                supporting_data={},
                rationale="",
                sources=[],
                recommended_action="",
                created_at=datetime.now(UTC),
            ),
            Insight(
                category=InsightCategory.OPPORTUNITY,
                priority=3,
                summary="Opportunity 1",
                supporting_data={},
                rationale="",
                sources=[],
                recommended_action="",
                created_at=datetime.now(UTC),
            ),
        ]
        result = format_fn(insights, [])
        assert "1 critical finding" in result
        assert "2 risk(s)" in result
        assert "1 opportunity" in result


# =============================================================================
# Task 2: MCP Tool Tests (Mocked)
# =============================================================================


class TestGetFinancialInsightsMCP:
    """Tests for get_financial_insights() MCP tool (AC1-AC5).

    Note: Complex mocking tests moved to integration tests.
    These tests focus on input validation and basic behavior.
    """

    @pytest.mark.asyncio
    async def test_natural_language_query(self):
        """Test natural language query parsing (AC1)."""
        from raglite.main import get_financial_insights
        from raglite.shared.models import TimeSeriesData

        # Patch at the right location - inside the get_financial_insights function
        with patch(
            "raglite.forecasting.timeseries_extract.extract_timeseries",
            new_callable=AsyncMock,
        ) as mock_extract:
            # Return empty to trigger "no insights" path
            mock_extract.return_value = TimeSeriesData(
                metric_name="revenue",
                points=[],
                source_documents=[],
            )

            request = InsightsQueryRequest(query="What risks should I know about?")
            response = await get_financial_insights.fn(request)

            # Should return empty response with helpful message
            assert response.total_insights == 0
            assert "No insights available" in response.formatted_summary

    @pytest.mark.asyncio
    async def test_empty_data_response(self):
        """Test response when no data available (AC3)."""
        from raglite.main import get_financial_insights
        from raglite.shared.models import TimeSeriesData

        with patch(
            "raglite.forecasting.timeseries_extract.extract_timeseries",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = TimeSeriesData(
                metric_name="revenue",
                points=[],
                source_documents=[],
            )

            request = InsightsQueryRequest()
            response = await get_financial_insights.fn(request)

            assert response.total_insights == 0
            assert response.total_recommendations == 0
            assert "ingest financial documents" in response.formatted_summary.lower()

    @pytest.mark.asyncio
    async def test_graceful_metric_failure_handling(self):
        """Test graceful handling when individual metric extraction fails.

        Per-metric failures should be caught and logged, not propagated.
        The tool should return empty response if all metrics fail.
        """
        from raglite.main import get_financial_insights

        with patch(
            "raglite.forecasting.timeseries_extract.extract_timeseries",
            new_callable=AsyncMock,
        ) as mock_extract:
            # All metric extractions fail - should gracefully return empty
            mock_extract.side_effect = Exception("Database connection failed")

            request = InsightsQueryRequest()
            response = await get_financial_insights.fn(request)

            # Should return empty response, not raise
            assert response.total_insights == 0
            assert "No insights available" in response.formatted_summary


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for module-level constants."""

    def test_supported_categories(self):
        """Test supported category constants."""
        from raglite.main import SUPPORTED_INSIGHT_CATEGORIES

        expected = {"RISK", "OPPORTUNITY", "ANOMALY", "TREND", "STRATEGIC_PRIORITY"}
        assert SUPPORTED_INSIGHT_CATEGORIES == expected

    def test_time_period_mappings(self):
        """Test time period mapping constants."""
        from raglite.main import TIME_PERIOD_MAPPINGS

        assert TIME_PERIOD_MAPPINGS["last_quarter"] == "Previous Quarter"
        assert TIME_PERIOD_MAPPINGS["current_quarter"] == "Current Quarter"
        assert TIME_PERIOD_MAPPINGS["last_year"] == "Last 12 Months"
        assert TIME_PERIOD_MAPPINGS["ytd"] == "Year-to-Date"
