"""Forecast MCP tools.

Story 8: Refactored get_financial_forecast from 456 to ~150 lines using forecast_helpers.py.

Full documentation for get_financial_forecast:

**Supported Metrics:** Any metric in the financial_tables database (e.g., revenue, turnover,
cash_flow, ebitda, expenses, capex). The system automatically searches the database via SQL
and falls back to hybrid search if needed.

**Model Selection (Story 6.11.6):**
The tool intelligently selects between Prophet (~21s, fast) and Ensemble (~78s, 4 models) based on:
- **Default (model_type="auto", prefer_accuracy=False):** Uses Prophet for fast response
- **High-accuracy mode (prefer_accuracy=True):** Uses Ensemble (Prophet+Linear+XGBoost+LightGBM)

**WHEN TO SET prefer_accuracy=True:**
Set `prefer_accuracy=True` when the user indicates they want:
- "highly accurate", "most accurate", "best possible" forecast
- "take your time", "don't rush", "thorough analysis"
- "for board presentation", "critical decision", "important forecast"
- "ensemble model", "multiple models", "robust forecast"

**WHEN TO USE DEFAULT (prefer_accuracy=False):**
- Quick questions: "What's the revenue forecast?"
- No urgency indicators mentioned
- User wants fast response

**Input Modes:**
1. **Structured Query (Programmatic):**
   Provide explicit `metric` and `periods_ahead` parameters.
2. **Natural Language Query (Conversational):**
   Provide a `query` parameter and let the system extract parameters.

**How It Works:**
1. Parse query to extract metric and time period (regex + LLM fallback)
2. Extract historical time-series data (Story 5.0.1: SQL-first with fallback)
3. Auto-select model based on metric type and prefer_accuracy flag
4. Generate forecast using selected model + LLM hybrid approach
5. Return predictions with confidence intervals and model selection explanation

**Minimum Data Requirement:**
- Requires 8+ historical data points (2 years quarterly) for reliable forecasts
- Returns clear error message if insufficient data
"""

from raglite.main import mcp
from raglite.mcp.tools.forecast_helpers import (
    build_enhanced_basis,
    build_response,
    check_model_selection_cache_for_forecast,
    extract_historical_data,
    fetch_external_regressors,
    generate_forecast_auto_select,
    generate_forecast_explicit_model,
    generate_forecast_with_cache,
    handle_forecast_error,
    parse_and_validate_metric,
)
from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastQueryRequest, ForecastQueryResponse

logger = get_logger(__name__)


async def _fetch_regressors_if_requested(
    request: ForecastQueryRequest,
    metric: str,
    historical_data,
    periods_ahead: int,
) -> tuple:
    """Fetch external regressors if requested in the query.

    Args:
        request: Forecast query request
        metric: Validated metric name
        historical_data: Historical time-series data
        periods_ahead: Number of periods to forecast

    Returns:
        Tuple of (external_regressors, regressors_used)
    """
    if not request.use_external_regressors:
        return None, []

    return await fetch_external_regressors(
        metric, historical_data, periods_ahead, request.regressor_names, logger
    )


async def _generate_forecast_with_model_selection(
    requested_model_type: str,
    metric: str,
    historical_data,
    periods_ahead: int,
    request: ForecastQueryRequest,
    external_regressors,
    regressors_used: list[str],
) -> tuple:
    """Generate forecast using appropriate model selection strategy.

    Args:
        requested_model_type: Model type requested (auto, prophet, ensemble)
        metric: Validated metric name
        historical_data: Historical time-series data
        periods_ahead: Number of periods to forecast
        request: Original forecast query request
        external_regressors: External regressor data
        regressors_used: List of regressor names used

    Returns:
        Tuple of (forecast_result, actual_model_type, model_selection_reason, model_desc, regressors_used)
    """
    if requested_model_type == "auto":
        cached_selection = check_model_selection_cache_for_forecast(metric, logger)
        if cached_selection is not None:
            (
                forecast_result,
                actual_model_type,
                model_selection_reason,
                regressors_used,
            ) = await generate_forecast_with_cache(
                metric,
                historical_data,
                periods_ahead,
                cached_selection,
                external_regressors,
                logger,
            )
            model_desc = f"{cached_selection.best_model.upper()} (cached)"
        else:
            (
                forecast_result,
                actual_model_type,
                model_selection_reason,
            ) = await generate_forecast_auto_select(
                metric,
                historical_data,
                periods_ahead,
                request.prefer_accuracy,
                external_regressors,
                request.future_regressor_strategy,
                regressors_used,
                logger,
            )
            model_desc = "Ensemble" if actual_model_type == "ensemble" else "Prophet"
    else:
        (
            forecast_result,
            actual_model_type,
            model_selection_reason,
        ) = await generate_forecast_explicit_model(
            metric,
            historical_data,
            periods_ahead,
            requested_model_type,
            external_regressors,
            request.future_regressor_strategy,
            logger,
        )
        model_desc = "Ensemble" if actual_model_type == "ensemble" else "Prophet"

    return forecast_result, actual_model_type, model_selection_reason, model_desc, regressors_used


