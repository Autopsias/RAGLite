"""Unit tests for Story 4.7: Proactive Insight Generation.

Tests the generate_insights() function, helper functions (categorize_insight,
calculate_insight_priority, filter_insights), and Insight/InsightCategory/
InsightGenerationResult models.
"""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    ForecastPoint,
    ForecastResult,
    Insight,
    InsightCategory,
    InsightGenerationResult,
    Trend,
    TrendDirection,
)

# =============================================================================
# Test InsightCategory Enum (AC2)
# =============================================================================


class TestInsightCategory:
    """Tests for the InsightCategory enum."""

    def test_category_values(self):
        """Test that InsightCategory has all 5 required values (AC2)."""
        assert InsightCategory.RISK.value == "risk"
        assert InsightCategory.OPPORTUNITY.value == "opportunity"
        assert InsightCategory.ANOMALY.value == "anomaly"
        assert InsightCategory.TREND.value == "trend"
        assert InsightCategory.STRATEGIC_PRIORITY.value == "strategic_priority"

    def test_category_is_string_enum(self):
        """Test that InsightCategory is a string enum."""
        assert isinstance(InsightCategory.RISK, str)
        assert InsightCategory.RISK == "risk"

    def test_all_category_values(self):
        """Test iterating over all category values."""
        categories = list(InsightCategory)
        assert len(categories) == 5
        assert InsightCategory.RISK in categories
        assert InsightCategory.OPPORTUNITY in categories
        assert InsightCategory.ANOMALY in categories
        assert InsightCategory.TREND in categories
        assert InsightCategory.STRATEGIC_PRIORITY in categories


# =============================================================================
# Test Insight Model (AC2, AC3, AC5)
# =============================================================================


class TestInsightModel:
    """Tests for the Insight model."""

    def test_insight_with_all_fields(self):
        """Test creating Insight with all fields populated (AC5)."""
        insight = Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Marketing spend increased 30% with no revenue increase",
            supporting_data={
                "metric": "marketing_spend",
                "value": 2600000,
                "expected_value": 2000000,
                "magnitude_pct": 30.0,
            },
            rationale="Marketing spend deviation of 30% suggests potential inefficiency.",
            sources=["marketing_spend", "revenue"],
            recommended_action="Review marketing ROI and campaign effectiveness.",
            created_at=datetime(2024, 10, 15, 12, 0, 0),
        )

        assert insight.category == InsightCategory.RISK
        assert insight.priority == 1
        assert "Marketing spend" in insight.summary
        assert insight.supporting_data["metric"] == "marketing_spend"
        assert "inefficiency" in insight.rationale.lower()
        assert "marketing_spend" in insight.sources
        assert "ROI" in insight.recommended_action

    def test_insight_default_values(self):
        """Test Insight default values for optional fields."""
        insight = Insight(
            category=InsightCategory.ANOMALY,
            priority=3,
            summary="Revenue anomaly detected",
        )

        assert insight.supporting_data == {}
        assert insight.rationale == ""
        assert insight.sources == []
        assert insight.recommended_action == ""
        assert insight.created_at is not None

    def test_insight_priority_bounds(self):
        """Test that priority is bounded 1-5 (AC3)."""
        insight = Insight(
            category=InsightCategory.TREND,
            priority=5,
            summary="Stable trend observed",
        )
        assert 1 <= insight.priority <= 5

    def test_insight_priority_validation_too_low(self):
        """Test that priority < 1 raises validation error."""
        with pytest.raises(ValueError):
            Insight(
                category=InsightCategory.RISK,
                priority=0,
                summary="Invalid priority",
            )

    def test_insight_priority_validation_too_high(self):
        """Test that priority > 5 raises validation error."""
        with pytest.raises(ValueError):
            Insight(
                category=InsightCategory.RISK,
                priority=6,
                summary="Invalid priority",
            )

    def test_insight_serialization(self):
        """Test that Insight can be serialized to dict."""
        insight = Insight(
            category=InsightCategory.OPPORTUNITY,
            priority=2,
            summary="Growth opportunity identified",
            supporting_data={"metric": "revenue", "magnitude": 15.2},
        )

        data = insight.model_dump()
        assert data["category"] == "opportunity"
        assert data["priority"] == 2
        assert data["summary"] == "Growth opportunity identified"
        assert data["supporting_data"]["metric"] == "revenue"

    def test_insight_required_fields(self):
        """Test that required fields raise error if missing."""
        with pytest.raises(ValueError):
            Insight(
                category=InsightCategory.RISK,
                # Missing required 'summary' and 'priority'
            )


