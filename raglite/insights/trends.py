"""Trend analysis and pattern recognition for financial time-series data.

Story 4.6: Statistical trend analysis with CAGR, QoQ growth, and Pearson correlation.
Target: ~50-80 lines per Tech Spec Section 3.4 (comprehensive docstrings acceptable per Story 4.5).
"""

from itertools import combinations

import numpy as np
from scipy.stats import pearsonr

from raglite.shared.logging import get_logger
from raglite.shared.models import (
    CorrelationResult,
    TimeSeriesData,
    Trend,
    TrendAnalysisResult,
    TrendDirection,
)

logger = get_logger(__name__)


def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """Calculate Compound Annual Growth Rate.

    Story 4.6 AC2: CAGR calculation for growth patterns.

    Args:
        start_value: Initial value at start of period
        end_value: Final value at end of period
        years: Number of years in the period

    Returns:
        CAGR as a decimal (e.g., 0.15 for 15% growth)

    Example:
        >>> calculate_cagr(100.0, 150.0, 2.0)
        0.2247...  # ~22.47% annual growth rate
    """
    if start_value <= 0 or years <= 0:
        return 0.0
    return float(((end_value / start_value) ** (1 / years)) - 1)


def calculate_qoq_growth(values: list[float]) -> float:
    """Calculate average Quarter-over-Quarter growth rate.

    Story 4.6 AC2: QoQ growth rate calculation.

    Args:
        values: List of sequential values (quarters)

    Returns:
        Average QoQ growth rate as percentage (e.g., 5.2 for 5.2%)

    Example:
        >>> calculate_qoq_growth([100.0, 105.0, 110.0, 116.0])
        5.22...  # ~5.22% average QoQ growth
    """
    if len(values) < 2:
        return 0.0
    growths = [
        (values[i] - values[i - 1]) / values[i - 1] * 100
        for i in range(1, len(values))
        if values[i - 1] != 0
    ]
    return float(np.mean(growths)) if growths else 0.0


def classify_direction(cagr: float, threshold: float = 0.05) -> TrendDirection:
    """Classify trend direction based on CAGR.

    Story 4.6 AC3: Direction classification.

    Args:
        cagr: Compound Annual Growth Rate as decimal
        threshold: Growth threshold for classification (default 0.05 = 5%)

    Returns:
        TrendDirection enum value

    Example:
        >>> classify_direction(0.10)  # 10% growth
        TrendDirection.INCREASING
        >>> classify_direction(-0.08)  # -8% growth
        TrendDirection.DECREASING
        >>> classify_direction(0.02)  # 2% growth
        TrendDirection.STABLE
    """
    if cagr > threshold:
        return TrendDirection.INCREASING
    elif cagr < -threshold:
        return TrendDirection.DECREASING
    return TrendDirection.STABLE


def detect_correlation(
    metric_a: str,
    metric_b: str,
    values_a: list[float],
    values_b: list[float],
) -> CorrelationResult:
    """Detect correlation between two metrics using Pearson correlation.

    Story 4.6 AC1/AC2: Correlation detection.

    Args:
        metric_a: Name of first metric
        metric_b: Name of second metric
        values_a: Values for first metric
        values_b: Values for second metric

    Returns:
        CorrelationResult with coefficient, p-value, and interpretation

    Raises:
        ValueError: If fewer than 3 matching data points

    Example:
        >>> detect_correlation("revenue", "expenses", [100, 110, 120], [50, 55, 60])
        CorrelationResult(metric_a="revenue", metric_b="expenses", correlation_coefficient=1.0, ...)
    """
    if len(values_a) != len(values_b) or len(values_a) < 3:
        raise ValueError("Need at least 3 matching data points for correlation analysis")

    # Check for constant values (zero variance) which makes correlation undefined
    if np.std(values_a) == 0 or np.std(values_b) == 0:
        return CorrelationResult(
            metric_a=metric_a,
            metric_b=metric_b,
            correlation_coefficient=0.0,
            p_value=1.0,  # Not significant
            interpretation="Undefined (constant values)",
        )

    r, p_value = pearsonr(values_a, values_b)

    # Generate interpretation
    abs_r = abs(r)
    if abs_r > 0.7:
        strength = "Strong"
    elif abs_r > 0.4:
        strength = "Moderate"
    else:
        strength = "Weak"
    direction = "positive" if r > 0 else "negative"
    interpretation = f"{strength} {direction} correlation"

    return CorrelationResult(
        metric_a=metric_a,
        metric_b=metric_b,
        correlation_coefficient=round(float(r), 3),
        p_value=round(float(p_value), 4),
        interpretation=interpretation,
    )


