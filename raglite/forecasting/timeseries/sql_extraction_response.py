"""SQL extraction response handling.

Handles validation, finalization, error handling, and Qdrant fallback.
Part of Story 8.1 refactoring to split sql_extraction.py.
"""

from raglite.forecasting.timeseries.metadata import (
    ExtractionError,
    MetricValidationError,
    UnitMixingError,
)
from raglite.forecasting.timeseries.qdrant_ebitda import (
    extract_ebitda_from_qdrant_chunks,
)
from raglite.forecasting.timeseries.qdrant_metric import (
    extract_metric_from_qdrant_chunks,
)
from raglite.forecasting.timeseries.qdrant_variable_cost import (
    extract_variable_cost_from_qdrant_chunks,
)
from raglite.forecasting.timeseries.sql_extraction_normalization import (
    normalize_timeseries_data,
    normalize_timeseries_with_units,
)
from raglite.forecasting.timeseries.sql_extraction_validation import (
    validate_ebitda_scale,
    validate_scale_with_config,
)
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

logger = get_logger(__name__)

# Threshold for detecting unit mixing (kEUR vs EUR M)
UNIT_MIXING_SWING_THRESHOLD = 10.0

# Threshold for REJECTING data due to extreme unit mixing
# Beyond this threshold, data quality is too poor for reliable forecasting
# Phase 3 Quality Fix (2026-01-29): Increased from 30x to 50x
# EBITDA monthly data has legitimate high variance (slow vs strong months)
# The previous threshold was causing false rejections after relaxing the 50M cap
UNIT_MIXING_REJECTION_THRESHOLD = 50.0

# EBITDA-specific threshold - higher due to legitimate business volatility
# EBITDA can swing significantly month-to-month for cyclical businesses
# Fix 2026-01-30: Increased from 100x to 200x - GROUP data shows legitimate 170x swing
# (min ~1.34 M EUR in slow months, max ~229 M EUR in strong months)
# Fix 2026-01-30 (v2): Increased from 200x to 300x - Portugal data has anomalous
# values (960M, 828M in source PDFs) causing 265x swing after YTD conversion.
# These appear to be GROUP-level data incorrectly tagged as Portugal entity.
# TODO: File data quality ticket to investigate source document extraction.
EBITDA_SWING_THRESHOLD = 300.0


def validate_unit_consistency(
    points: list[TimeSeriesPoint], metric: str, reject_on_severe: bool = True
) -> list[str]:
    """Detect unit mixing that indicates data quality issues.

    When data comes from different sources or documents, values may be in
    different units (e.g., kEUR vs EUR millions). This function detects
    when the max/min ratio exceeds a threshold, indicating potential unit mixing.

    Phase 5 enhancement: Rejects data with swing >20x instead of just warning.
    This prevents forecasting with data that has extreme unit mixing.

    Phase 3 Quality Fix (2026-01-29): EBITDA uses a higher threshold (100x)
    due to legitimate business volatility in cyclical industries.

    Args:
        points: List of TimeSeriesPoint objects
        metric: Metric name for logging context
        reject_on_severe: If True, raise UnitMixingError when swing exceeds threshold

    Returns:
        List of warning messages (empty if no issues detected)

    Raises:
        UnitMixingError: When swing exceeds rejection threshold
            and reject_on_severe is True
    """
    issues: list[str] = []
    if len(points) < 2:
        return issues

    values = [p.value for p in points if p.value is not None and p.value != 0]
    if len(values) < 2:
        return issues

    # Check positive values only (negative values have different semantics)
    positive_values = [v for v in values if v > 0]
    if len(positive_values) < 2:
        return issues

    max_val = max(positive_values)
    min_val = min(positive_values)

    swing_ratio = max_val / min_val

    # Phase 3 Quality Fix (2026-01-29): Use EBITDA-specific threshold
    # EBITDA has legitimate high volatility in cyclical industries
    from raglite.forecasting.timeseries.sql_extraction_config import get_ebitda_metrics

    is_ebitda = metric.lower() in get_ebitda_metrics()
    rejection_threshold = EBITDA_SWING_THRESHOLD if is_ebitda else UNIT_MIXING_REJECTION_THRESHOLD

    # REJECT data with swing exceeding threshold
    if reject_on_severe and swing_ratio > rejection_threshold:
        logger.error(
            "Unit mixing too severe - rejecting data for forecasting",
            extra={
                "metric": metric,
                "max_value": max_val,
                "min_value": min_val,
                "swing_ratio": swing_ratio,
                "rejection_threshold": rejection_threshold,
                "is_ebitda": is_ebitda,
            },
        )
        raise UnitMixingError(metric, swing_ratio, max_val, min_val)

    # Warn for moderate unit mixing (10x-20x)
    if swing_ratio > UNIT_MIXING_SWING_THRESHOLD:
        issues.append(
            f"Unit mixing suspected for '{metric}': max={max_val:.1f}, min={min_val:.1f}, "
            f"swing={swing_ratio:.1f}x (threshold={UNIT_MIXING_SWING_THRESHOLD}x). "
            "Check for kEUR vs EUR M mixing in source documents."
        )
        logger.warning(
            "Potential unit mixing detected in time series data",
            extra={
                "metric": metric,
                "max_value": max_val,
                "min_value": min_val,
                "swing_ratio": swing_ratio,
                "threshold": UNIT_MIXING_SWING_THRESHOLD,
            },
        )

    return issues


