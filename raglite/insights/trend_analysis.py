"""Core trend analysis functionality.

Extracted from trends.py to reduce file size.
Contains the main analyze_trends function and its helpers.
"""

from itertools import combinations
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass

import builtins

from raglite.shared.logging import get_logger
from raglite.shared.models import (
    CorrelationResult,
    TimeSeriesData,
    Trend,
    TrendAnalysisResult,
    TrendDirection,
)

logger = get_logger(__name__)


def _extract_metric_data(ts: TimeSeriesData) -> tuple[builtins.list[float], builtins.list[str]]:
    """Extract values and dates from timeseries data.

    Args:
        ts: TimeSeriesData object with points

    Returns:
        Tuple of (values list, dates list)
    """
    values = [p.value for p in ts.points]
    dates = [p.label or p.date.strftime("%Y-%m-%d") for p in ts.points]
    return values, dates


def _calculate_confidence(values: builtins.list[float]) -> float:
    """Calculate confidence score based on data consistency.

    Higher confidence if QoQ growth is consistent (low standard deviation).

    Args:
        values: List of sequential values

    Returns:
        Confidence score between 0.0 and 1.0
    """
    if len(values) <= 1:
        return 0.0

    std_growth = float(
        np.std(
            [
                (values[i] - values[i - 1]) / values[i - 1]
                for i in range(1, len(values))
                if values[i - 1] != 0
            ]
        )
    )
    return round(max(0.0, min(1.0, 1.0 - std_growth)), 2)


def _create_trend_from_data(
    metric: str,
    values: builtins.list[float],
    dates: builtins.list[str],
    auto_explain: bool = False,
) -> Trend:
    """Create a Trend object from metric values and dates.

    Args:
        metric: Metric name
        values: List of sequential values
        dates: List of corresponding date labels
        auto_explain: If True, generate LLM explanation

    Returns:
        Trend object with calculated metrics
    """
    # Calculate years for CAGR (assume quarterly data = 0.25 years per point)
    years = len(values) * 0.25

    # Calculate growth metrics
    from .trends import calculate_cagr, calculate_qoq_growth, classify_direction

    cagr = calculate_cagr(values[0], values[-1], years)
    qoq = calculate_qoq_growth(values)
    direction = classify_direction(cagr)
    magnitude = abs(cagr) * 100  # Convert to percentage
    confidence = _calculate_confidence(values)

    trend = Trend(
        metric=metric,
        direction=direction,
        magnitude=round(magnitude, 1),
        confidence=confidence,
        start_date=dates[0],
        end_date=dates[-1],
        cagr=round(cagr, 4),
        qoq_growth=round(qoq, 2),
    )

    return trend


def _log_trend_detection(
    metric: str,
    direction: TrendDirection,
    magnitude: float,
    cagr: float,
    qoq: float,
    confidence: float,
    start_date: str,
    end_date: str,
    data_points: int,
) -> None:
    """Log trend detection with structured context.

    Args:
        metric: Metric name
        direction: Trend direction
        magnitude: Trend magnitude percentage
        cagr: Compound annual growth rate
        qoq: Quarter-over-quarter growth
        confidence: Confidence score
        start_date: Start date
        end_date: End date
        data_points: Number of data points
    """
    logger.info(
        "Trend detected",
        extra={
            "metric": metric,
            "direction": direction.value,
            "magnitude": round(magnitude, 1),
            "cagr": round(cagr, 4),
            "qoq_growth": round(qoq, 2),
            "confidence": round(confidence, 2),
            "start_date": start_date,
            "end_date": end_date,
            "data_points": data_points,
        },
    )


async def _analyze_single_metric(
    metric: str,
    ts: TimeSeriesData,
    auto_explain: bool,
) -> tuple[Trend, builtins.list[float]] | None:
    """Analyze a single metric for trends.

    Args:
        metric: Metric name
        ts: TimeSeriesData object
        auto_explain: If True, generate LLM explanation

    Returns:
        Tuple of (Trend, values) or None if metric invalid

    Raises:
        ValueError: If insufficient data points
    """
    if len(ts.points) < 3:
        raise ValueError(
            f"Insufficient data for metric '{metric}': {len(ts.points)} points. "
            "Minimum 3 required for trend analysis."
        )

    values, dates = _extract_metric_data(ts)
    trend = _create_trend_from_data(metric, values, dates, auto_explain)

    # Auto-explain if requested
    if auto_explain:
        from .trends import explain_trend

        try:
            trend.description = await explain_trend(trend)
        except Exception as e:
            logger.warning(f"Failed to generate trend explanation: {e}")
            trend.description = f"Trend detected: {trend.metric} shows {trend.direction.value} trend with {trend.cagr:.1%} CAGR from {trend.start_date} to {trend.end_date}."

    # Log the detected trend
    _log_trend_detection(
        metric=metric,
        direction=trend.direction,
        magnitude=trend.magnitude,
        cagr=trend.cagr,
        qoq=trend.qoq_growth,
        confidence=trend.confidence,
        start_date=trend.start_date,
        end_date=trend.end_date,
        data_points=len(values),
    )

    return trend, values