# =============================================================================
# Test InsightGenerationResult Model (AC1)
# =============================================================================


class TestInsightGenerationResultModel:
    """Tests for the InsightGenerationResult model."""

    def test_result_with_all_fields(self):
        """Test creating InsightGenerationResult with all fields."""
        insights = [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Critical risk detected",
            ),
            Insight(
                category=InsightCategory.OPPORTUNITY,
                priority=3,
                summary="Growth opportunity",
            ),
        ]

        result = InsightGenerationResult(
            insights=insights,
            total_generated=2,
            generation_method="LLM synthesis (Mistral Large)",
            metrics_analyzed=3,
        )

        assert len(result.insights) == 2
        assert result.total_generated == 2
        assert "Mistral Large" in result.generation_method
        assert result.metrics_analyzed == 3

    def test_result_default_values(self):
        """Test InsightGenerationResult default values."""
        result = InsightGenerationResult(
            total_generated=0,
            metrics_analyzed=0,
        )

        assert result.insights == []
        assert "LLM synthesis" in result.generation_method


# =============================================================================
# Test calculate_insight_priority() Function (AC3)
# =============================================================================


class TestCalculateInsightPriority:
    """Tests for the calculate_insight_priority() function."""

    def test_critical_anomaly_priority_1(self):
        """Test critical anomaly gets priority 1 (AC3)."""
        from raglite.insights.proactive import calculate_insight_priority

        anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=30.0,
        )

        priority = calculate_insight_priority(anomaly=anomaly)
        assert priority == 1

    def test_moderate_anomaly_priority_2(self):
        """Test moderate anomaly gets priority 2."""
        from raglite.insights.proactive import calculate_insight_priority

        anomaly = Anomaly(
            date="2024-Q3",
            metric="expenses",
            value=550000,
            expected_value=500000,
            z_score=2.2,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=10.0,
        )

        priority = calculate_insight_priority(anomaly=anomaly)
        assert priority == 2

    def test_minor_anomaly_priority_3(self):
        """Test minor anomaly gets default priority 3."""
        from raglite.insights.proactive import calculate_insight_priority

        anomaly = Anomaly(
            date="2024-Q3",
            metric="cash_flow",
            value=105000,
            expected_value=100000,
            z_score=1.6,
            severity=AnomalySeverity.MINOR,
            magnitude_pct=5.0,
        )

        priority = calculate_insight_priority(anomaly=anomaly)
        assert priority == 3

    def test_high_magnitude_trend_priority_2(self):
        """Test trend with >20% magnitude gets priority 2."""
        from raglite.insights.proactive import calculate_insight_priority

        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=25.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        priority = calculate_insight_priority(trend=trend)
        assert priority == 2

    def test_medium_magnitude_trend_priority_3(self):
        """Test trend with 10-20% magnitude gets priority 3."""
        from raglite.insights.proactive import calculate_insight_priority

        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=15.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        priority = calculate_insight_priority(trend=trend)
        assert priority == 3

    def test_combined_critical_anomaly_and_trend(self):
        """Test combined critical anomaly and trend gets priority 1."""
        from raglite.insights.proactive import calculate_insight_priority

        anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=30.0,
        )
        trend = Trend(
            metric="marketing_spend",
            direction=TrendDirection.INCREASING,
            magnitude=30.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        priority = calculate_insight_priority(anomaly=anomaly, trend=trend)
        assert priority == 1  # Critical anomaly takes precedence

    def test_default_priority_with_no_inputs(self):
        """Test default priority 3 with no significant inputs."""
        from raglite.insights.proactive import calculate_insight_priority

        priority = calculate_insight_priority()
        assert priority == 3


# =============================================================================
# Test categorize_insight() Function (AC2)
# =============================================================================


class TestCategorizeInsight:
    """Tests for the categorize_insight() function."""

    def test_critical_anomaly_categorized_as_risk(self):
        """Test critical anomaly is categorized as RISK (AC2)."""
        from raglite.insights.proactive import categorize_insight

        anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=30.0,
        )

        category = categorize_insight(anomaly=anomaly)
        assert category == InsightCategory.RISK

    def test_increasing_high_magnitude_trend_categorized_as_opportunity(self):
        """Test increasing trend >10% is categorized as OPPORTUNITY (AC2)."""
        from raglite.insights.proactive import categorize_insight

        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=15.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        category = categorize_insight(trend=trend)
        assert category == InsightCategory.OPPORTUNITY

    def test_decreasing_high_magnitude_trend_categorized_as_risk(self):
        """Test decreasing trend >10% is categorized as RISK (AC2)."""
        from raglite.insights.proactive import categorize_insight

        trend = Trend(
            metric="revenue",
            direction=TrendDirection.DECREASING,
            magnitude=15.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        category = categorize_insight(trend=trend)
        assert category == InsightCategory.RISK

    def test_moderate_anomaly_categorized_as_anomaly(self):
        """Test moderate anomaly (not critical) is categorized as ANOMALY."""
        from raglite.insights.proactive import categorize_insight

        anomaly = Anomaly(
            date="2024-Q3",
            metric="expenses",
            value=550000,
            expected_value=500000,
            z_score=2.2,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=10.0,
        )

        category = categorize_insight(anomaly=anomaly)
        assert category == InsightCategory.ANOMALY

    def test_stable_trend_categorized_as_trend(self):
        """Test stable trend is categorized as TREND."""
        from raglite.insights.proactive import categorize_insight

        trend = Trend(
            metric="cash_flow",
            direction=TrendDirection.STABLE,
            magnitude=3.0,
            start_date="2024-Q1",
            end_date="2024-Q4",
        )

        category = categorize_insight(trend=trend)
        assert category == InsightCategory.TREND

    def test_forecast_only_categorized_as_strategic_priority(self):
        """Test forecast without anomaly/trend is categorized as STRATEGIC_PRIORITY."""
        from raglite.insights.proactive import categorize_insight

        forecast = ForecastResult(
            metric_name="revenue",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=1100000,
                    lower=1000000,
                    upper=1200000,
                )
            ],
            periods_ahead=4,
        )

        category = categorize_insight(forecast=forecast)
        assert category == InsightCategory.STRATEGIC_PRIORITY


