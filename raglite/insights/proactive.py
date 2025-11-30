"""Proactive insight generation from financial analysis.

Story 4.7: Combines anomaly detection, trend analysis, and contextual reasoning
to generate prioritized actionable insights.
Target: ~50-80 lines per Tech Spec Section 3.5 (comprehensive docstrings acceptable).
"""

import time
from datetime import UTC, datetime

from raglite.shared.logging import get_logger
from raglite.shared.models import (
    Anomaly,
    AnomalySeverity,
    ForecastResult,
    Insight,
    InsightCategory,
    InsightGenerationResult,
    Trend,
    TrendDirection,
)

logger = get_logger(__name__)


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


async def synthesize_insight(
    anomaly: Anomaly | None = None,
    trend: Trend | None = None,
    forecast: ForecastResult | None = None,
) -> tuple[str, str, str]:
    """Generate LLM-powered insight synthesis with rationale and recommendation.

    Story 4.7 AC1/AC5: Contextual reasoning combining anomalies, trends, and forecasts.

    Args:
        anomaly: Optional anomaly data
        trend: Optional trend data
        forecast: Optional forecast data

    Returns:
        Tuple of (summary, rationale, recommended_action)

    Example:
        >>> summary, rationale, action = await synthesize_insight(anomaly=anomaly)
        >>> print(summary)
        "Marketing spend increased 30% with no revenue increase - potential inefficiency"
    """
    from raglite.shared.clients import get_mistral_client

    # Build context for LLM
    context_parts = []
    if anomaly:
        context_parts.append(
            f"Anomaly: {anomaly.metric} shows {anomaly.magnitude_pct:.1f}% deviation "
            f"(z-score: {anomaly.z_score}, severity: {anomaly.severity.value}) on {anomaly.date}"
        )
    if trend:
        context_parts.append(
            f"Trend: {trend.metric} is {trend.direction.value} by {trend.magnitude:.1f}% "
            f"(CAGR: {trend.cagr:.1%}) from {trend.start_date} to {trend.end_date}"
        )
    if forecast:
        context_parts.append(
            f"Forecast: {forecast.metric_name} predicted for next {forecast.periods_ahead} periods"
        )

    context = "\n".join(context_parts)

    prompt = f"""Analyze this financial data and provide:
1. A one-sentence summary (max 100 chars)
2. A brief rationale (2-3 sentences explaining the significance)
3. A recommended action (1 sentence)

Financial Data:
{context}

Respond in this exact format:
SUMMARY: [your summary]
RATIONALE: [your rationale]
ACTION: [your recommended action]"""

    try:
        client = get_mistral_client()
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content if response.choices else ""

        # Parse response
        summary = ""
        rationale = ""
        action = ""

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("SUMMARY:"):
                summary = line[8:].strip()
            elif line.startswith("RATIONALE:"):
                rationale = line[10:].strip()
            elif line.startswith("ACTION:"):
                action = line[7:].strip()

        # Fallback if parsing fails
        if not summary:
            if anomaly:
                summary = f"{anomaly.metric} shows {anomaly.severity.value} deviation of {anomaly.magnitude_pct:.1f}%"
            elif trend:
                summary = f"{trend.metric} {trend.direction.value} trend of {trend.magnitude:.1f}%"
            else:
                summary = "Financial metric requires attention"

        logger.info(
            "Insight synthesized",
            extra={
                "has_anomaly": anomaly is not None,
                "has_trend": trend is not None,
                "has_forecast": forecast is not None,
            },
        )

        return summary, rationale, action

    except Exception as e:
        logger.warning(f"LLM synthesis failed: {e}", extra={"error": str(e)})
        # Fallback summaries
        if anomaly:
            return (
                f"{anomaly.metric} shows {anomaly.severity.value} deviation of {anomaly.magnitude_pct:.1f}%",
                f"Value of {anomaly.value} deviates significantly from expected {anomaly.expected_value}.",
                "Investigate the cause of this deviation.",
            )
        elif trend:
            return (
                f"{trend.metric} {trend.direction.value} trend of {trend.magnitude:.1f}%",
                f"Trend from {trend.start_date} to {trend.end_date} shows {trend.cagr:.1%} CAGR.",
                "Monitor this trend and plan accordingly.",
            )
        else:
            return (
                "Financial metric requires attention",
                "Forecast data indicates uncertainty.",
                "Review forecast assumptions and data quality.",
            )


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
    insights: list[Insight],
    *,
    category: InsightCategory | None = None,
    max_priority: int | None = None,
    limit: int | None = None,
) -> list[Insight]:
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