async def explain_trend(trend: Trend) -> str:
    """Generate LLM-powered explanation for a trend.

    Story 4.6 AC2: Contextual reasoning for trend significance.

    Args:
        trend: Detected trend to explain

    Returns:
        LLM-generated explanation string

    Example:
        >>> explanation = await explain_trend(trend)
        >>> print(explanation)
        "Revenue shows strong growth of 15.2% CAGR over 8 quarters..."
    """
    from raglite.shared.clients import get_mistral_client

    prompt = f"""Analyze this financial trend and provide a brief explanation (2-3 sentences):

Metric: {trend.metric}
Direction: {trend.direction.value}
CAGR: {trend.cagr:.1%}
QoQ Average Growth: {trend.qoq_growth:.1f}%
Period: {trend.start_date} to {trend.end_date}
Magnitude: {trend.magnitude:.1f}%

Provide possible business implications of this trend. Be specific but concise."""

    try:
        client = get_mistral_client()
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        explanation = response.choices[0].message.content if response.choices else ""

        logger.info(
            "Trend explanation generated",
            extra={
                "metric": trend.metric,
                "direction": trend.direction.value,
                "cagr": round(trend.cagr, 4),
            },
        )

        return explanation.strip()
    except Exception as e:
        logger.warning(
            "Failed to generate trend explanation",
            extra={"metric": trend.metric, "error": str(e)},
        )
        return (
            f"Trend detected: {trend.metric} shows {trend.direction.value} trend "
            f"with {trend.cagr:.1%} CAGR from {trend.start_date} to {trend.end_date}."
        )


async def analyze_trends(
    metrics: list[str],
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
    trends: list[Trend] = []
    correlations: list[CorrelationResult] = []
    metrics_values: dict[str, list[float]] = {}

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

        ts = timeseries_data[metric]
        if len(ts.points) < 3:
            raise ValueError(
                f"Insufficient data for metric '{metric}': {len(ts.points)} points. "
                "Minimum 3 required for trend analysis."
            )

        values = [p.value for p in ts.points]
        dates = [p.label or p.date.strftime("%Y-%m-%d") for p in ts.points]
        metrics_values[metric] = values

        # Calculate years for CAGR (assume quarterly data = 0.25 years per point)
        years = len(values) * 0.25

        # Calculate growth metrics
        cagr = calculate_cagr(values[0], values[-1], years)
        qoq = calculate_qoq_growth(values)
        direction = classify_direction(cagr)
        magnitude = abs(cagr) * 100  # Convert to percentage

        # Calculate confidence based on data consistency
        # Higher confidence if QoQ growth is consistent with CAGR direction
        std_growth = (
            float(
                np.std(
                    [
                        (values[i] - values[i - 1]) / values[i - 1]
                        for i in range(1, len(values))
                        if values[i - 1] != 0
                    ]
                )
            )
            if len(values) > 1
            else 0.0
        )
        confidence = max(0.0, min(1.0, 1.0 - std_growth))

        trend = Trend(
            metric=metric,
            direction=direction,
            magnitude=round(magnitude, 1),
            confidence=round(confidence, 2),
            start_date=dates[0],
            end_date=dates[-1],
            cagr=round(cagr, 4),
            qoq_growth=round(qoq, 2),
        )

        # Auto-explain if requested
        if auto_explain:
            trend.description = await explain_trend(trend)

        trends.append(trend)

        # AC4: Structured logging for each detected trend
        logger.info(
            "Trend detected",
            extra={
                "metric": metric,
                "direction": direction.value,
                "magnitude": round(magnitude, 1),
                "cagr": round(cagr, 4),
                "qoq_growth": round(qoq, 2),
                "confidence": round(confidence, 2),
                "start_date": dates[0],
                "end_date": dates[-1],
                "data_points": len(values),
            },
        )

    # Detect correlations between all metric pairs
    if len(metrics_values) >= 2:
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
    )
