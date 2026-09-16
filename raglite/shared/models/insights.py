"""Insights, anomalies, trends, and recommendations models.

Defines models for proactive insight generation, anomaly detection, trend analysis,
and strategic recommendations.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# Story 4.5: Anomaly detection models
class AnomalySeverity(StrEnum):
    """Severity levels for detected anomalies.

    Story 4.5 AC3: Anomaly severity scoring based on Z-score thresholds.
    - CRITICAL: |z| > 3.0 - Extreme outlier requiring immediate attention
    - MODERATE: |z| > 2.0 - Significant deviation from expected values
    - MINOR: |z| > 1.5 - Small deviation, may indicate emerging trend
    """

    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"


class Anomaly(BaseModel):
    """Detected anomaly in financial time-series data.

    Story 4.5 AC2/AC4: Anomaly with full context for analysis and reporting.

    Attributes:
        date: Date/period of the anomaly (e.g., "2024-Q3", "Jan 2024")
        metric: Name of the financial metric
        value: Actual observed value
        expected_value: Expected value based on historical mean
        z_score: Standard deviations from mean (negative = below mean)
        severity: Severity level based on Z-score thresholds
        reason: LLM-generated explanation of the anomaly
        magnitude_pct: Percentage deviation from expected value
    """

    date: str = Field(..., description="Date/period of anomaly (e.g., '2024-Q3')")
    metric: str = Field(..., description="Name of the financial metric")
    value: float = Field(..., description="Actual observed value")
    expected_value: float = Field(..., description="Expected value based on mean")
    z_score: float = Field(..., description="Standard deviations from mean")
    severity: AnomalySeverity = Field(..., description="Anomaly severity level")
    reason: str = Field(default="", description="LLM-generated explanation")
    magnitude_pct: float = Field(
        default=0.0,
        description="Percentage deviation from expected ((value-expected)/expected * 100)",
    )


class AnomalyDetectionResult(BaseModel):
    """Result of anomaly detection analysis.

    Story 4.5 AC1: Complete anomaly detection result with metadata.

    Attributes:
        metric_name: Name of the analyzed metric
        anomalies: List of detected Anomaly objects
        data_points_analyzed: Number of data points processed
        detection_method: Statistical method used for detection
        mean_value: Mean of analyzed data
        std_deviation: Standard deviation of analyzed data
    """

    metric_name: str = Field(..., description="Name of analyzed metric")
    anomalies: list[Anomaly] = Field(
        default_factory=list,
        description="List of detected anomalies",
    )
    data_points_analyzed: int = Field(..., description="Number of data points processed")
    detection_method: str = Field(
        default="Z-score analysis (threshold: |z| > 2)",
        description="Statistical method used for detection",
    )
    mean_value: float = Field(default=0.0, description="Mean of analyzed data")
    std_deviation: float = Field(default=0.0, description="Standard deviation of data")


# Story 4.6: Trend analysis and pattern recognition models
class TrendDirection(StrEnum):
    """Direction of detected trend.

    Story 4.6 AC3: Trend direction characterization.

    - INCREASING: Growth > 5% (CAGR threshold)
    - DECREASING: Growth < -5% (CAGR threshold)
    - STABLE: -5% <= growth <= 5%
    - CYCLICAL: Seasonal pattern detected (reserved for future)
    """

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    CYCLICAL = "cyclical"


class Trend(BaseModel):
    """Detected trend in financial time-series data.

    Story 4.6 AC1/AC3: Trend with direction and magnitude.

    Attributes:
        metric: Name of the financial metric (e.g., "revenue", "expenses")
        direction: Trend direction (INCREASING, DECREASING, STABLE, CYCLICAL)
        magnitude: Magnitude as percentage (e.g., 15.2 for 15.2% CAGR)
        confidence: Statistical confidence score (0.0 to 1.0)
        start_date: Start of trend period (e.g., "2024-Q1")
        end_date: End of trend period (e.g., "2024-Q4")
        description: LLM-generated trend explanation
        cagr: Compound Annual Growth Rate
        qoq_growth: Quarter-over-Quarter average growth rate
    """

    metric: str = Field(..., description="Name of the financial metric")
    direction: TrendDirection = Field(..., description="Trend direction")
    magnitude: float = Field(..., description="Magnitude as percentage (e.g., 15.2 for 15.2% CAGR)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Statistical confidence")
    start_date: str = Field(..., description="Start of trend period (e.g., '2024-Q1')")
    end_date: str = Field(..., description="End of trend period (e.g., '2024-Q4')")
    description: str = Field(default="", description="LLM-generated trend explanation")
    cagr: float = Field(default=0.0, description="Compound Annual Growth Rate")
    qoq_growth: float = Field(default=0.0, description="Quarter-over-Quarter average growth rate")


class CorrelationResult(BaseModel):
    """Correlation between two financial metrics.

    Story 4.6 AC1: Correlation detection between metrics using Pearson correlation.

    Attributes:
        metric_a: First metric name
        metric_b: Second metric name
        correlation_coefficient: Pearson correlation coefficient (-1.0 to 1.0)
        p_value: Statistical significance (p-value)
        interpretation: Human-readable interpretation (e.g., "Strong positive correlation")
    """

    metric_a: str = Field(..., description="First metric name")
    metric_b: str = Field(..., description="Second metric name")
    correlation_coefficient: float = Field(
        ..., ge=-1.0, le=1.0, description="Pearson correlation coefficient"
    )
    p_value: float = Field(..., description="Statistical significance (p-value)")
    interpretation: str = Field(
        default="",
        description="Human-readable interpretation (e.g., 'Strong positive correlation')",
    )


class TrendAnalysisResult(BaseModel):
    """Result of trend analysis across multiple metrics.

    Story 4.6 AC1: Complete trend analysis result with metadata.

    Attributes:
        trends: List of detected Trend objects
        correlations: List of detected CorrelationResult objects
        metrics_analyzed: Number of metrics processed
        analysis_method: Methods used for analysis (CAGR, QoQ, Pearson correlation)
    """

    trends: list[Trend] = Field(default_factory=list, description="List of detected trends")
    correlations: list[CorrelationResult] = Field(
        default_factory=list, description="List of detected correlations"
    )
    metrics_analyzed: int = Field(..., description="Number of metrics processed")
    analysis_method: str = Field(
        default="Statistical analysis (CAGR, QoQ, Pearson correlation)",
        description="Methods used for analysis",
    )


# Story 4.7: Proactive insight generation models
class InsightCategory(StrEnum):
    """Category of proactive insight.

    Story 4.7 AC2: Insight categorization.

    - RISK: Negative trend, forecast downturn, critical anomaly
    - OPPORTUNITY: Positive trend, growth potential
    - ANOMALY: Unexplained outlier requiring investigation
    - TREND: Notable pattern (neutral - could be good or bad)
    - STRATEGIC_PRIORITY: High-impact area needing attention
    """

    RISK = "risk"
    OPPORTUNITY = "opportunity"
    ANOMALY = "anomaly"
    TREND = "trend"
    STRATEGIC_PRIORITY = "strategic_priority"


class Insight(BaseModel):
    """Proactive insight generated from financial analysis.

    Story 4.7 AC2/AC3/AC5: Insight with category, priority, and supporting data.

    Attributes:
        category: Insight category (risk, opportunity, anomaly, trend, strategic_priority)
        priority: Priority level (1=critical, 5=low)
        summary: One-sentence insight summary
        supporting_data: Data points supporting the insight
        rationale: LLM-generated explanation
        sources: Source documents/metrics cited
        recommended_action: Suggested next step
        created_at: Insight generation timestamp
    """

    category: InsightCategory = Field(..., description="Insight category")
    priority: int = Field(
        ...,
        ge=1,
        le=5,
        description="Priority (1=critical, 5=low)",
    )
    summary: str = Field(..., description="One-sentence insight summary")
    supporting_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Data points supporting the insight",
    )
    rationale: str = Field(default="", description="LLM-generated explanation")
    sources: list[str] = Field(
        default_factory=list,
        description="Source documents/metrics cited",
    )
    recommended_action: str = Field(
        default="",
        description="Suggested next step",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Insight generation timestamp",
    )


class InsightGenerationResult(BaseModel):
    """Result of proactive insight generation.

    Story 4.7 AC1: Complete insight generation result with metadata.

    Attributes:
        insights: List of generated insights sorted by priority
        total_generated: Total insights before filtering
        generation_method: Method used for insight generation
        metrics_analyzed: Number of unique metrics processed
    """

    insights: list[Insight] = Field(
        default_factory=list,
        description="List of generated insights sorted by priority",
    )
    total_generated: int = Field(..., description="Total insights before filtering")
    generation_method: str = Field(
        default="LLM synthesis (Mistral Large)",
        description="Method used for insight generation",
    )
    metrics_analyzed: int = Field(..., description="Number of unique metrics processed")


# Story 4.8: Strategic recommendation engine models
class RecommendationCategory(StrEnum):
    """Category of strategic recommendation.

    Story 4.8 AC1: Recommendation categorization based on insight type.

    - COST_REDUCTION: Reduce expenses, improve efficiency
    - REVENUE_GROWTH: Increase revenue, expand market
    - RISK_MITIGATION: Address risks, prevent losses
    - OPERATIONAL_EFFICIENCY: Streamline processes
    - STRATEGIC_INVESTMENT: Capital allocation decisions
    """

    COST_REDUCTION = "cost_reduction"
    REVENUE_GROWTH = "revenue_growth"
    RISK_MITIGATION = "risk_mitigation"
    OPERATIONAL_EFFICIENCY = "operational_efficiency"
    STRATEGIC_INVESTMENT = "strategic_investment"


class Recommendation(BaseModel):
    """Strategic recommendation generated from financial insights.

    Story 4.8 AC2/AC3: Recommendation with impact score and rationale.

    Attributes:
        category: Recommendation category
        impact_score: Impact score (1=low, 10=high)
        title: Short recommendation title
        description: Detailed recommendation description
        rationale: LLM-generated explanation of why this matters
        supporting_evidence: Data points supporting the recommendation
        action_steps: Concrete action steps (3-5 items)
        urgency: Urgency level (high, medium, low)
        sources: Source insights/documents cited
        created_at: Recommendation generation timestamp
    """

    category: RecommendationCategory = Field(..., description="Recommendation category")
    impact_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Impact score (1=low, 10=high)",
    )
    title: str = Field(..., description="Short recommendation title")
    description: str = Field(..., description="Detailed recommendation description")
    rationale: str = Field(
        default="",
        description="LLM-generated explanation of why this matters",
    )
    supporting_evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Data points supporting the recommendation",
    )
    action_steps: list[str] = Field(
        default_factory=list,
        description="Concrete action steps (3-5 items)",
    )
    urgency: str = Field(
        default="medium",
        description="Urgency level: high, medium, low",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Source insights/documents cited",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Recommendation generation timestamp",
    )


class RecommendationResult(BaseModel):
    """Result of strategic recommendation generation.

    Story 4.8 AC1: Complete recommendation result with metadata.

    Attributes:
        recommendations: List of recommendations sorted by impact (descending)
        total_generated: Total recommendations before filtering
        generation_method: Method used for recommendation generation
        insights_analyzed: Number of insights processed
    """

    recommendations: list[Recommendation] = Field(
        default_factory=list,
        description="List of recommendations sorted by impact (descending)",
    )
    total_generated: int = Field(..., description="Total recommendations before filtering")
    generation_method: str = Field(
        default="LLM synthesis (Mistral Large)",
        description="Method used for recommendation generation",
    )
    insights_analyzed: int = Field(..., description="Number of insights processed")


# Story 4.9: Proactive Insights MCP Tool models
class InsightsQueryRequest(BaseModel):
    """Request for proactive financial insights via MCP.

    Story 4.9 AC1: MCP tool parameters for insight queries.
    Supports both structured parameters and natural language queries.

    Attributes:
        category: Optional filter by insight category (RISK, OPPORTUNITY, etc.)
        time_period: Optional time period filter (last_quarter, ytd, etc.)
        limit: Maximum insights to return (1-20, default 5)
        include_recommendations: Include strategic recommendations (default True)
        query: Optional natural language query for context-aware filtering
    """

    category: str | None = Field(
        default=None,
        description="Filter by category: RISK, OPPORTUNITY, ANOMALY, TREND, STRATEGIC_PRIORITY",
    )
    time_period: str | None = Field(
        default=None,
        description="Time period: last_quarter, last_year, ytd, current_quarter",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum insights to return (1-20, default 5)",
    )
    include_recommendations: bool = Field(
        default=True,
        description="Include strategic recommendations from Story 4.8",
    )
    query: str | None = Field(
        default=None,
        description="Natural language query for context-aware filtering",
    )


class InsightsQueryResponse(BaseModel):
    """Response from proactive insights MCP tool.

    Story 4.9 AC2/AC4: Ranked insights with conversational formatting.

    Attributes:
        insights: Ranked insights (priority 1=highest first)
        recommendations: Strategic recommendations (impact 10=highest first)
        total_insights: Total insights before limit
        total_recommendations: Total recommendations before filtering
        formatted_summary: LLM-friendly executive summary
        time_period_analyzed: Time period covered by analysis
        generation_time_ms: Total generation time in milliseconds
        source_documents: Documents analyzed for insights
    """

    insights: list[Insight] = Field(
        default_factory=list,
        description="Ranked insights (priority 1=highest first)",
    )
    recommendations: list[Recommendation] = Field(
        default_factory=list,
        description="Strategic recommendations (impact 10=highest first)",
    )
    total_insights: int = Field(..., description="Total insights before limit")
    total_recommendations: int = Field(..., description="Total recommendations before filtering")
    formatted_summary: str = Field(
        default="",
        description="LLM-friendly executive summary",
    )
    time_period_analyzed: str = Field(
        default="",
        description="Time period covered by analysis",
    )
    generation_time_ms: float = Field(
        default=0.0,
        description="Total generation time in milliseconds",
    )
    source_documents: list[str] = Field(
        default_factory=list,
        description="Documents analyzed for insights",
    )