async def generate_insights(
    anomalies: list[Anomaly],
    trends: list[Trend],
    forecasts: list[ForecastResult],
    *,
    auto_synthesize: bool = True,
) -> InsightGenerationResult:
    """Generate prioritized insights from anomalies, trends, and forecasts.

    Story 4.7 AC1-AC6: Proactive insight generation with LLM synthesis.

    Args:
        anomalies: List of detected anomalies from Story 4.5
        trends: List of identified trends from Story 4.6
        forecasts: List of forecast results from Story 4.2
        auto_synthesize: If True, generate LLM summaries. Default True.

    Returns:
        InsightGenerationResult containing:
          - insights: List of Insight objects sorted by priority
          - total_generated: Count before filtering
          - generation_method: "LLM synthesis (Mistral Large)"
          - metrics_analyzed: Number of unique metrics processed

    Raises:
        ValueError: If all inputs are empty (nothing to analyze)

    Example:
        >>> from raglite.insights.anomalies import Anomaly
        >>> anomalies = [Anomaly(metric="marketing_spend", severity="critical", ...)]
        >>> result = await generate_insights(anomalies, [], [])
        >>> print(result.insights[0].category)
        InsightCategory.RISK
    """
    start_time = time.time()

    if not anomalies and not trends and not forecasts:
        raise ValueError("No data to analyze: anomalies, trends, and forecasts are all empty")

    logger.info(
        "Starting insight generation",
        extra={
            "anomalies_count": len(anomalies),
            "trends_count": len(trends),
            "forecasts_count": len(forecasts),
            "auto_synthesize": auto_synthesize,
        },
    )

    insights: list[Insight] = []
    seen_metrics: set[str] = set()

    # Process anomalies
    for anomaly in anomalies:
        metric_key = _get_metric_key(anomaly, None, None)
        if metric_key in seen_metrics:
            continue
        seen_metrics.add(metric_key)

        category = categorize_insight(anomaly=anomaly)
        priority = calculate_insight_priority(anomaly=anomaly)

        if auto_synthesize:
            summary, rationale, action = await synthesize_insight(anomaly=anomaly)
        else:
            summary = f"{anomaly.metric} shows {anomaly.severity.value} deviation"
            rationale = ""
            action = ""

        insight = Insight(
            category=category,
            priority=priority,
            summary=summary,
            supporting_data={
                "metric": anomaly.metric,
                "value": anomaly.value,
                "expected_value": anomaly.expected_value,
                "z_score": anomaly.z_score,
                "magnitude_pct": anomaly.magnitude_pct,
                "severity": anomaly.severity.value,
            },
            rationale=rationale,
            sources=[anomaly.metric],
            recommended_action=action,
            created_at=datetime.now(UTC),
        )
        insights.append(insight)

        logger.info(
            "Insight generated from anomaly",
            extra={
                "category": category.value,
                "priority": priority,
                "metric": anomaly.metric,
            },
        )

    # Process trends
    for trend in trends:
        metric_key = _get_metric_key(None, trend, None)
        if metric_key in seen_metrics:
            continue
        seen_metrics.add(metric_key)

        category = categorize_insight(trend=trend)
        priority = calculate_insight_priority(trend=trend)

        if auto_synthesize:
            summary, rationale, action = await synthesize_insight(trend=trend)
        else:
            summary = f"{trend.metric} shows {trend.direction.value} trend"
            rationale = ""
            action = ""

        insight = Insight(
            category=category,
            priority=priority,
            summary=summary,
            supporting_data={
                "metric": trend.metric,
                "direction": trend.direction.value,
                "magnitude": trend.magnitude,
                "cagr": trend.cagr,
                "qoq_growth": trend.qoq_growth,
                "confidence": trend.confidence,
            },
            rationale=rationale,
            sources=[trend.metric],
            recommended_action=action,
            created_at=datetime.now(UTC),
        )
        insights.append(insight)

        logger.info(
            "Insight generated from trend",
            extra={
                "category": category.value,
                "priority": priority,
                "metric": trend.metric,
            },
        )

    # Process forecasts
    for forecast in forecasts:
        metric_key = _get_metric_key(None, None, forecast)
        if metric_key in seen_metrics:
            continue
        seen_metrics.add(metric_key)

        category = categorize_insight(forecast=forecast)
        priority = calculate_insight_priority(forecast=forecast)

        if auto_synthesize:
            summary, rationale, action = await synthesize_insight(forecast=forecast)
        else:
            summary = f"{forecast.metric_name} forecast for {forecast.periods_ahead} periods"
            rationale = ""
            action = ""

        insight = Insight(
            category=category,
            priority=priority,
            summary=summary,
            supporting_data={
                "metric": forecast.metric_name,
                "periods_ahead": forecast.periods_ahead,
                "accuracy_estimate": forecast.accuracy_estimate,
            },
            rationale=rationale,
            sources=[forecast.metric_name],
            recommended_action=action,
            created_at=datetime.now(UTC),
        )
        insights.append(insight)

        logger.info(
            "Insight generated from forecast",
            extra={
                "category": category.value,
                "priority": priority,
                "metric": forecast.metric_name,
            },
        )

    # Sort by priority (1=critical first)
    insights.sort(key=lambda x: x.priority)

    # Calculate metrics
    total_generated = len(insights)
    metrics_analyzed = len(
        {a.metric for a in anomalies}
        | {t.metric for t in trends}
        | {f.metric_name for f in forecasts}
    )

    generation_time_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "Insight generation complete",
        extra={
            "total_generated": total_generated,
            "metrics_analyzed": metrics_analyzed,
            "generation_time_ms": generation_time_ms,
        },
    )

    return InsightGenerationResult(
        insights=insights,
        total_generated=total_generated,
        generation_method="LLM synthesis (Mistral Large)" if auto_synthesize else "Rule-based",
        metrics_analyzed=metrics_analyzed,
    )