async def suggest_available_metrics(metric: str, min_points: int) -> None:
    """Raise ExtractionError with suggestions for available metrics.

    Args:
        metric: Metric that was not found
        min_points: Minimum required data points

    Raises:
        ExtractionError: With available metric suggestions
    """
    from raglite.forecasting.metrics import list_available_metrics

    try:
        available_info = await list_available_metrics(min_points=min_points, use_cache=True)
        available_names = [m.name for m in available_info if m.can_forecast]

        raise ExtractionError(
            f"No data found in financial_tables for metric '{metric}'. "
            f"Available metrics: {', '.join(available_names[:5])}"
            + (f" (and {len(available_names) - 5} more)" if len(available_names) > 5 else "")
        )
    except ExtractionError:
        raise
    except Exception:
        raise ExtractionError(
            f"No data found in financial_tables for metric '{metric}' "
            f"with valid period and fiscal_year"
        ) from None


def _get_fallback_entity(metric: str, entity: str | None) -> str:
    """Determine the entity to use for Qdrant fallback.

    Multi-geography fix (2026-01-30): Uses passed entity or defaults based on metric.
    For EBITDA, defaults to "GROUP" for consolidated data (~€200M/year).
    For other metrics, defaults to "portugal" for regional data.

    Args:
        metric: Metric name
        entity: Explicitly requested entity (may be None)

    Returns:
        Entity string to use for Qdrant extraction
    """
    if entity is not None:
        return entity

    # Default entity based on metric type
    if metric.lower() in ["ebitda", "ebitda ifrs"]:
        return "GROUP"  # Consolidated EBITDA ~€200M/year
    return "portugal"  # Regional default for other metrics


async def try_qdrant_fallback(
    metric: str,
    min_points: int,
    entity: str | None = None,
) -> TimeSeriesData | None:
    """Attempt Qdrant extraction as fallback.

    Multi-geography fix (2026-01-30): Added entity parameter to support
    geography-specific Qdrant fallback. Uses passed entity or defaults
    based on metric type.

    Args:
        metric: Metric to extract
        min_points: Minimum required data points
        entity: Optional entity/geography filter (GROUP, Portugal, Brazil, etc.)

    Returns:
        TimeSeriesData if successful, None otherwise
    """
    fallback_entity = _get_fallback_entity(metric, entity)

    try:
        qdrant_result: TimeSeriesData | None
        if metric.lower() == "ebitda":
            qdrant_result = await extract_ebitda_from_qdrant_chunks(
                entity=fallback_entity, min_points=min_points
            )
        elif metric.lower() in ["variable_cost", "variable cost"]:
            qdrant_result = await extract_variable_cost_from_qdrant_chunks(
                entity=fallback_entity, min_points=min_points
            )
        else:
            qdrant_result = await extract_metric_from_qdrant_chunks(
                metric=metric, min_points=min_points, entity=fallback_entity
            )
        if qdrant_result:
            return qdrant_result
        logger.warning(
            f"Qdrant fallback returned no data for {metric}",
            extra={"metric": metric, "entity": fallback_entity},
        )
        return None
    except Exception as qdrant_error:
        logger.warning(
            f"Qdrant fallback failed for {metric}",
            extra={"metric": metric, "entity": fallback_entity, "qdrant_error": str(qdrant_error)},
        )
        return None


async def validate_minimum_points(
    points: list[TimeSeriesPoint],
    metric: str,
    min_points: int,
) -> None:
    """Validate that minimum points threshold is met.

    Args:
        points: List of TimeSeriesPoint objects
        metric: Metric name
        min_points: Minimum required data points

    Raises:
        MetricValidationError: If insufficient points with available metrics
        ExtractionError: If insufficient points and cannot fetch available metrics
    """
    if len(points) < min_points:
        logger.warning(
            "Insufficient SQL data points",
            extra={
                "metric": metric,
                "points_found": len(points),
                "min_required": min_points,
            },
        )

        from raglite.forecasting.metrics import list_available_metrics

        try:
            available_info = await list_available_metrics(min_points=min_points, use_cache=True)
            available_names = [m.name for m in available_info if m.can_forecast]

            raise MetricValidationError(
                metric_name=metric,
                data_points_found=len(points),
                minimum_required=min_points,
                available_metrics=available_names,
            )
        except MetricValidationError:
            raise
        except Exception as metrics_error:
            logger.warning(
                "Could not fetch available metrics for error message",
                extra={"error": str(metrics_error)},
            )
            raise ExtractionError(
                f"Insufficient data: found {len(points)} points, need {min_points} minimum"
            ) from None