def _detect_metric_correlations(
    metrics_values: dict[str, builtins.list[float]],
) -> builtins.list[CorrelationResult]:
    """Detect correlations between all metric pairs.

    Args:
        metrics_values: Dict mapping metric names to value lists

    Returns:
        List of significant CorrelationResult objects
    """
    correlations: builtins.list[CorrelationResult] = []

    if len(metrics_values) < 2:
        return correlations

    from .trends import detect_correlation

    for metric_a, metric_b in combinations(metrics_values.keys(), 2):
        values_a = metrics_values[metric_a]
        values_b = metrics_values[metric_b]

        # Ensure same length for correlation
        min_len = min(len(values_a), len(values_b))
        if min_len >= 3:
            try:
                corr = detect_correlation(
                    metric_a, metric_b, values_a[:min_len], values_b[:min_len]
                )
                # Only include significant correlations (|r| > 0.4 and p < 0.1)
                if abs(corr.correlation_coefficient) > 0.4 and corr.p_value < 0.1:
                    correlations.append(corr)
                    logger.info(
                        "Correlation detected",
                        extra={
                            "metric_a": metric_a,
                            "metric_b": metric_b,
                            "correlation": corr.correlation_coefficient,
                            "p_value": corr.p_value,
                            "interpretation": corr.interpretation,
                        },
                    )
            except ValueError as e:
                logger.warning(f"Correlation detection failed for {metric_a}/{metric_b}: {e}")

    return correlations


async def analyze_trends(
    metrics: builtins.list[str],
    timeseries_data: dict[str, TimeSeriesData],
    *,
    auto_explain: bool = False,
) -> TrendAnalysisResult:
    """Analyze trends and patterns in financial data.

    Story 4.6 AC1-AC5: Statistical trend analysis with growth patterns and correlations.

    Args:
        metrics: List of metric names to analyze (e.g., ["revenue", "expenses", "cash_flow"])
        timeseries_data: Dict mapping metric names to their TimeSeriesData
        auto_explain: If True, automatically generate LLM explanations for each trend.
            Default False to reduce API calls in bulk processing.

    Returns:
        TrendAnalysisResult containing:
          - trends: List of detected Trend objects
          - correlations: List of CorrelationResult objects
          - metrics_analyzed: Number of metrics processed
          - analysis_method: "Statistical analysis (CAGR, QoQ, Pearson correlation)"

    Raises:
        ValueError: If timeseries has fewer than 3 data points for any metric

    Example:
        >>> from raglite.shared.models import TimeSeriesData, TimeSeriesPoint
        >>> from datetime import datetime
        >>> revenue = TimeSeriesData(metric_name="revenue", points=[...])
        >>> expenses = TimeSeriesData(metric_name="expenses", points=[...])
        >>> result = await analyze_trends(
        ...     ["revenue", "expenses"],
        ...     {"revenue": revenue, "expenses": expenses}
        ... )
        >>> print(result.trends[0])
        Trend(metric="revenue", direction=INCREASING, magnitude=15.2, ...)
    """
    trends: builtins.list[Trend] = []
    metrics_values: dict[str, builtins.list[float]] = {}

    logger.info(
        "Starting trend analysis",
        extra={
            "metrics": metrics,
            "metrics_count": len(metrics),
            "auto_explain": auto_explain,
        },
    )

    # Analyze each metric for trends
    for metric in metrics:
        if metric not in timeseries_data:
            logger.warning(f"Metric '{metric}' not found in timeseries_data")
            continue

        result = await _analyze_single_metric(metric, timeseries_data[metric], auto_explain)
        if result:
            trend, values = result
            trends.append(trend)
            metrics_values[metric] = values

    # Detect correlations between all metric pairs
    correlations = _detect_metric_correlations(metrics_values)

    logger.info(
        "Trend analysis complete",
        extra={
            "trends_found": len(trends),
            "correlations_found": len(correlations),
            "metrics_analyzed": len(metrics_values),
        },
    )

    return TrendAnalysisResult(
        trends=trends,
        correlations=correlations,
        metrics_analyzed=len(metrics_values),
        analysis_method="Statistical analysis (CAGR, QoQ, Pearson correlation)",
    )
