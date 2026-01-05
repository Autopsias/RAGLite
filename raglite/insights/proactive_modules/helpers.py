"""Helper functions for insight prioritization, categorization, and filtering.

Story 4.7: Utility functions for insight analysis.
"""

from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    ForecastResult,
    InsightCategory,
    Trend,
    TrendDirection,
)


def calculate_insight_priority(
    anomaly: Anomaly | None = None,
    trend: Trend | None = None,
    forecast: ForecastResult | None = None,
) -> int:
    """Calculate insight priority (1=critical, 5=low).

    Story 4.7 AC3: Priority scoring based on severity, magnitude, and confidence.

    Args:
        anomaly: Optional anomaly data
        trend: Optional trend data
        forecast: Optional forecast data

    Returns:
        Priority score from 1 (critical) to 5 (low)

    Example:
        >>> calculate_insight_priority(anomaly=Anomaly(severity=AnomalySeverity.CRITICAL, ...))
        1
        >>> calculate_insight_priority(trend=Trend(magnitude=25.0, ...))
        2
    """
    score = 3  # Default: medium priority

    if anomaly:
        if anomaly.severity == AnomalySeverity.CRITICAL:
            score = min(score, 1)
        elif anomaly.severity == AnomalySeverity.MODERATE:
            score = min(score, 2)

    if trend:
        if abs(trend.magnitude) > 20:  # >20% change
            score = min(score, 2)
        elif abs(trend.magnitude) > 10:  # >10% change
            score = min(score, 3)

    if forecast:
        # Low confidence forecasts need attention
        confidence = getattr(forecast, "confidence", None)
        if confidence is not None and confidence < 0.5:
            score = min(score, 2)

    return score


def categorize_insight(
    anomaly: Anomaly | None = None,
    trend: Trend | None = None,
    forecast: ForecastResult | None = None,
) -> InsightCategory:
    """Determine insight category based on inputs.

    Story 4.7 AC2: Insight categorization logic.

    Args:
        anomaly: Optional anomaly data
        trend: Optional trend data
        forecast: Optional forecast data

    Returns:
        InsightCategory enum value

    Example:
        >>> categorize_insight(anomaly=Anomaly(severity=AnomalySeverity.CRITICAL, ...))
        InsightCategory.RISK
        >>> categorize_insight(trend=Trend(direction=TrendDirection.INCREASING, magnitude=15.0, ...))
        InsightCategory.OPPORTUNITY
    """
    # Anomaly-driven: check severity
    if anomaly and anomaly.severity == AnomalySeverity.CRITICAL:
        return InsightCategory.RISK

    # Trend-driven: check direction and magnitude
    if trend:
        if trend.direction == TrendDirection.INCREASING and trend.magnitude > 10:
            return InsightCategory.OPPORTUNITY
        elif trend.direction == TrendDirection.DECREASING and trend.magnitude > 10:
            return InsightCategory.RISK

    # Forecast-driven: low confidence = strategic priority
    if forecast:
        confidence = getattr(forecast, "confidence", None)
        if confidence is not None and confidence < 0.5:
            return InsightCategory.STRATEGIC_PRIORITY

    # Default: anomaly -> ANOMALY, trend -> TREND, forecast -> STRATEGIC_PRIORITY
    if anomaly:
        return InsightCategory.ANOMALY
    if trend:
        return InsightCategory.TREND

    return InsightCategory.STRATEGIC_PRIORITY


def _get_metric_key(
    anomaly: Anomaly | None, trend: Trend | None, forecast: ForecastResult | None
) -> str:
    """Extract metric key for deduplication."""
    if anomaly:
        return f"anomaly:{anomaly.metric}:{anomaly.date}"
    if trend:
        return f"trend:{trend.metric}"
    if forecast:
        return f"forecast:{forecast.metric_name}"
    return "unknown"


def filter_insights(
    insights: list,
    *,
    category: InsightCategory | None = None,
    max_priority: int | None = None,
    limit: int | None = None,
) -> list:
    """Filter and limit insights by category, priority, or count.

    Story 4.7 AC3/AC4: Insight filtering for result limiting.

    Args:
        insights: List of insights to filter
        category: Optional category filter
        max_priority: Optional max priority (1-5, inclusive)
        limit: Optional max number of results

    Returns:
        Filtered list of insights

    Example:
        >>> filtered = filter_insights(insights, category=InsightCategory.RISK, limit=5)
    """
    result = insights

    if category:
        result = [i for i in result if i.category == category]

    if max_priority:
        result = [i for i in result if i.priority <= max_priority]

    if limit:
        result = result[:limit]

    return result