# =============================================================================
# Test filter_insights() Function (AC3, AC4)
# =============================================================================


class TestFilterInsights:
    """Tests for the filter_insights() function."""

    @pytest.fixture
    def sample_insights(self) -> list[Insight]:
        """Create sample insights for filtering tests."""
        return [
            Insight(
                category=InsightCategory.RISK,
                priority=1,
                summary="Critical risk",
            ),
            Insight(
                category=InsightCategory.OPPORTUNITY,
                priority=2,
                summary="Growth opportunity",
            ),
            Insight(
                category=InsightCategory.RISK,
                priority=3,
                summary="Medium risk",
            ),
            Insight(
                category=InsightCategory.ANOMALY,
                priority=4,
                summary="Minor anomaly",
            ),
            Insight(
                category=InsightCategory.TREND,
                priority=5,
                summary="Stable trend",
            ),
        ]

    def test_filter_by_category(self, sample_insights):
        """Test filtering insights by category."""
        from raglite.insights.proactive import filter_insights

        result = filter_insights(sample_insights, category=InsightCategory.RISK)

        assert len(result) == 2
        assert all(i.category == InsightCategory.RISK for i in result)

    def test_filter_by_max_priority(self, sample_insights):
        """Test filtering insights by max priority."""
        from raglite.insights.proactive import filter_insights

        result = filter_insights(sample_insights, max_priority=2)

        assert len(result) == 2
        assert all(i.priority <= 2 for i in result)

    def test_filter_by_limit(self, sample_insights):
        """Test limiting number of insights returned."""
        from raglite.insights.proactive import filter_insights

        result = filter_insights(sample_insights, limit=3)

        assert len(result) == 3

    def test_filter_combined(self, sample_insights):
        """Test combining multiple filters."""
        from raglite.insights.proactive import filter_insights

        result = filter_insights(
            sample_insights,
            category=InsightCategory.RISK,
            max_priority=2,
            limit=1,
        )

        assert len(result) == 1
        assert result[0].category == InsightCategory.RISK
        assert result[0].priority <= 2

    def test_filter_no_match(self, sample_insights):
        """Test filter with no matching insights."""
        from raglite.insights.proactive import filter_insights

        result = filter_insights(
            sample_insights,
            category=InsightCategory.STRATEGIC_PRIORITY,
        )

        assert len(result) == 0


