"""Unit tests for Story 4.9: Proactive Insights MCP Tool.

Tests cover:
- InsightsQueryRequest/InsightsQueryResponse models (Task 1)
- parse_insights_query() natural language parsing (Task 3)
- format_insights_for_display() conversational formatting (Task 4)
- get_financial_insights() MCP tool behavior (Task 2)

Target: 90%+ coverage for AC validation.
"""

from datetime import UTC, datetime

import pytest

from raglite.shared.models import (
    Insight,
    InsightCategory,
    InsightsQueryRequest,
    InsightsQueryResponse,
    Recommendation,
    RecommendationCategory,
)

# =============================================================================
# Task 1: Model Tests
# =============================================================================


class TestInsightsQueryRequestModel:
    """Tests for InsightsQueryRequest model (AC1)."""

    def test_default_values(self):
        """Test default parameter values."""
        request = InsightsQueryRequest()
        assert request.category is None
        assert request.time_period is None
        assert request.limit == 5
        assert request.include_recommendations is True
        assert request.query is None

    def test_structured_query(self):
        """Test structured query parameters."""
        request = InsightsQueryRequest(
            category="RISK",
            time_period="last_quarter",
            limit=10,
            include_recommendations=False,
        )
        assert request.category == "RISK"
        assert request.time_period == "last_quarter"
        assert request.limit == 10
        assert request.include_recommendations is False

    def test_natural_language_query(self):
        """Test natural language query parameter."""
        request = InsightsQueryRequest(query="What risks should I know about this quarter?")
        assert request.query == "What risks should I know about this quarter?"
        assert request.category is None  # Parsed at runtime

    def test_limit_validation_min(self):
        """Test limit minimum validation."""
        with pytest.raises(ValueError):
            InsightsQueryRequest(limit=0)

    def test_limit_validation_max(self):
        """Test limit maximum validation."""
        with pytest.raises(ValueError):
            InsightsQueryRequest(limit=21)

    def test_valid_categories(self):
        """Test valid category values are accepted."""
        for category in [
            "RISK",
            "OPPORTUNITY",
            "ANOMALY",
            "TREND",
            "STRATEGIC_PRIORITY",
        ]:
            request = InsightsQueryRequest(category=category)
            assert request.category == category

    def test_valid_time_periods(self):
        """Test valid time period values are accepted."""
        for period in ["last_quarter", "current_quarter", "last_year", "ytd"]:
            request = InsightsQueryRequest(time_period=period)
            assert request.time_period == period


class TestInsightsQueryResponseModel:
    """Tests for InsightsQueryResponse model (AC2/AC4)."""

    def test_empty_response(self):
        """Test response with no insights."""
        response = InsightsQueryResponse(
            insights=[],
            recommendations=[],
            total_insights=0,
            total_recommendations=0,
            formatted_summary="No insights available.",
            time_period_analyzed="All available data",
            generation_time_ms=100.0,
            source_documents=[],
        )
        assert len(response.insights) == 0
        assert len(response.recommendations) == 0
        assert response.total_insights == 0

    def test_response_with_insights(self):
        """Test response with insights."""
        insight = Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Critical risk detected",
            supporting_data={"metric": "revenue"},
            rationale="Significant deviation",
            sources=["Q3_Report.pdf"],
            recommended_action="Investigate immediately",
            created_at=datetime.now(UTC),
        )
        response = InsightsQueryResponse(
            insights=[insight],
            recommendations=[],
            total_insights=1,
            total_recommendations=0,
        )
        assert len(response.insights) == 1
        assert response.insights[0].category == InsightCategory.RISK

    def test_response_with_recommendations(self):
        """Test response with recommendations."""
        recommendation = Recommendation(
            category=RecommendationCategory.RISK_MITIGATION,
            impact_score=9,
            title="Mitigate revenue risk",
            description="Take action to address revenue decline",
            rationale="Revenue is declining",
            supporting_evidence={"metric": "revenue"},
            action_steps=["Review revenue drivers", "Adjust strategy"],
            urgency="high",
            sources=["Q3_Report.pdf"],
            created_at=datetime.now(UTC),
        )
        response = InsightsQueryResponse(
            insights=[],
            recommendations=[recommendation],
            total_insights=0,
            total_recommendations=1,
        )
        assert len(response.recommendations) == 1
        assert response.recommendations[0].impact_score == 9


