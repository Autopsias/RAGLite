"""SQL extraction data validation.

Part of Story 8.1 refactoring to split sql_extraction.py.
Handles scale validation and quality checks for extracted timeseries data.
"""

import statistics

from raglite.forecasting.timeseries.metadata import ExtractionError
from raglite.forecasting.timeseries.sql_extraction_config import get_ebitda_metrics
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


def validate_scale_with_config(points: list[TimeSeriesPoint], metric: str) -> None:
    """Generic scale validation using config scale_reference_median.

    Story 6.28: Checks if extracted values are within reasonable range.
    Catches scale mismatches (e.g., kEUR vs EUR, 1000x errors).

    Args:
        points: Extracted time-series points
        metric: Metric name
    """
    try:
        from raglite.forecasting.data_quality.config import get_variable_config

        var_config = get_variable_config(metric)
        if var_config and var_config.value_range.scale_reference_median is not None:
            expected_median = var_config.value_range.scale_reference_median
            values_for_check = [p.value for p in points if p.value is not None]
            if values_for_check:
                actual_median = statistics.median(values_for_check)
                # Calculate ratio - handle sign differences
                if expected_median != 0:
                    ratio = abs(actual_median / expected_median)
                else:
                    ratio = 1.0

                # Flag significant scale mismatches (>10x or <0.1x)
                if ratio > 10 or ratio < 0.1:
                    logger.warning(
                        f"SCALE MISMATCH DETECTED for {metric}: actual median {actual_median:.2f} "
                        f"vs expected {expected_median:.2f} (ratio: {ratio:.2f}x)",
                        extra={
                            "metric": metric,
                            "actual_median": actual_median,
                            "expected_median": expected_median,
                            "ratio": ratio,
                            "points_count": len(values_for_check),
                            "sample_values": values_for_check[:5],
                        },
                    )
                else:
                    logger.debug(
                        f"Scale validation OK for {metric}: median {actual_median:.2f} "
                        f"(expected ~{expected_median:.2f}, ratio: {ratio:.2f}x)",
                        extra={"metric": metric, "ratio": ratio},
                    )
    except ImportError:
        pass  # Config not available, skip scale validation


def validate_ebitda_scale(points: list[TimeSeriesPoint], metric: str) -> None:
    """EBITDA-specific scale validation.

    Story 6.26: Checks that EBITDA values are in EUR millions, not line-item breakdowns.

    Args:
        points: Extracted time-series points
        metric: Metric name

    Raises:
        ExtractionError: If EBITDA values are too small (likely wrong data)
    """
    if metric.lower() not in get_ebitda_metrics() or not points:
        return

    avg_value = sum(p.value for p in points if p.value is not None) / len(points)
    # €1M threshold: monthly EBITDA for Secil Group should be €10-20M
    # YTD values in database are in EUR millions (e.g., 139.37 = €139.37M)
    # If avg < 1.0, we're extracting wrong data (line items avg €97)
    if avg_value < 1.0:
        logger.error(
            f"EBITDA scale validation FAILED: avg={avg_value:.2f}, expected EUR millions",
            extra={
                "metric": metric,
                "avg_value": avg_value,
                "points_count": len(points),
                "sample_values": [p.value for p in points[:5]],
            },
        )
        raise ExtractionError(
            f"EBITDA values too small (avg={avg_value:.2f}). Expected EUR millions for Group EBITDA. "
            "Data may be extracting line-item breakdowns instead of consolidated values. "
            "Check that 'ebitda' maps to 'EBITDA IFRS' in METRIC_SYNONYMS."
        )
    else:
        logger.info(
            f"EBITDA scale validation PASSED: avg={avg_value:.2f}M EUR",
            extra={"metric": metric, "avg_value": avg_value},
        )