# =============================================================================
# Test synthesize_insight() Function (AC1, AC5)
# =============================================================================


class TestSynthesizeInsight:
    """Tests for the synthesize_insight() function."""

    @pytest.fixture
    def sample_anomaly(self) -> Anomaly:
        """Create sample anomaly for synthesis tests."""
        return Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=30.0,
        )

    @pytest.fixture
    def sample_trend(self) -> Trend:
        """Create sample trend for synthesis tests."""
        return Trend(
            metric="revenue",
            direction=TrendDirection.STABLE,
            magnitude=2.0,
            confidence=0.9,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.02,
            qoq_growth=0.5,
        )

    @pytest.mark.asyncio
    async def test_synthesize_anomaly_with_mocked_mistral(self, sample_anomaly):
        """Test synthesize_insight with mocked Mistral client."""
        from raglite.insights.proactive import synthesize_insight

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""SUMMARY: Marketing spend increased 30% with no revenue increase.
RATIONALE: The significant deviation in marketing spend without corresponding revenue growth suggests potential inefficiency in marketing campaigns.
ACTION: Review marketing ROI and campaign effectiveness."""
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            summary, rationale, action = await synthesize_insight(anomaly=sample_anomaly)

        assert "marketing spend" in summary.lower() or "30%" in summary
        assert len(rationale) > 0
        assert len(action) > 0
        mock_client.chat.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_trend_with_mocked_mistral(self, sample_trend):
        """Test synthesize_insight with trend and mocked Mistral."""
        from raglite.insights.proactive import synthesize_insight

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""SUMMARY: Revenue shows stable growth pattern.
RATIONALE: The 2% stable growth indicates consistent performance without significant volatility.
ACTION: Continue monitoring current strategies."""
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            summary, rationale, action = await synthesize_insight(trend=sample_trend)

        assert len(summary) > 0
        assert len(rationale) > 0
        assert len(action) > 0

    @pytest.mark.asyncio
    async def test_synthesize_fallback_on_error(self, sample_anomaly):
        """Test that synthesize_insight returns fallback on API error."""
        from raglite.insights.proactive import synthesize_insight

        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = Exception("API error")

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            summary, rationale, action = await synthesize_insight(anomaly=sample_anomaly)

        # Should return fallback values
        assert "marketing_spend" in summary
        assert "moderate" in summary
        assert len(rationale) > 0
        assert len(action) > 0

    @pytest.mark.asyncio
    async def test_synthesize_prompt_contains_context(self, sample_anomaly, sample_trend):
        """Test that the LLM prompt contains all context."""
        from raglite.insights.proactive import synthesize_insight

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="SUMMARY: Test\nRATIONALE: Test\nACTION: Test"))
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            await synthesize_insight(anomaly=sample_anomaly, trend=sample_trend)

        # Check the prompt sent to Mistral
        call_args = mock_client.chat.complete.call_args
        prompt = call_args.kwargs["messages"][0]["content"]

        assert "marketing_spend" in prompt.lower()
        assert "30" in prompt  # magnitude_pct
        assert "revenue" in prompt.lower()


