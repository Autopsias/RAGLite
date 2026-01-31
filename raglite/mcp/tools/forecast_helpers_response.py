"""Response building and error handling helpers for forecast MCP tool.

Story 8: Split from forecast_helpers.py to reduce file size below 500 LOC limit.
"""

from __future__ import annotations

from logging import Logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raglite.shared.models import ForecastQueryResponse, ForecastResult, TimeSeriesData


def build_enhanced_basis(
    model_type: str,
    model_desc: str,
    historical_data: TimeSeriesData,
    metric: str,
    regressors_used: list[str],
    ensemble_models: list[str] | None,
) -> str:
    """Build enhanced basis description.

    Args:
        model_type: Model type used
        model_desc: Model description
        historical_data: Historical time-series data
        metric: Metric name
        regressors_used: List of regressor names used
        ensemble_models: List of ensemble model names (if ensemble)

    Returns:
        Enhanced basis string
    """
    if model_type == "ensemble" and ensemble_models:
        models_used = ", ".join(ensemble_models)
        return (
            f"{model_desc} model ({models_used}) trained on {len(historical_data.points)} "
            f"quarters of historical {metric} data from {len(historical_data.source_documents)} documents"
        )
    elif regressors_used:
        regressors_str = ", ".join(regressors_used)
        return (
            f"{model_desc} model trained on {len(historical_data.points)} quarters of historical "
            f"{metric} data with external regressors ({regressors_str}) from "
            f"{len(historical_data.source_documents)} documents"
        )
    else:
        return (
            f"{model_desc} model trained on {len(historical_data.points)} quarters of historical "
            f"{metric} data from {len(historical_data.source_documents)} documents"
        )


def build_response(
    forecast_result: ForecastResult,
    historical_data: TimeSeriesData,
    actual_model_type: str,
    model_selection_reason: str,
    regressors_used: list[str],
) -> ForecastQueryResponse:
    """Build the final ForecastQueryResponse.

    Forecast debug fix (2026-01-28): Added forecast date range fields to response
    for improved user clarity about forecast horizon.

    Args:
        forecast_result: Generated forecast result
        historical_data: Historical time-series data
        actual_model_type: Model type that was used
        model_selection_reason: Reason for model selection
        regressors_used: List of regressors used

    Returns:
        ForecastQueryResponse with all fields populated
    """
    from raglite.shared.models import ForecastQueryResponse

    # Forecast debug fix: Extract date range information
    last_historical_date = None
    forecast_start_date = None
    forecast_end_date = None

    # Get last historical data point date
    if historical_data.points:
        last_point = max(historical_data.points, key=lambda p: p.date)
        last_historical_date = last_point.date.strftime("%Y-%m-%d")

    # Get forecast date range
    if forecast_result.forecast:
        forecast_dates = sorted([f.date for f in forecast_result.forecast])
        if forecast_dates:
            forecast_start_date = forecast_dates[0].strftime("%Y-%m-%d")
            forecast_end_date = forecast_dates[-1].strftime("%Y-%m-%d")

    response = ForecastQueryResponse.from_forecast_result(
        result=forecast_result,
        source_documents=historical_data.source_documents,
        regressors_used=regressors_used if regressors_used else None,
        model_type=actual_model_type,
        model_selection_reason=model_selection_reason,
    )

    # Add date range fields
    response.last_historical_date = last_historical_date
    response.forecast_start_date = forecast_start_date
    response.forecast_end_date = forecast_end_date

    return response


def handle_forecast_error(e: Exception, metric: str, logger: Logger) -> None:
    """Handle forecast generation errors with appropriate logging and re-raising.

    Args:
        e: Exception that was raised
        metric: Metric name being forecasted
        logger: Logger instance

    Raises:
        QueryError: Transformed error with appropriate message
    """
    from raglite.forecasting.hybrid import InsufficientDataError
    from raglite.forecasting.timeseries import ExtractionError, MetricValidationError
    from raglite.retrieval.search import QueryError

    if isinstance(e, InsufficientDataError):
        error_msg = (
            f"Insufficient historical data for {metric} forecast. "
            f"At least 8 data points (2 years quarterly) are required for reliable predictions."
        )
        logger.warning("Forecast query failed - insufficient data", extra={"metric": metric})
        raise QueryError(error_msg) from e
    elif isinstance(e, MetricValidationError):
        error_msg = f"{str(e)}\n\nAvailable metrics:\n" + "\n".join(
            f"  - {m}" for m in e.available_metrics[:10]
        )
        logger.warning("Forecast query failed - metric validation", extra={"metric": e.metric_name})
        raise QueryError(error_msg) from e
    elif isinstance(e, ExtractionError):
        error_msg = f"Could not extract {metric} time-series data. Details: {str(e)}"
        logger.warning("Forecast query failed - extraction error", extra={"metric": metric})
        raise QueryError(error_msg) from e
    else:
        logger.error(
            "Forecast query failed - unexpected error",
            extra={"metric": metric, "error": str(e)},
            exc_info=True,
        )
        raise QueryError(f"Forecast generation failed: {e}") from e