def _build_forecast_response(
    forecast_result,
    historical_data,
    actual_model_type: str,
    model_desc: str,
    model_selection_reason: str,
    metric: str,
    regressors_used: list[str],
) -> ForecastQueryResponse:
    """Build final forecast response with enhanced basis.

    Args:
        forecast_result: Raw forecast result
        historical_data: Historical time-series data
        actual_model_type: Model type used for forecasting
        model_desc: Human-readable model description
        model_selection_reason: Reason for model selection
        metric: Validated metric name
        regressors_used: List of regressor names used

    Returns:
        Complete forecast query response
    """
    enhanced_basis = build_enhanced_basis(
        actual_model_type,
        model_desc,
        historical_data,
        metric,
        regressors_used,
        forecast_result.ensemble_models,
    )
    forecast_result.basis = enhanced_basis

    return build_response(
        forecast_result=forecast_result,
        historical_data=historical_data,
        actual_model_type=actual_model_type,
        model_selection_reason=model_selection_reason,
        regressors_used=regressors_used,
    )


@mcp.tool()
async def get_financial_forecast(
    request: ForecastQueryRequest,
) -> ForecastQueryResponse:
    """Query financial forecasts for key metrics using Prophet/Ensemble models.

    See module docstring for full documentation on supported metrics, model selection,
    input modes, and examples.

    Args:
        request: Forecast query parameters (metric, periods_ahead, query, model_type, prefer_accuracy)

    Returns:
        ForecastQueryResponse with forecast, confidence intervals, and model selection details

    Raises:
        QueryError: If metric not supported, no metric specified, or insufficient data
    """
    logger.info(
        "Forecast query received",
        extra={
            "metric": request.metric,
            "periods_ahead": request.periods_ahead,
            "query": request.query,
        },
    )

    metric, periods_ahead = parse_and_validate_metric(request, logger)

    try:
        historical_data = await extract_historical_data(metric, logger)
        logger.info(
            "Time-series extraction complete",
            extra={"metric": metric, "data_points": len(historical_data.points)},
        )

        external_regressors, regressors_used = await _fetch_regressors_if_requested(
            request, metric, historical_data, periods_ahead
        )

        requested_model_type = request.model_type or "auto"
        (
            forecast_result,
            actual_model_type,
            model_selection_reason,
            model_desc,
            regressors_used,
        ) = await _generate_forecast_with_model_selection(
            requested_model_type,
            metric,
            historical_data,
            periods_ahead,
            request,
            external_regressors,
            regressors_used,
        )

        logger.info(
            "Forecast generated successfully",
            extra={"metric": metric, "periods": periods_ahead, "model_type": actual_model_type},
        )

        response = _build_forecast_response(
            forecast_result,
            historical_data,
            actual_model_type,
            model_desc,
            model_selection_reason,
            metric,
            regressors_used,
        )

        logger.info(
            "Forecast query complete", extra={"metric": metric, "model_type": actual_model_type}
        )
        return response

    except Exception as e:
        handle_forecast_error(e, metric, logger)
        raise


# Re-exports for backward compatibility with tests
# These functions were moved to forecast_helpers.py but tests still import them from here
extract_historical_data_by_type = extract_historical_data
generate_forecast = generate_forecast_auto_select
extract_timeseries = extract_historical_data