# =============================================================================
# Test generate_insights() Function (AC1-AC6)
# =============================================================================


class TestGenerateInsights:
    """Tests for the generate_insights() function."""

    @pytest.fixture
    def sample_anomalies(self) -> list[Anomaly]:
        """Create sample anomalies."""
        return [
            Anomaly(
                date="2024-Q3",
                metric="marketing_spend",
                value=2600000,
                expected_value=2000000,
                z_score=2.5,
                severity=AnomalySeverity.MODERATE,
                magnitude_pct=30.0,
            ),
        ]

    @pytest.fixture
    def sample_trends(self) -> list[Trend]:
        """Create sample trends."""
        return [
            Trend(
                metric="revenue",
                direction=TrendDirection.STABLE,
                magnitude=2.0,
                confidence=0.9,
                start_date="2024-Q1",
                end_date="2024-Q4",
                cagr=0.02,
                qoq_growth=0.5,
            ),
        ]

    @pytest.fixture
    def sample_forecasts(self) -> list[ForecastResult]:
        """Create sample forecasts."""
        return [
            ForecastResult(
                metric_name="cash_flow",
                forecast=[
                    ForecastPoint(
                        date=datetime(2025, 1, 1),
                        value=1100000,
                        lower=1000000,
                        upper=1200000,
                    )
                ],
                periods_ahead=4,
            ),
        ]

    @pytest.mark.asyncio
    async def test_generate_insights_returns_result(
        self, sample_anomalies, sample_trends, sample_forecasts
    ):
        """Test that generate_insights returns InsightGenerationResult (AC1)."""
        from raglite.insights.proactive import generate_insights

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="SUMMARY: Test insight\nRATIONALE: Test\nACTION: Test")
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights(sample_anomalies, sample_trends, sample_forecasts)

        assert isinstance(result, InsightGenerationResult)
        assert result.total_generated == 3  # 1 anomaly + 1 trend + 1 forecast
        assert result.metrics_analyzed == 3

    @pytest.mark.asyncio
    async def test_generate_insights_empty_input_raises_error(self):
        """Test that empty inputs raise ValueError."""
        from raglite.insights.proactive import generate_insights

        with pytest.raises(ValueError, match="No data to analyze"):
            await generate_insights([], [], [])

    @pytest.mark.asyncio
    async def test_generate_insights_anomaly_only(self, sample_anomalies):
        """Test generate_insights with anomaly only."""
        from raglite.insights.proactive import generate_insights

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="SUMMARY: Anomaly detected\nRATIONALE: Test\nACTION: Test"
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights(sample_anomalies, [], [])

        assert result.total_generated == 1
        assert result.insights[0].category == InsightCategory.ANOMALY

    @pytest.mark.asyncio
    async def test_generate_insights_sorted_by_priority(
        self, sample_anomalies, sample_trends, sample_forecasts
    ):
        """Test insights are sorted by priority (AC3)."""
        from raglite.insights.proactive import generate_insights

        # Create critical anomaly
        critical_anomaly = Anomaly(
            date="2024-Q3",
            metric="critical_metric",
            value=5000000,
            expected_value=2000000,
            z_score=4.0,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=150.0,
        )

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="SUMMARY: Test\nRATIONALE: Test\nACTION: Test"))
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights(
                [critical_anomaly] + sample_anomalies,
                sample_trends,
                sample_forecasts,
            )

        # First insight should be highest priority (lowest number)
        priorities = [i.priority for i in result.insights]
        assert priorities == sorted(priorities)

    @pytest.mark.asyncio
    async def test_generate_insights_deduplication(self):
        """Test that duplicate metrics are deduplicated."""
        from raglite.insights.proactive import generate_insights

        # Same metric, different dates
        anomalies = [
            Anomaly(
                date="2024-Q3",
                metric="revenue",
                value=1000000,
                expected_value=800000,
                z_score=2.5,
                severity=AnomalySeverity.MODERATE,
                magnitude_pct=25.0,
            ),
            Anomaly(
                date="2024-Q3",  # Same date+metric = duplicate key
                metric="revenue",
                value=1100000,
                expected_value=800000,
                z_score=3.0,
                severity=AnomalySeverity.CRITICAL,
                magnitude_pct=37.5,
            ),
        ]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="SUMMARY: Test\nRATIONALE: Test\nACTION: Test"))
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights(anomalies, [], [])

        # Should be deduplicated - only 1 insight for revenue Q3
        assert result.total_generated == 1

    @pytest.mark.asyncio
    async def test_generate_insights_auto_synthesize_false(self, sample_anomalies, sample_trends):
        """Test generate_insights with auto_synthesize=False."""
        from raglite.insights.proactive import generate_insights

        result = await generate_insights(
            sample_anomalies,
            sample_trends,
            [],
            auto_synthesize=False,
        )

        # Should not call LLM
        assert result.total_generated == 2
        assert result.generation_method == "Rule-based"
        # Summaries should be simple
        for insight in result.insights:
            assert len(insight.summary) > 0
            assert insight.rationale == ""

    @pytest.mark.asyncio
    async def test_generate_insights_supporting_data_populated(self, sample_anomalies):
        """Test that supporting_data dict is populated (AC5)."""
        from raglite.insights.proactive import generate_insights

        result = await generate_insights(
            sample_anomalies,
            [],
            [],
            auto_synthesize=False,
        )

        insight = result.insights[0]
        assert "metric" in insight.supporting_data
        assert "value" in insight.supporting_data
        assert "z_score" in insight.supporting_data
        assert insight.supporting_data["metric"] == "marketing_spend"


