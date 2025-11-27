"""Forecasting Agent for agentic workflows.

Story 4.2 AC5: Integrates forecasting capabilities into agentic framework,
enabling orchestrator to invoke forecasting for multi-step workflows.

NOTE: Strands import is optional - use no-op decorator if not available.
"""

import json
import time

try:
    from strands import tool
except ImportError:
    # Strands not installed - use no-op decorator
    def tool(func):  # type: ignore
        """No-op tool decorator when strands is not available."""
        return func


from raglite.forecasting.hybrid import (
    InsufficientDataError,
    generate_forecast,
)
from raglite.forecasting.timeseries_extract import (
    ExtractionError,
    extract_timeseries,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@tool
async def forecasting_agent(instruction: str, context: dict | None = None) -> str:
    """Forecasting Agent: Generate financial forecasts with confidence intervals.

    Story 4.2 AC5: Wraps Stories 4.1-4.2 forecasting pipeline to enable
    agentic workflows to generate financial forecasts.

    Uses AWS Strands @tool decorator for agent coordination.
    Returns JSON-serialized ForecastResult with predictions and reasoning.

    Args:
        instruction: Task instruction containing the metric and documents
        context: Optional context data from previous agents (may contain docs or time-series)

    Returns:
        JSON string containing:
        {
            "metric_name": Metric being forecasted,
            "forecast": [
                {"date": "2025-01-01", "value": 1500000, "lower": 1400000, "upper": 1600000, "label": "Q1 2025"},
                ...
            ],
            "confidence_reasoning": LLM-generated explanation,
            "basis": Forecast basis description,
            "accuracy_estimate": Expected accuracy,
            "periods_ahead": Number of periods forecasted,
            "metadata": {
                "latency_ms": Execution time,
                "success": True/False,
                "data_points": Number of historical points used
            }
        }

    Error Handling:
        If extraction or forecasting fails, returns JSON with:
        {
            "metric_name": Requested metric,
            "forecast": [],
            "confidence_reasoning": "",
            "metadata": {
                "success": False,
                "error": Error description
            }
        }
    """
    start_time = time.time()
    error_msg = None

    # Parse instruction to extract metric and document list
    metric = "revenue"  # Default metric
    docs: list[str] = []

    # Check context for parameters
    if context and isinstance(context, dict):
        metric = context.get("metric", "revenue")
        docs = context.get("documents", [])
        periods_ahead = context.get("periods_ahead", 4)
    else:
        periods_ahead = 4

    # Try to parse metric from instruction if not in context
    instruction_lower = instruction.lower()
    if "cash flow" in instruction_lower or "cash_flow" in instruction_lower:
        metric = "cash_flow"
    elif "expense" in instruction_lower:
        metric = "expenses"
    elif "ebitda" in instruction_lower:
        metric = "ebitda"

    try:
        logger.info(
            "Forecasting agent starting",
            extra={"metric": metric, "docs": docs, "periods_ahead": periods_ahead},
        )

        # Step 1: Extract time-series data (Story 4.1)
        time_series_data = await extract_timeseries(docs=docs, metric=metric)

        # Step 2: Generate forecast (Story 4.2)
        forecast_result = await generate_forecast(
            metric=metric,
            historical_data=time_series_data,
            periods_ahead=periods_ahead,
        )

        # Compute latency before building response
        latency_ms = round((time.time() - start_time) * 1000, 2)

        # Build successful response
        response = {
            "metric_name": forecast_result.metric_name,
            "forecast": [
                {
                    "date": p.date.isoformat(),
                    "value": round(p.value, 2),
                    "lower": round(p.lower, 2),
                    "upper": round(p.upper, 2),
                    "label": p.label,
                }
                for p in forecast_result.forecast
            ],
            "confidence_reasoning": forecast_result.confidence_reasoning,
            "basis": forecast_result.basis,
            "accuracy_estimate": forecast_result.accuracy_estimate,
            "periods_ahead": forecast_result.periods_ahead,
            "metadata": {
                "success": True,
                "latency_ms": latency_ms,
                "data_points": len(forecast_result.historical_data),
            },
        }

        logger.info(
            "Forecasting agent complete",
            extra={
                "metric": metric,
                "forecast_points": len(forecast_result.forecast),
                "latency_ms": latency_ms,
            },
        )

        return json.dumps(response)

    except InsufficientDataError as e:
        error_msg = f"Insufficient data: {str(e)}"
        logger.warning(
            "Forecasting agent - insufficient data",
            extra={"metric": metric, "error": error_msg},
        )

    except ExtractionError as e:
        error_msg = f"Time-series extraction failed: {str(e)}"
        logger.error(
            "Forecasting agent - extraction error",
            extra={"metric": metric, "error": error_msg},
            exc_info=True,
        )

    except Exception as e:
        error_msg = f"Forecasting agent error: {str(e)}"
        logger.error(
            "Forecasting agent - unexpected error",
            extra={"metric": metric, "error": error_msg},
            exc_info=True,
        )

    # Return error response
    latency_ms = round((time.time() - start_time) * 1000, 2)
    error_response = {
        "metric_name": metric,
        "forecast": [],
        "confidence_reasoning": "",
        "basis": "",
        "accuracy_estimate": "",
        "periods_ahead": periods_ahead,
        "metadata": {
            "success": False,
            "latency_ms": latency_ms,
            "error": error_msg,
            "data_points": 0,
        },
    }

    return json.dumps(error_response)
