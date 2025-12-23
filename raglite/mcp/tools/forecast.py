"""Forecast MCP tools."""

from raglite.external_data.storage import CachedModelSelection, get_cached_model_selection
from raglite.forecasting.extraction_routing import extract_historical_data_by_type
from raglite.forecasting.hybrid import (
    InsufficientDataError,
    _route_to_model,
    generate_ensemble_forecast,
    generate_forecast,
)
from raglite.forecasting.timeseries_extract import (
    ExtractionError,
    MetricValidationError,
    extract_timeseries,
)
from raglite.main import mcp
from raglite.mcp.tools.query import parse_forecast_query
from raglite.retrieval.search import QueryError
from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastQueryRequest, ForecastQueryResponse

logger = get_logger(__name__)


@mcp.tool()
async def get_financial_forecast(
    request: ForecastQueryRequest,
) -> ForecastQueryResponse:
    """Query financial forecasts for key metrics.
    Story 4.4 AC1-AC5: MCP tool for conversational forecast queries using
    Prophet statistical forecasting combined with LLM reasoning.
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
       Example:
           >>> request = ForecastQueryRequest(metric="revenue", periods_ahead=4)
           >>> response = await get_financial_forecast(request)
    2. **Natural Language Query (Conversational):**
       Provide a `query` parameter and let the system extract parameters.
       Example:
           >>> request = ForecastQueryRequest(query="What's the revenue forecast for next quarter?")
           >>> response = await get_financial_forecast(request)
    **How It Works:**
    1. Parse query to extract metric and time period (regex + LLM fallback)
    2. Extract historical time-series data (Story 5.0.1: SQL-first with fallback):
       a. Try SQL extraction from PostgreSQL financial_tables (primary)
       b. Fall back to hybrid search + LLM extraction if SQL fails
    3. Auto-select model based on metric type and prefer_accuracy flag
    4. Generate forecast using selected model + LLM hybrid approach
    5. Return predictions with confidence intervals and model selection explanation
    **Minimum Data Requirement:**
    - Requires 8+ historical data points (2 years quarterly) for reliable forecasts
    - Returns clear error message if insufficient data
    Args:
        request: Forecast query parameters containing:
          - metric: Financial metric to forecast (any metric in database: revenue, turnover, ebitda, cash_flow, expenses, capex, etc.)
          - periods_ahead: Number of quarters to forecast (1-8, default: 4)
          - query: Optional natural language query (parsed for metric/period)
          - model_type: "auto" (intelligent selection), "prophet" (fast), or "ensemble" (slower, 4 models)
          - prefer_accuracy: Set True when user wants highest accuracy (accepts ~3.7x slower execution)
    Returns:
        ForecastQueryResponse containing:
          - metric_name: Name of forecasted metric
          - forecast: List of ForecastPoint with value/lower/upper confidence intervals
          - basis: Description of historical data used (e.g., "Prophet model trained on 12 quarters")
          - confidence_reasoning: LLM explanation of forecast confidence
          - methodology: "Prophet + Mistral Large hybrid forecasting"
          - accuracy_estimate: "±15% (NFR10 target)"
          - source_documents: Documents used for time-series extraction
          - periods_ahead: Number of periods forecasted
          - model_type: Which model was used (prophet_univariate, prophet_multivariate, ensemble)
          - model_selection_reason: Why this model was chosen (helpful for transparency)
    Raises:
        QueryError: If metric not supported, no metric specified, or insufficient data
    Example - Quick Forecast (Default - Prophet):
        >>>
        >>> request = ForecastQueryRequest(metric="revenue", periods_ahead=4)
        >>> response = await get_financial_forecast(request)
        >>> print(response.model_type)
        "prophet_multivariate"
        >>> print(response.model_selection_reason)
        "Prophet selected (faster execution ~21s vs ~78s with comparable accuracy)"
    Example - High-Accuracy Forecast (Ensemble):
        >>>
        >>> request = ForecastQueryRequest(metric="ebitda", periods_ahead=4, prefer_accuracy=True)
        >>> response = await get_financial_forecast(request)
        >>> print(response.model_type)
        "ensemble"
        >>> print(response.model_selection_reason)
        "High-value financial metric with accuracy preference and 3 regressors available"
    Example - Natural Language with Accuracy Intent:
        >>>
        >>> request = ForecastQueryRequest(query="thorough detailed revenue forecast", prefer_accuracy=True)
        >>> response = await get_financial_forecast(request)
        >>>
    """
    logger.info(
        "Forecast query received",
        extra={
            "metric": request.metric,
            "periods_ahead": request.periods_ahead,
            "query": request.query,
        },
    )
    metric = request.metric
    periods_ahead = request.periods_ahead
    if request.query and not metric:
        parsed_metric, parsed_periods = parse_forecast_query(request.query)
        if parsed_metric:
            metric = parsed_metric
        if parsed_periods:
            periods_ahead = parsed_periods
        logger.info(
            "Parsed natural language query",
            extra={
                "original_query": request.query,
                "parsed_metric": metric,
                "parsed_periods": periods_ahead,
            },
        )
    if not metric:
        error_msg = (
            "Could not determine metric to forecast. Please specify a financial metric "
            "(e.g., revenue, turnover, ebitda, cash_flow, expenses, capex) or rephrase your query."
        )
        logger.warning("Forecast query failed - no metric", extra={"query": request.query})
        raise QueryError(error_msg)
    metric = metric.lower()
    try:
        logger.info(
            "Extracting time-series data",
            extra={"metric": metric},
        )
        try:
            logger.info(
                "Attempting type-routed extraction",
                extra={"metric": metric, "method": "type_routed"},
            )
            historical_data = await extract_historical_data_by_type(metric=metric, min_points=6)
            if historical_data is None:
                raise ExtractionError(f"Type-routed extraction returned None for {metric}")
            logger.info(
                "Type-routed extraction successful",
                extra={
                    "metric": metric,
                    "data_points": len(historical_data.points),
                    "method": "type_routed",
                },
            )
        except MetricValidationError:
            raise
        except ExtractionError as e:
            logger.warning(
                "SQL extraction failed, falling back to hybrid search",
                extra={
                    "metric": metric,
                    "reason": str(e),
                    "fallback_method": "hybrid_search",
                },
            )
            historical_data = await extract_timeseries(docs=[], metric=metric)
            logger.info(
                "Hybrid search extraction successful",
                extra={
                    "metric": metric,
                    "data_points": len(historical_data.points),
                    "source_docs": len(historical_data.source_documents),
                    "method": "hybrid_search_fallback",
                },
            )
        logger.info(
            "Time-series extraction complete",
            extra={
                "metric": metric,
                "data_points": len(historical_data.points),
                "source_docs": len(historical_data.source_documents),
            },
        )
        requested_model_type = request.model_type or "auto"
        external_regressors = None
        regressors_used: list[str] = []
        model_selection_reason: str | None = None
        if request.use_external_regressors:
            try:
                from datetime import timedelta

                from raglite.forecasting.regressor_fetch import fetch_regressors_for_metric

                if historical_data.points:
                    historical_dates = [
                        p.date.date() if hasattr(p.date, "date") else p.date
                        for p in historical_data.points
                    ]
                    start_date = min(historical_dates) - timedelta(days=365)
                    end_date = max(historical_dates) + timedelta(days=30 * periods_ahead)
                    external_regressors = await fetch_regressors_for_metric(
                        metric=metric,
                        start_date=start_date,
                        end_date=end_date,
                        regressor_names=request.regressor_names,
                    )
                    regressors_used = list(external_regressors.keys())
                    logger.info(
                        "External regressors fetched",
                        extra={
                            "metric": metric,
                            "regressors": regressors_used,
                            "count": len(regressors_used),
                        },
                    )
            except Exception as e:
                logger.warning(
                    "External regressor fetch failed, falling back to univariate",
                    extra={"metric": metric, "error": str(e)},
                )
                external_regressors = None
                regressors_used = []
        # Story 7b-6: Check model selection cache first for optimal per-variable model
        cached_selection: CachedModelSelection | None = None
        if requested_model_type == "auto":
            try:
                cached_selection = await get_cached_model_selection(metric)
                if cached_selection and not cached_selection.is_expired:
                    logger.info(
                        "Using cached model selection",
                        extra={
                            "metric": metric,
                            "best_model": cached_selection.best_model,
                            "best_mase": cached_selection.best_mase,
                            "use_regressors": cached_selection.use_regressors,
                            "regressor_count": len(cached_selection.regressor_list),
                        },
                    )
                else:
                    cached_selection = None  # Treat expired as cache miss
                    logger.debug(
                        "Model selection cache miss or expired",
                        extra={"metric": metric},
                    )
            except Exception as e:
                logger.warning(
                    "Error checking model selection cache, using fallback",
                    extra={"metric": metric, "error": str(e)},
                )
                cached_selection = None

        # Route based on cache hit or fall back to existing logic
        if cached_selection is not None:
            # Filter regressors to only those in cached selection
            if cached_selection.use_regressors and external_regressors:
                filtered_regressors = {
                    name: series
                    for name, series in external_regressors.items()
                    if name in cached_selection.regressor_list
                }
                regressors_used = list(filtered_regressors.keys())
            else:
                filtered_regressors = None
                regressors_used = []

            model_type = cached_selection.best_model
            mase_str = f"{cached_selection.best_mase:.2f}" if cached_selection.best_mase else "N/A"
            model_selection_reason = f"Cached selection: {model_type} (MASE={mase_str})"

            # Route to selected model
            if model_type == "ensemble":
                forecast_result = await generate_ensemble_forecast(
                    metric=metric,
                    historical_data=historical_data,
                    periods_ahead=periods_ahead,
                    fast_mode=True,
                    external_regressors=filtered_regressors,
                )
                model_desc = "Ensemble (cached)"
                actual_model_type = "ensemble"
            else:
                try:
                    forecast_result = await _route_to_model(
                        model_name=model_type,
                        metric=metric,
                        historical_data=historical_data,
                        periods_ahead=periods_ahead,
                        external_regressors=filtered_regressors,
                    )
                    model_desc = f"{model_type.upper()} (cached)"
                    actual_model_type = model_type
                except Exception as e:
                    # Fallback to Prophet on any error
                    logger.warning(
                        f"Cached model {model_type} failed, falling back to Prophet",
                        extra={"error": str(e), "metric": metric},
                    )
                    forecast_result = await generate_forecast(
                        metric=metric,
                        historical_data=historical_data,
                        periods_ahead=periods_ahead,
                        external_regressors=filtered_regressors,
                        use_model_selection=False,
                    )
                    model_desc = "Prophet (fallback)"
                    actual_model_type = "prophet_fallback"
                    model_selection_reason = f"Fallback from {model_type}: {str(e)}"
        elif requested_model_type == "auto":
            # Cache miss - use existing select_model_type() logic
            from raglite.forecasting.regressor_config import select_model_type

            model_type, model_selection_reason = select_model_type(
                metric=metric,
                prefer_accuracy=request.prefer_accuracy,
                num_regressors=len(regressors_used),
            )
            logger.info(
                "Auto-selected model type (cache miss)",
                extra={
                    "metric": metric,
                    "selected_model": model_type,
                    "reason": model_selection_reason,
                    "prefer_accuracy": request.prefer_accuracy,
                    "num_regressors": len(regressors_used),
                },
            )
            if model_type == "ensemble":
                forecast_result = await generate_ensemble_forecast(
                    metric=metric,
                    historical_data=historical_data,
                    periods_ahead=periods_ahead,
                    fast_mode=True,
                    external_regressors=external_regressors,
                )
                model_desc = "Ensemble"
                actual_model_type = "ensemble"
            else:
                forecast_result = await generate_forecast(
                    metric=metric,
                    historical_data=historical_data,
                    periods_ahead=periods_ahead,
                    external_regressors=external_regressors if external_regressors else None,
                    future_regressor_strategy=request.future_regressor_strategy,
                )
                model_desc = "Prophet Multi-variate" if external_regressors else "Prophet"
                actual_model_type = (
                    "prophet_multivariate" if external_regressors else "prophet_univariate"
                )
        else:
            # User explicitly requested a specific model_type
            model_type = requested_model_type
            model_selection_reason = f"User explicitly requested {model_type}"
            if model_type == "ensemble":
                forecast_result = await generate_ensemble_forecast(
                    metric=metric,
                    historical_data=historical_data,
                    periods_ahead=periods_ahead,
                    fast_mode=True,
                    external_regressors=external_regressors,
                )
                model_desc = "Ensemble"
                actual_model_type = "ensemble"
            else:
                forecast_result = await generate_forecast(
                    metric=metric,
                    historical_data=historical_data,
                    periods_ahead=periods_ahead,
                    external_regressors=external_regressors if external_regressors else None,
                    future_regressor_strategy=request.future_regressor_strategy,
                )
                model_desc = "Prophet Multi-variate" if external_regressors else "Prophet"
                actual_model_type = (
                    "prophet_multivariate" if external_regressors else "prophet_univariate"
                )
        logger.info(
            "Forecast generated successfully",
            extra={
                "metric": metric,
                "periods": periods_ahead,
                "forecast_points": len(forecast_result.forecast),
                "model_type": model_type,
            },
        )
        if model_type == "ensemble" and forecast_result.ensemble_models:
            models_used = ", ".join(forecast_result.ensemble_models)
            enhanced_basis = (
                f"{model_desc} model ({models_used}) trained on {len(historical_data.points)} "
                f"quarters of historical {metric} data from {len(historical_data.source_documents)} documents"
            )
        elif regressors_used:
            regressors_str = ", ".join(regressors_used)
            enhanced_basis = (
                f"{model_desc} model trained on {len(historical_data.points)} quarters of historical "
                f"{metric} data with external regressors ({regressors_str}) from "
                f"{len(historical_data.source_documents)} documents"
            )
        else:
            enhanced_basis = (
                f"{model_desc} model trained on {len(historical_data.points)} quarters of historical "
                f"{metric} data from {len(historical_data.source_documents)} documents"
            )
        forecast_result.basis = enhanced_basis
        response = ForecastQueryResponse.from_forecast_result(
            result=forecast_result,
            source_documents=historical_data.source_documents,
            regressors_used=regressors_used if regressors_used else None,
            model_type=actual_model_type,
            model_selection_reason=model_selection_reason,
        )
        logger.info(
            "Forecast query complete",
            extra={
                "metric": metric,
                "periods": periods_ahead,
                "model_type": actual_model_type,
                "model_selection_reason": model_selection_reason,
                "regressors_used": regressors_used,
                "confidence_reasoning_length": len(response.confidence_reasoning),
            },
        )
        return response
    except InsufficientDataError as e:
        error_msg = (
            f"Insufficient historical data for {metric} forecast. "
            f"At least 8 data points (2 years quarterly) are required for reliable predictions. "
            f"Please ingest more financial documents containing {metric} data."
        )
        logger.warning(
            "Forecast query failed - insufficient data",
            extra={"metric": metric, "error": str(e)},
        )
        raise QueryError(error_msg) from e
    except MetricValidationError as e:
        error_msg = (
            f"{str(e)}\n\n"
            f"Available metrics with ≥8 data points for forecasting:\n"
            + "\n".join(f"  - {m}" for m in e.available_metrics[:10])
        )
        if len(e.available_metrics) > 10:
            error_msg += f"\n  ... and {len(e.available_metrics) - 10} more"
        logger.warning(
            "Forecast query failed - metric validation",
            extra={
                "metric": e.metric_name,
                "data_points_found": e.data_points_found,
                "available_metrics": e.available_metrics[:5],
            },
        )
        raise QueryError(error_msg) from e
    except ExtractionError as e:
        error_msg = f"Could not extract {metric} time-series data. Details: {str(e)}"
        logger.warning(
            "Forecast query failed - extraction error",
            extra={"metric": metric, "error": str(e)},
        )
        raise QueryError(error_msg) from e
    except Exception as e:
        logger.error(
            "Forecast query failed - unexpected error",
            extra={
                "metric": metric,
                "periods": periods_ahead,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise QueryError(f"Forecast generation failed: {e}") from e