# =============================================================================
# Test Marketing Spend Example (AC6)
# =============================================================================


class TestMarketingSpendExample:
    """Tests for the marketing spend anomaly example from AC6."""

    @pytest.mark.asyncio
    async def test_marketing_spend_anomaly_generates_risk_insight(self):
        """Test AC6: Marketing spend 30% YoY increase with stable revenue -> RISK."""
        from raglite.insights.proactive import generate_insights

        # Marketing spend anomaly
        marketing_anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=30.0,
        )

        # Revenue stable trend
        revenue_trend = Trend(
            metric="revenue",
            direction=TrendDirection.STABLE,
            magnitude=2.0,
            confidence=0.9,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.02,
            qoq_growth=0.5,
        )

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""SUMMARY: Q3 marketing spend increased 30% YoY with no corresponding revenue increase - potential inefficiency.
RATIONALE: Marketing spend deviation of 30% without revenue growth suggests campaigns may not be delivering expected ROI.
ACTION: Review marketing campaign effectiveness and ROI metrics."""
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response

        with patch("raglite.shared.clients.get_mistral_client", return_value=mock_client):
            result = await generate_insights([marketing_anomaly], [revenue_trend], [])

        # Should generate insights for both
        assert result.total_generated == 2

        # Find marketing insight
        marketing_insight = next(
            (i for i in result.insights if "marketing" in i.supporting_data.get("metric", "")),
            None,
        )
        assert marketing_insight is not None
        assert marketing_insight.category == InsightCategory.ANOMALY
        assert (
            "marketing" in marketing_insight.summary.lower() or "30%" in marketing_insight.summary
        )


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in insight generation."""

    @pytest.mark.asyncio
    async def test_single_anomaly_no_trends_no_forecasts(self):
        """Test with single anomaly only."""
        from raglite.insights.proactive import generate_insights

        anomaly = Anomaly(
            date="2024-Q3",
            metric="revenue",
            value=1500000,
            expected_value=1000000,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=50.0,
        )

        result = await generate_insights([anomaly], [], [], auto_synthesize=False)

        assert result.total_generated == 1
        assert result.insights[0].category == InsightCategory.RISK
        assert result.insights[0].priority == 1

    @pytest.mark.asyncio
    async def test_only_trends(self):
        """Test with trends only."""
        from raglite.insights.proactive import generate_insights

        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=25.0,
            confidence=0.95,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.25,
            qoq_growth=6.0,
        )

        result = await generate_insights([], [trend], [], auto_synthesize=False)

        assert result.total_generated == 1
        assert result.insights[0].category == InsightCategory.OPPORTUNITY

    @pytest.mark.asyncio
    async def test_only_forecasts(self):
        """Test with forecasts only."""
        from raglite.insights.proactive import generate_insights

        forecast = ForecastResult(
            metric_name="revenue",
            forecast=[
                ForecastPoint(
                    date=datetime(2025, 1, 1),
                    value=1100000,
                    lower=900000,
                    upper=1300000,
                )
            ],
            periods_ahead=4,
        )

        result = await generate_insights([], [], [forecast], auto_synthesize=False)

        assert result.total_generated == 1
        assert result.insights[0].category == InsightCategory.STRATEGIC_PRIORITY

    @pytest.mark.asyncio
    async def test_conflicting_signals(self):
        """Test handling of conflicting signals (anomaly + positive trend)."""
        from raglite.insights.proactive import generate_insights

        # Critical anomaly (negative signal)
        anomaly = Anomaly(
            date="2024-Q3",
            metric="expenses",
            value=5000000,
            expected_value=3000000,
            z_score=3.5,
            severity=AnomalySeverity.CRITICAL,
            magnitude_pct=66.7,
        )

        # Positive trend (different metric)
        trend = Trend(
            metric="revenue",
            direction=TrendDirection.INCREASING,
            magnitude=20.0,
            confidence=0.9,
            start_date="2024-Q1",
            end_date="2024-Q4",
            cagr=0.20,
            qoq_growth=5.0,
        )

        result = await generate_insights([anomaly], [trend], [], auto_synthesize=False)

        # Should generate both insights
        assert result.total_generated == 2

        # Find the risk insight
        risk_insights = [i for i in result.insights if i.category == InsightCategory.RISK]
        assert len(risk_insights) >= 1

        # Find the opportunity insight
        opp_insights = [i for i in result.insights if i.category == InsightCategory.OPPORTUNITY]
        assert len(opp_insights) >= 1


