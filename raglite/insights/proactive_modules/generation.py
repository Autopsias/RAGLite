"""Main insight generation orchestration module.

Story 4.7 AC1-AC6: Proactive insight generation with LLM synthesis.
"""

import time
from datetime import UTC, datetime

from raglite.shared.logging import get_logger
from raglite.shared.models import (
    Anomaly,
    ForecastResult,
    Insight,
    InsightGenerationResult,
    Trend,
)

from .helpers import _get_metric_key, calculate_insight_priority, categorize_insight
from .synthesis import synthesize_insight

logger = get_logger(__name__)


async def _process_anomaly(
    anomaly: Anomaly,
    auto_synthesize: bool,
) -> Insight:
    """Process a single anomaly into an insight.

    Args:
        anomaly: Anomaly data to process
        auto_synthesize: If True, generate LLM summary

    Returns:
        Insight object with category, priority, and synthesized summary
    """
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

    logger.info(
        "Insight generated from anomaly",
        extra={
            "category": category.value,
            "priority": priority,
            "metric": anomaly.metric,
        },
    )

    return insight


async def _process_trend(
    trend: Trend,
    auto_synthesize: bool,
) -> Insight:
    """Process a single trend into an insight.

    Args:
        trend: Trend data to process
        auto_synthesize: If True, generate LLM summary

    Returns:
        Insight object with category, priority, and synthesized summary
    """
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

    logger.info(
        "Insight generated from trend",
        extra={
            "category": category.value,
            "priority": priority,
            "metric": trend.metric,
        },
    )

    return insight


async def _process_forecast(
    forecast: ForecastResult,
    auto_synthesize: bool,
) -> Insight:
    """Process a single forecast into an insight.

    Args:
        forecast: Forecast data to process
        auto_synthesize: If True, generate LLM summary

    Returns:
        Insight object with category, priority, and synthesized summary
    """
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

    logger.info(
        "Insight generated from forecast",
        extra={
            "category": category.value,
            "priority": priority,
            "metric": forecast.metric_name,
        },
    )

    return insight


async def generate_insights(
    anomalies: list[Anomaly],
    trends: list[Trend],
    forecasts: list[ForecastResult],
    *,
    auto_synthesize: bool = True,
) -> InsightGenerationResult:
    """Generate prioritized insights from anomalies, trends, and forecasts (Story 4.7).

    Processes each unique metric to create insights with LLM synthesis support.

    Args:
        anomalies: Detected anomalies from Story 4.5
        trends: Identified trends from Story 4.6
        forecasts: Forecast results from Story 4.2
        auto_synthesize: Generate LLM summaries (default True)

    Returns:
        InsightGenerationResult with insights sorted by priority

    Raises:
        ValueError: If all inputs are empty

    Example:
        >>> result = await generate_insights(anomalies, [], [])
        >>> print(result.insights[0].category)  # InsightCategory.RISK
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

        insight = await _process_anomaly(anomaly, auto_synthesize)
        insights.append(insight)

    # Process trends
    for trend in trends:
        metric_key = _get_metric_key(None, trend, None)
        if metric_key in seen_metrics:
            continue
        seen_metrics.add(metric_key)

        insight = await _process_trend(trend, auto_synthesize)
        insights.append(insight)

    # Process forecasts
    for forecast in forecasts:
        metric_key = _get_metric_key(None, None, forecast)
        if metric_key in seen_metrics:
            continue
        seen_metrics.add(metric_key)

        insight = await _process_forecast(forecast, auto_synthesize)
        insights.append(insight)

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
