"""Forecast MCP tools.

Story 8: Refactored get_financial_forecast from 456 to ~150 lines using forecast_helpers.py.
Multi-geography fix (2026-01-30): Added entity parameter for geography-specific forecasts.

Full documentation for get_financial_forecast:

**Supported Metrics:** Any metric in the financial_tables database (e.g., revenue, turnover,
cash_flow, ebitda, expenses, capex). The system automatically searches the database via SQL
and falls back to hybrid search if needed.

**Multi-Geography Support (2026-01-30):**
Forecast any Secil geography by specifying the `entity` parameter:
- `entity="GROUP"` - Consolidated data (~€200M/year for EBITDA)
- `entity="Portugal"` - Portugal region (~€150M/year for EBITDA)
- `entity="Brazil"` - Brazil region (~€40M/year for EBITDA)
- `entity="Tunisia"` - Tunisia region (~€15M/year for EBITDA)
- `entity="Lebanon"` - Lebanon region
- `entity="Angola"` - Angola region
- `entity=None` (default) - Uses config-based default (GROUP for EBITDA, etc.)

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
   Provide explicit `metric`, `entity`, and `periods_ahead` parameters.
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

import asyncio
from typing import Any

from raglite.forecasting.forecast_job_tracker import (
    create_forecast_job,
    get_forecast_job_status,
    start_background_forecast,
)
from raglite.main import mcp
from raglite.mcp.tools.forecast_helpers import (
    build_enhanced_basis,
    build_response,
    calculate_periods_for_target_year,
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
from raglite.shared.models import (
    AsyncForecastResponse,
    ForecastJobStatus,
    ForecastQueryRequest,
    ForecastQueryResponse,
)

logger = get_logger(__name__)


async def _fetch_regressors_if_requested(
    request: ForecastQueryRequest,
    metric: str,
    historical_data: Any,
    periods_ahead: int,
) -> tuple[Any, list[str]]:
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
    historical_data: Any,
    periods_ahead: int,
    request: ForecastQueryRequest,
    external_regressors: Any,
    regressors_used: list[str],
) -> tuple[Any, str, str, str, list[str]]:
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
    forecast_result: Any,
    historical_data: Any,
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


# Top-level timeout for forecast operations (prevents MCP client timeout)
FORECAST_TIMEOUT_SECONDS = 90.0

# Claude Desktop has ~30s MCP client timeout; use 25s safety margin
MCP_CLIENT_TIMEOUT_SECONDS = 25.0


def _should_use_async(request: ForecastQueryRequest) -> bool:
    """Check if forecast should auto-route to async.

    Ensemble/prefer_accuracy=True takes ~52s, exceeds 30s MCP timeout.
    Prophet only takes ~21s, safe for sync.

    Args:
        request: Forecast query request

    Returns:
        True if forecast should use async path
    """
    if request.prefer_accuracy:
        return True
    if request.model_type and request.model_type.lower() == "ensemble":
        return True
    return False


async def _execute_forecast_internal(
    request: ForecastQueryRequest,
    metric: str,
    periods_ahead: int,
) -> ForecastQueryResponse:
    """Internal forecast execution logic (wrapped with timeout by caller).

    Forecast debug fix (2026-01-28): Added support for target_year parameter.
    When target_year is specified, periods_ahead is dynamically calculated
    after historical data extraction.

    Multi-geography fix (2026-01-30): Added entity parameter threading.

    Args:
        request: Forecast query parameters
        metric: Validated metric name
        periods_ahead: Number of periods to forecast (may be recalculated if target_year set)

    Returns:
        ForecastQueryResponse with forecast results
    """
    historical_data = await extract_historical_data(
        metric, logger, entity=request.entity, entity_level=request.entity_level
    )
    logger.info(
        "Time-series extraction complete",
        extra={"metric": metric, "data_points": len(historical_data.points)},
    )

    # Forecast debug fix: Recalculate periods_ahead if target_year was specified
    if request.target_year is not None:
        periods_ahead = calculate_periods_for_target_year(
            request.target_year, historical_data, logger
        )
        logger.info(
            "Periods ahead recalculated from target_year",
            extra={
                "target_year": request.target_year,
                "final_periods_ahead": periods_ahead,
            },
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


@mcp.tool()
async def get_financial_forecast(
    request: ForecastQueryRequest,
) -> ForecastQueryResponse | AsyncForecastResponse:
    """Query financial forecasts for key metrics using Prophet/Ensemble models.

    See module docstring for full documentation on supported metrics, model selection,
    input modes, and examples.

    Args:
        request: Forecast query parameters (metric, periods_ahead, query, model_type, prefer_accuracy)

    Returns:
        ForecastQueryResponse with forecast, confidence intervals, and model selection details

    Raises:
        QueryError: If metric not supported, no metric specified, or insufficient data
        TimeoutError: If forecast generation exceeds timeout (90 seconds)
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

    # Auto-route to async if forecast would exceed MCP timeout
    if _should_use_async(request):
        logger.info(
            "Auto-routing to async (ensemble/prefer_accuracy detected)",
            extra={"metric": metric, "prefer_accuracy": request.prefer_accuracy},
        )
        return await get_financial_forecast_async.fn(request)  # type: ignore[no-any-return]

    try:
        # Wrap forecast execution with timeout to prevent indefinite hangs
        # This protects against slow DB connections, model loading issues, etc.
        response = await asyncio.wait_for(
            _execute_forecast_internal(request, metric, periods_ahead),
            timeout=FORECAST_TIMEOUT_SECONDS,
        )
        return response

    except TimeoutError:
        logger.warning(
            "Sync forecast timed out, retrying with async",
            extra={
                "metric": metric,
                "periods_ahead": periods_ahead,
                "timeout_seconds": FORECAST_TIMEOUT_SECONDS,
            },
        )
        # Retry with async instead of returning error
        return await get_financial_forecast_async.fn(request)  # type: ignore[no-any-return]

    except Exception as e:
        handle_forecast_error(e, metric, logger)
        raise