def finalize_timeseries(
    points: list[TimeSeriesPoint],
    metric: str,
    is_ytd_data: bool,
    source_documents: set[str],
    units: list[str | None] | None = None,
    config_prefers_ytd: bool = False,
) -> TimeSeriesData:
    """Sort, normalize, validate and create final TimeSeriesData.

    Args:
        points: List of TimeSeriesPoint objects
        metric: Metric name
        is_ytd_data: Whether data is YTD format (from SQL period prefix detection)
        source_documents: Set of source document names
        units: Optional list of unit strings (parallel to points)
        config_prefers_ytd: Whether config specifies this metric stores YTD values.
            Fix 2026-01-30: When True, forces YTD-to-monthly conversion even if
            SQL period strings lack "YTD" prefix. This fixes the EBITDA 6x
            overestimation bug where cumulative YTD values (€203M Dec) were
            treated as monthly values.

    Returns:
        TimeSeriesData with validated data

    Note:
        Phase 2 data quality: If units provided, applies explicit unit-based
        normalization before value-based heuristics.
    """
    # Fix 2026-01-30: Compute effective is_ytd_data
    # If config says prefer_ytd=True, force YTD conversion for EBITDA-type metrics
    # This bridges the gap between config intent and SQL period format detection
    from raglite.forecasting.timeseries.sql_extraction_config import get_ebitda_metrics

    effective_is_ytd = is_ytd_data
    if config_prefers_ytd and not is_ytd_data and metric.lower() in get_ebitda_metrics():
        effective_is_ytd = True
        logger.info(
            "Forcing YTD conversion based on config (prefer_ytd=True)",
            extra={
                "metric": metric,
                "config_prefers_ytd": config_prefers_ytd,
                "sql_detected_ytd": is_ytd_data,
                "effective_is_ytd": effective_is_ytd,
            },
        )

    # Sort by date and normalize
    points.sort(key=lambda p: p.date)

    # Phase 2 data quality: Use unit-aware normalization if units provided
    if units is not None and len(units) == len(points):
        # Sort units to match sorted points (by date)
        point_unit_pairs = sorted(zip(points, units, strict=False), key=lambda x: x[0].date)
        points = [p for p, _ in point_unit_pairs]
        units = [u for _, u in point_unit_pairs]
        points = normalize_timeseries_with_units(points, units, metric, effective_is_ytd)
    else:
        points = normalize_timeseries_data(points, metric, effective_is_ytd)

    # Log success
    min_date = points[0].date.strftime("%Y-%m-%d")
    max_date = points[-1].date.strftime("%Y-%m-%d")
    logger.info(
        "SQL extraction successful",
        extra={
            "metric": metric,
            "points": len(points),
            "date_range": f"{min_date} to {max_date}",
            "is_ytd_data": is_ytd_data,
            "effective_is_ytd": effective_is_ytd,
            "config_prefers_ytd": config_prefers_ytd,
        },
    )

    # Validate data quality
    validate_scale_with_config(points, metric)
    validate_ebitda_scale(points, metric)

    # Check for unit consistency issues (warns but doesn't fail)
    unit_issues = validate_unit_consistency(points, metric)
    if unit_issues:
        for issue in unit_issues:
            logger.warning(issue)

    return TimeSeriesData(
        metric_name=metric,
        points=points,
        interval="monthly",
        source_documents=sorted(source_documents),
    )


async def handle_extraction_failure(
    error: Exception,
    metric: str,
    min_points: int,
    entity: str | None = None,
) -> TimeSeriesData:
    """Handle extraction failure with Qdrant fallback.

    Multi-geography fix (2026-01-30): Added entity parameter to pass to Qdrant fallback.

    Args:
        error: Original exception
        metric: Metric name
        min_points: Minimum required data points
        entity: Optional entity/geography filter for Qdrant fallback

    Returns:
        TimeSeriesData from Qdrant fallback

    Raises:
        Original exception if Qdrant fallback also fails
    """
    fallback_entity = _get_fallback_entity(metric, entity)

    if isinstance(error, MetricValidationError):
        logger.warning(
            f"SQL extraction has insufficient {metric} data, trying Qdrant fallback",
            extra={
                "metric": metric,
                "entity": fallback_entity,
                "sql_points": error.data_points_found,
                "min_required": error.minimum_required,
            },
        )
    elif isinstance(error, ExtractionError):
        logger.warning(
            f"SQL extraction failed for {metric}, trying Qdrant chunk fallback",
            extra={
                "metric": metric,
                "entity": fallback_entity,
                "original_error": str(error),
            },
        )

    qdrant_result = await try_qdrant_fallback(metric, min_points, entity=entity)
    if qdrant_result:
        return qdrant_result

    if isinstance(error, ExtractionError):
        logger.error(
            f"Both SQL and Qdrant extraction failed for {metric}",
            extra={"metric": metric, "entity": fallback_entity, "sql_error": str(error)},
        )
    raise error
