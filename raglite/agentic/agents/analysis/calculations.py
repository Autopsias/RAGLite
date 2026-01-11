"""Financial calculation functions for analysis agent.

This module contains all the mathematical calculation functions used
by the analysis agent for different types of financial analysis.
"""


def _calculate_yoy_growth(data: dict[str, float]) -> tuple[float, str]:
    """Calculate year-over-year growth percentage.

    Expects dict with two values (previous and current).
    Formula: (current - previous) / previous
    """
    if len(data) < 2:
        raise ValueError("YoY growth requires at least 2 data points")

    values = sorted(data.values())
    previous, current = values[0], values[1]

    if previous == 0:
        raise ValueError("Previous value cannot be zero for YoY growth")

    growth = (current - previous) / previous
    calculation = f"({current} - {previous}) / {previous} = {growth:.2f}"

    return growth, calculation


def _calculate_variance(data: dict[str, float]) -> tuple[float, str]:
    """Calculate variance (difference between actual and budget).

    Expects dict with 'budget' and 'actual' keys.
    Formula: (actual - budget) / budget
    """
    if "budget" not in data or "actual" not in data:
        raise ValueError("Variance requires 'budget' and 'actual' keys")

    budget = data["budget"]
    actual = data["actual"]

    if budget == 0:
        raise ValueError("Budget cannot be zero for variance calculation")

    variance = (actual - budget) / budget
    calculation = f"({actual} - {budget}) / {budget} = {variance:.2f}"

    return variance, calculation


def _calculate_trend(data: dict[str, float]) -> tuple[float, str, str]:
    """Detect trend (increasing, decreasing, or stable).

    Calculates slope of data points.

    Returns:
        Tuple of (slope_value, trend_direction, calculation_str)
    """
    if len(data) < 2:
        raise ValueError("Trend detection requires at least 2 data points")

    values = list(data.values())
    n = len(values)

    # Simple linear regression slope
    x_mean = (n - 1) / 2.0  # Indices: 0, 1, 2, ... n-1
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    slope = numerator / denominator if denominator != 0 else 0

    # Determine trend direction
    if slope > 0.1:
        trend = "increasing"
    elif slope < -0.1:
        trend = "decreasing"
    else:
        trend = "stable"

    calculation = f"slope={slope:.2f} per period"

    return slope, trend, calculation


def _calculate_percentage(data: dict[str, float]) -> tuple[float, str]:
    """Calculate percentage (part / whole * 100).

    Expects dict with 'part' and 'whole' keys.
    """
    if "part" not in data or "whole" not in data:
        raise ValueError("Percentage requires 'part' and 'whole' keys")

    part = data["part"]
    whole = data["whole"]

    if whole == 0:
        raise ValueError("Whole cannot be zero for percentage calculation")

    percentage = (part / whole) * 100
    calculation = f"({part} / {whole}) × 100 = {percentage:.2f}"

    return percentage, calculation
