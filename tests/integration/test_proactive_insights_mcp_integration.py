"""Integration tests for Story 4.9: Proactive Insights MCP Tool.

Tests the MCP tool integration with simplified mocking.
Complex unit tests are in tests/unit/test_proactive_insights_mcp.py.

Target: Verify AC1-AC5 through observable behavior.
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
    TimeSeriesData,
)

# Mark all tests as preserve_collection - these are read-only tests
# that don't modify the Qdrant collection (performance optimization)
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestGetFinancialInsightsIntegration:
    """Integration tests for get_financial_insights() MCP tool."""

    @pytest.mark.asyncio
    async def test_empty_data_returns_helpful_message(self):
        """Test MCP tool handles empty data gracefully (AC3)."""
        from raglite.main import get_financial_insights

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

            # AC3: Graceful handling of no data
            assert response.__class__.__name__ == "InsightsQueryResponse"
            assert response.total_insights == 0
            assert "ingest financial documents" in response.formatted_summary.lower()

    @pytest.mark.asyncio
    async def test_request_model_validation(self):
        """Test InsightsQueryRequest validates inputs correctly (AC1)."""
        # Valid structured query
        request = InsightsQueryRequest(
            category="RISK",
            time_period="last_quarter",
            limit=5,
            include_recommendations=True,
        )
        assert request.category == "RISK"
        assert request.limit == 5

        # Valid natural language query
        request = InsightsQueryRequest(query="What risks should I focus on?")
        assert request.query == "What risks should I focus on?"

        # Invalid limit - too small
        with pytest.raises(ValueError):
            InsightsQueryRequest(limit=0)

        # Invalid limit - too large
        with pytest.raises(ValueError):
            InsightsQueryRequest(limit=25)

    @pytest.mark.asyncio
    async def test_response_model_structure(self):
        """Test InsightsQueryResponse has correct structure (AC2/AC4)."""
        from raglite.main import get_financial_insights

        with patch(
            "raglite.forecasting.timeseries_extract.extract_timeseries",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = TimeSeriesData(
                metric_name="revenue",
                points=[],
                source_documents=["test.pdf"],
            )

            request = InsightsQueryRequest()
            response = await get_financial_insights.fn(request)

            # AC2: Response model validation
            assert hasattr(response, "insights")
            assert hasattr(response, "recommendations")
            assert hasattr(response, "total_insights")
            assert hasattr(response, "total_recommendations")
            assert hasattr(response, "formatted_summary")
            assert hasattr(response, "time_period_analyzed")
            assert hasattr(response, "generation_time_ms")
            assert hasattr(response, "source_documents")

            # AC4: Formatted summary is a string
            assert isinstance(response.formatted_summary, str)
            assert len(response.formatted_summary) > 0

    @pytest.mark.asyncio
    async def test_natural_language_parsing_integration(self):
        """Test natural language query parsing works end-to-end (AC1)."""
        from raglite.main import parse_insights_query
        from raglite.shared.models import InsightCategory

        # Test various query patterns
        test_cases = [
            ("What risks should I know about?", InsightCategory.RISK, None),
            (
                "Show me opportunities this quarter",
                InsightCategory.OPPORTUNITY,
                "current_quarter",
            ),
            (
                "Any anomalies from last quarter?",
                InsightCategory.ANOMALY,
                "last_quarter",
            ),
            ("What are the trends year to date?", InsightCategory.TREND, "ytd"),
            ("What should I prioritize?", InsightCategory.STRATEGIC_PRIORITY, None),
        ]

        for query, expected_category, expected_period in test_cases:
            category, time_period = parse_insights_query(query)
            assert category == expected_category, f"Failed for: {query}"
            if expected_period:
                assert time_period == expected_period, f"Failed period for: {query}"

    @pytest.mark.asyncio
    async def test_formatted_summary_generation(self):
        """Test format_insights_for_display() generates correct output (AC4)."""
        from raglite.main import format_insights_for_display

        # Test with insights
        insights = [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Critical revenue decline detected",
                supporting_data={"metric": "revenue"},
                rationale="Q3 revenue dropped significantly",
                sources=["Q3_Report.pdf"],
                recommended_action="Investigate",
                created_at=datetime.now(UTC),
            ),
            Insight(
                category=InsightCategory.OPPORTUNITY,
                priority=3,
                summary="Cost optimization opportunity",
                supporting_data={"metric": "expenses"},
                rationale="Operating costs can be reduced",
                sources=["Q3_Report.pdf"],
                recommended_action="Review costs",
                created_at=datetime.now(UTC),
            ),
        ]

        recommendations = [
            Recommendation(
                category=RecommendationCategory.RISK_MITIGATION,
                impact_score=9,
                title="Address Revenue Decline",
                description="Take action",
                rationale="Revenue is critical",
                supporting_evidence={},
                action_steps=["Review data", "Develop plan"],
                urgency="high",
                sources=[],
                created_at=datetime.now(UTC),
            )
        ]

        result = format_insights_for_display(insights, recommendations)

        # AC4: Verify formatted output
        assert "Executive Summary" in result
        assert "1 critical finding" in result
        assert "1 risk" in result
        assert "1 opportunity" in result
        assert "Key Insights" in result
        assert "Critical" in result  # Priority indicator
        assert "Recommended Actions" in result
        assert "Address Revenue Decline" in result

    @pytest.mark.asyncio
    async def test_observability_fields_populated(self):
        """Test observability fields are correctly populated (AC1)."""
        from raglite.main import get_financial_insights

        with patch(
            "raglite.forecasting.timeseries_extract.extract_timeseries",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = TimeSeriesData(
                metric_name="revenue",
                points=[],
                source_documents=[],
            )

            request = InsightsQueryRequest(
                category="RISK",
                time_period="last_quarter",
            )
            response = await get_financial_insights.fn(request)

            # Observability fields
            assert response.generation_time_ms >= 0
            assert isinstance(response.total_insights, int)
            assert isinstance(response.total_recommendations, int)
            assert response.time_period_analyzed is not None

    @pytest.mark.asyncio
    async def test_default_limit_applied(self):
        """Test default limit of 5 is applied (AC3)."""
        request = InsightsQueryRequest()
        assert request.limit == 5

    @pytest.mark.asyncio
    async def test_include_recommendations_default_true(self):
        """Test include_recommendations defaults to True (AC2)."""
        request = InsightsQueryRequest()
        assert request.include_recommendations is True

    @pytest.mark.asyncio
    async def test_time_period_mapping(self):
        """Test time period mappings are correct (AC1)."""
        from raglite.main import TIME_PERIOD_MAPPINGS

        assert TIME_PERIOD_MAPPINGS["last_quarter"] == "Previous Quarter"
        assert TIME_PERIOD_MAPPINGS["current_quarter"] == "Current Quarter"
        assert TIME_PERIOD_MAPPINGS["last_year"] == "Last 12 Months"
        assert TIME_PERIOD_MAPPINGS["ytd"] == "Year-to-Date"

    @pytest.mark.asyncio
    async def test_supported_categories(self):
        """Test supported categories are correct (AC1)."""
        from raglite.main import SUPPORTED_INSIGHT_CATEGORIES

        expected = {"RISK", "OPPORTUNITY", "ANOMALY", "TREND", "STRATEGIC_PRIORITY"}
        assert SUPPORTED_INSIGHT_CATEGORIES == expected
