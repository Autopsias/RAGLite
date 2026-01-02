"""Hybrid forecasting - Data preprocessing and validation.

Part of Story 8.1 refactoring to split hybrid.py.

Provides:
- select_regressors: Correlation-based regressor selection
- prepare_regressors: Align, interpolate, and validate regressors
- validate_timeseries_for_forecast: Pre-flight data quality checks
- transform_yoy_to_index: Convert YoY% changes to absolute index
- fetch_historical_metric: Load historical data from PostgreSQL

REFACTORING NOTE (Story 8 Technical Debt):
This file was split from 692 LOC to <200 LOC by extracting:
- YoY transformation → preprocessing_yoy.py
- Regressor selection/preparation → preprocessing_regressors.py
- Data fetching → preprocessing_data.py

All imports remain backward compatible via re-exports below.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

# Re-export functions from split modules for backward compatibility
from .preprocessing_data import (  # noqa: F401
    ensure_historical_data,
    fetch_historical_metric,
)
from .preprocessing_regressors import (  # noqa: F401
    generate_future_regressors,
    prepare_regressors,
    select_regressors,
    validate_regressor_scale,
)
from .preprocessing_yoy import (  # noqa: F401
    detect_yoy_percentage,
    transform_yoy_to_index,
)

# Module-level constants
logger = get_logger(__name__)
MAX_MISSING_RATIO = 0.30  # Maximum 30% missing data allowed
MAX_INTERPOLATION_GAP = 3  # Maximum periods to interpolate
POSITIVE_ONLY_METRICS = {"ebitda", "revenue", "capacity_utilization", "sales_volume"}

# Private function for internal use (kept in this file, not exported)
_generate_future_regressors = generate_future_regressors


def validate_timeseries_for_forecast(
    metric: str, points: list[TimeSeriesPoint]
) -> tuple[bool, list[str]]:
    """Pre-flight validation for time-series data before forecasting.

    FIX (2025-12-16): Detects data quality issues that cause forecast failures:
    1. Scale within expected range (catches kEUR/M€ mixing after extraction)
    2. Sign consistency (positive/negative per metric type)
    3. No extreme swings (>10x between consecutive points = data contamination)

    Args:
        metric: Name of the metric being forecast
        points: List of TimeSeriesPoint data to validate

    Returns:
        Tuple of (is_valid, list_of_issues). is_valid=True if no critical issues.
        Issues are logged as warnings but do not block forecasting.
    """
    if not points:
        return False, ["No data points provided"]

    issues: list[str] = []
    values = [p.value for p in points if p.value is not None]

    if not values:
        return False, ["All data points have None values"]

    metric_lower = metric.lower()

    # Check 1: Sign consistency for positive-only metrics
    if metric_lower in POSITIVE_ONLY_METRICS:
        neg_values = [v for v in values if v < 0]
        if neg_values:
            issues.append(
                f"Found {len(neg_values)} negative values for positive-only metric '{metric}': "
                f"{neg_values[:3]}{'...' if len(neg_values) > 3 else ''}"
            )
            logger.warning(
                f"Data quality issue: Negative values in {metric}",
                extra={
                    "metric": metric,
                    "negative_count": len(neg_values),
                    "sample": neg_values[:3],
                },
            )

    # Check 2: Detect extreme swings (10x jumps indicate data contamination)
    swing_count = 0
    for i in range(1, len(values)):
        if values[i - 1] != 0:
            ratio = abs(values[i] / values[i - 1])
            if ratio > 10 or ratio < 0.1:
                swing_count += 1
                if swing_count <= 3:  # Only log first 3
                    issues.append(
                        f"10x swing at index {i}: {values[i - 1]:.2f} -> {values[i]:.2f} (ratio: {ratio:.1f}x)"
                    )

    if swing_count > 0:
        logger.warning(
            f"Data quality issue: {swing_count} extreme swings (>10x) detected in {metric}",
            extra={"metric": metric, "swing_count": swing_count},
        )

    # Check 3: Scale sanity check for known metrics
    EXPECTED_RANGES = {
        "ebitda": (1, 500),  # 1-500 M€ for SECIL GROUP
        "revenue": (10, 2000),  # 10-2000 M€
        "variable_cost": (10, 500),  # 10-500 EUR/ton
        "capacity_utilization": (0, 100),  # 0-100%
    }

    if metric_lower in EXPECTED_RANGES:
        expected_min, expected_max = EXPECTED_RANGES[metric_lower]
        abs_values = [abs(v) for v in values]
        max_val = max(abs_values)

        if max_val > expected_max * 100:  # 100x threshold for scale detection
            issues.append(
                f"Scale issue: max value {max_val:.0f} exceeds expected max {expected_max} by 100x+ "
                f"(possible kEUR/M€ mixing still present)"
            )
            logger.warning(
                f"Data quality issue: Scale mismatch in {metric}",
                extra={"metric": metric, "max_value": max_val, "expected_max": expected_max},
            )

    # Return validation result (issues are warnings, not blockers)
    is_valid = len(issues) == 0
    if not is_valid:
        logger.info(
            f"Pre-forecast validation found {len(issues)} issues for {metric}",
            extra={"metric": metric, "issue_count": len(issues)},
        )

    return is_valid, issues
