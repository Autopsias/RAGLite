"""SQL extraction response handling.

Handles validation, finalization, error handling, and Qdrant fallback.
Part of Story 8.1 refactoring to split sql_extraction.py.
"""

from raglite.forecasting.timeseries.metadata import (
    ExtractionError,
    MetricValidationError,
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
)
from raglite.forecasting.timeseries.sql_extraction_validation import (
    validate_ebitda_scale,
    validate_scale_with_config,
)
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

logger = get_logger(__name__)


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


async def try_qdrant_fallback(
    metric: str,
    min_points: int,
) -> TimeSeriesData | None:
    """Attempt Qdrant extraction as fallback.

    Args:
        metric: Metric to extract
        min_points: Minimum required data points

    Returns:
        TimeSeriesData if successful, None otherwise
    """
    try:
        qdrant_result: TimeSeriesData | None
        if metric.lower() == "ebitda":
            qdrant_result = await extract_ebitda_from_qdrant_chunks(
                entity="portugal", min_points=min_points
            )
        elif metric.lower() in ["variable_cost", "variable cost"]:
            qdrant_result = await extract_variable_cost_from_qdrant_chunks(
                entity="portugal", min_points=min_points
            )
        else:
            qdrant_result = await extract_metric_from_qdrant_chunks(
                metric=metric, min_points=min_points, entity="portugal"
            )
        if qdrant_result:
            return qdrant_result
        logger.warning(
            f"Qdrant fallback returned no data for {metric}",
            extra={"metric": metric},
        )
        return None
    except Exception as qdrant_error:
        logger.warning(
            f"Qdrant fallback failed for {metric}",
            extra={"metric": metric, "qdrant_error": str(qdrant_error)},
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
) -> TimeSeriesData:
    """Sort, normalize, validate and create final TimeSeriesData.

    Args:
        points: List of TimeSeriesPoint objects
        metric: Metric name
        is_ytd_data: Whether data is YTD format
        source_documents: Set of source document names

    Returns:
        TimeSeriesData with validated data
    """
    # Sort by date and normalize
    points.sort(key=lambda p: p.date)
    points = normalize_timeseries_data(points, metric, is_ytd_data)

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
        },
    )

    # Validate data quality
    validate_scale_with_config(points, metric)
    validate_ebitda_scale(points, metric)

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
) -> TimeSeriesData:
    """Handle extraction failure with Qdrant fallback.

    Args:
        error: Original exception
        metric: Metric name
        min_points: Minimum required data points

    Returns:
        TimeSeriesData from Qdrant fallback

    Raises:
        Original exception if Qdrant fallback also fails
    """
    if isinstance(error, MetricValidationError):
        logger.warning(
            f"SQL extraction has insufficient {metric} data, trying Qdrant fallback",
            extra={
                "metric": metric,
                "sql_points": error.data_points_found,
                "min_required": error.minimum_required,
            },
        )
    elif isinstance(error, ExtractionError):
        logger.warning(
            f"SQL extraction failed for {metric}, trying Qdrant chunk fallback",
            extra={
                "metric": metric,
                "entity": "portugal",
                "original_error": str(error),
            },
        )

    qdrant_result = await try_qdrant_fallback(metric, min_points)
    if qdrant_result:
        return qdrant_result

    if isinstance(error, ExtractionError):
        logger.error(
            f"Both SQL and Qdrant extraction failed for {metric}",
            extra={"metric": metric, "entity": "portugal", "sql_error": str(error)},
        )
    raise error