# =============================================================================
# Task 3: Natural Language Parsing Tests
# =============================================================================


class TestParseInsightsQuery:
    """Tests for parse_insights_query() helper (AC1)."""

    @pytest.fixture
    def parse_fn(self):
        """Import parse function."""
        from raglite.main import parse_insights_query

        return parse_insights_query

    # Category parsing tests
    def test_parse_risk_category(self, parse_fn):
        """Test parsing risk-related queries."""
        queries = [
            "What risks should I know about?",
            "Show me any risk alerts",
            "Are there any dangers in the financials?",
            "What threats do we face?",
            "Any warning signs?",
        ]
        for query in queries:
            category, _ = parse_fn(query)
            assert category == InsightCategory.RISK, f"Failed for: {query}"

    def test_parse_opportunity_category(self, parse_fn):
        """Test parsing opportunity-related queries."""
        queries = [
            "What opportunities exist?",
            "Show me growth potential",
            "Any upside potential?",
        ]
        for query in queries:
            category, _ = parse_fn(query)
            assert category == InsightCategory.OPPORTUNITY, f"Failed for: {query}"

    def test_parse_anomaly_category(self, parse_fn):
        """Test parsing anomaly-related queries."""
        queries = [
            "What anomalies were detected?",
            "Show me outliers",
            "Any unusual patterns?",
            "What's unexpected?",
        ]
        for query in queries:
            category, _ = parse_fn(query)
            assert category == InsightCategory.ANOMALY, f"Failed for: {query}"

    def test_parse_trend_category(self, parse_fn):
        """Test parsing trend-related queries."""
        queries = [
            "What trends do you see?",
            "Show me trending metrics",
            "What patterns are emerging?",
        ]
        for query in queries:
            category, _ = parse_fn(query)
            assert category == InsightCategory.TREND, f"Failed for: {query}"

    def test_parse_strategic_priority_category(self, parse_fn):
        """Test parsing strategic priority queries."""
        queries = [
            "What should I prioritize?",
            "Show me strategic priorities",
            "What's most important?",
            "What should I focus on?",
        ]
        for query in queries:
            category, _ = parse_fn(query)
            assert category == InsightCategory.STRATEGIC_PRIORITY, f"Failed for: {query}"

    def test_parse_no_category(self, parse_fn):
        """Test queries without clear category."""
        category, _ = parse_fn("Show me everything")
        assert category is None

    # Time period parsing tests
    def test_parse_last_quarter(self, parse_fn):
        """Test parsing last quarter time period."""
        queries = [
            "What happened last quarter?",
            "Show me previous quarter insights",
        ]
        for query in queries:
            _, time_period = parse_fn(query)
            assert time_period == "last_quarter", f"Failed for: {query}"

    def test_parse_current_quarter(self, parse_fn):
        """Test parsing current quarter time period."""
        queries = [
            "What's happening this quarter?",
            "Show me current quarter data",
        ]
        for query in queries:
            _, time_period = parse_fn(query)
            assert time_period == "current_quarter", f"Failed for: {query}"

    def test_parse_last_year(self, parse_fn):
        """Test parsing last year time period."""
        queries = [
            "What happened last year?",
            "Show me past 12 months",
        ]
        for query in queries:
            _, time_period = parse_fn(query)
            assert time_period == "last_year", f"Failed for: {query}"

    def test_parse_ytd(self, parse_fn):
        """Test parsing year-to-date time period."""
        queries = [
            "What's the YTD performance?",
            "Show me year to date insights",
        ]
        for query in queries:
            _, time_period = parse_fn(query)
            assert time_period == "ytd", f"Failed for: {query}"

    def test_parse_no_time_period(self, parse_fn):
        """Test queries without time period."""
        _, time_period = parse_fn("What risks exist?")
        assert time_period is None

    # Combined parsing tests
    def test_parse_category_and_time_period(self, parse_fn):
        """Test parsing both category and time period."""
        category, time_period = parse_fn("What risks were there last quarter?")
        assert category == InsightCategory.RISK
        assert time_period == "last_quarter"


# =============================================================================
# Task 4: Conversational Formatting Tests
# =============================================================================