# Re-exports for backward compatibility with tests
# These functions were moved to forecast_helpers.py but tests still import them from here
extract_historical_data_by_type = extract_historical_data
generate_forecast = generate_forecast_auto_select
extract_timeseries = extract_historical_data


# =============================================================================
# ASYNC FORECAST TOOLS - MCP Timeout Resolution
# =============================================================================
# Claude Desktop has a 30-second hardcoded MCP client timeout, but forecasts
# take ~50 seconds. These tools enable an async job pattern that returns
# immediately with a job_id for status polling.
# =============================================================================


@mcp.tool()
async def get_financial_forecast_async(
    request: ForecastQueryRequest,
) -> AsyncForecastResponse:
    """Start async forecast generation (returns immediately, poll for results).

    Use this tool when forecast timing is uncertain or when you want to avoid
    MCP timeouts. The forecast runs in the background while you can continue
    other work.

    **When to use this vs get_financial_forecast:**
    - Use `get_financial_forecast_async` when you want immediate response
    - Use `get_financial_forecast_async` if forecasts have been timing out
    - Use `get_financial_forecast` for faster total turnaround (if it works)

    **Workflow:**
    1. Call `get_financial_forecast_async(metric="ebitda", periods_ahead=4)`
    2. Receive job_id immediately
    3. Poll with `get_forecast_status(job_id)` until status="completed"
    4. Retrieve full forecast from the status response

    Args:
        request: Forecast query parameters (same as get_financial_forecast)

    Returns:
        AsyncForecastResponse with job_id to poll for results
    """
    logger.info(
        "Async forecast query received",
        extra={
            "metric": request.metric,
            "periods_ahead": request.periods_ahead,
            "query": request.query,
        },
    )

    # Validate and parse the request
    metric, periods_ahead = parse_and_validate_metric(request, logger)

    # Create job and start background processing
    job_id = create_forecast_job(request, metric, periods_ahead)
    start_background_forecast(job_id, request, metric, periods_ahead)

    message = (
        f"Forecast started for {metric} ({periods_ahead} periods ahead). "
        f"Use get_forecast_status('{job_id}') to check progress. "
        f"Forecasts typically take 40-60 seconds to complete."
    )

    logger.info(
        "Async forecast job initiated",
        extra={
            "job_id": job_id,
            "metric": metric,
            "periods_ahead": periods_ahead,
        },
    )

    return AsyncForecastResponse(
        job_id=job_id,
        status="started",
        message=message,
        metric=metric,
        periods_ahead=periods_ahead,
    )


@mcp.tool()
async def get_forecast_status(job_id: str) -> ForecastJobStatus:
    """Check status of an async forecast job.

    Poll this endpoint to check if a forecast job has completed.
    When status="completed", the result field contains the full forecast.

    **Status values:**
    - `pending`: Job created, not yet started
    - `running`: Forecast generation in progress
    - `completed`: Forecast ready in `result` field
    - `failed`: Error occurred, see `error` field

    **Example:**
    ```
    status = get_forecast_status("abc-123")
    if status.status == "completed":
        forecast = status.result  # Full ForecastQueryResponse
    elif status.status == "failed":
        print(f"Error: {status.error}")
    else:
        print(f"Progress: {status.progress}%")
    ```

    Args:
        job_id: Job identifier from get_financial_forecast_async

    Returns:
        ForecastJobStatus with current status and results (if completed)

    Raises:
        ValueError: If job_id not found (may have expired or server restarted)
    """
    logger.info("Checking forecast job status", extra={"job_id": job_id})

    job_status = get_forecast_job_status(job_id)

    if job_status is None:
        error_msg = f"Forecast job not found: {job_id}. Job may have expired or server restarted."
        logger.warning("Forecast job status check failed - job not found", extra={"job_id": job_id})
        raise ValueError(error_msg)

    logger.info(
        "Forecast job status retrieved",
        extra={
            "job_id": job_id,
            "status": job_status.status,
            "progress": job_status.progress,
            "has_result": job_status.result is not None,
        },
    )

    return job_status
