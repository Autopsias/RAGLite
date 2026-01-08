"""Trend analysis and pattern recognition for financial time-series data.

Story 4.6: Statistical trend analysis with CAGR, QoQ growth, and Pearson correlation.
Target: ~50-80 lines per Tech Spec Section 3.4 (comprehensive docstrings acceptable per Story 4.5).
"""

import numpy as np
from scipy.stats import pearsonr

from raglite.shared.logging import get_logger
from raglite.shared.models import (
    CorrelationResult,
    Trend,
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