# =============================================================================
# Test Structured Logging (AC1)
# =============================================================================


class TestStructuredLogging:
    """Tests for structured logging in insight generation."""

    @pytest.mark.asyncio
    async def test_logging_on_insight_generation(self, caplog):
        """Test that insight generation logs with structured context."""
        from raglite.insights.proactive import generate_insights

        caplog.set_level(logging.INFO)

        anomaly = Anomaly(
            date="2024-Q3",
            metric="revenue",
            value=1500000,
            expected_value=1000000,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=50.0,
        )

        await generate_insights([anomaly], [], [], auto_synthesize=False)

        # Check that logs were emitted
        assert len(caplog.records) > 0

        # Check for key log messages
        log_messages = [r.message for r in caplog.records]
        assert any(
            "insight generation" in msg.lower() or "insight generated" in msg.lower()
            for msg in log_messages
        )

    @pytest.mark.asyncio
    async def test_logging_includes_insight_details(self, caplog):
        """Test that log entries include insight details."""
        from raglite.insights.proactive import generate_insights

        caplog.set_level(logging.INFO)

        anomaly = Anomaly(
            date="2024-Q3",
            metric="marketing_spend",
            value=2600000,
            expected_value=2000000,
            z_score=2.5,
            severity=AnomalySeverity.MODERATE,
            magnitude_pct=30.0,
        )

        await generate_insights([anomaly], [], [], auto_synthesize=False)

        # Check for category in log records
        found_category_log = False
        for record in caplog.records:
            if hasattr(record, "category") or "anomaly" in str(record.message).lower():
                found_category_log = True
                break
        assert found_category_log
