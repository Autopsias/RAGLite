"""Hybrid forecasting - Ensemble forecast generation and explanation.

Part of Story 8.1 refactoring to split hybrid.py.
Story 8: Refactored generate_forecast from 659 to ~150 lines using forecast_helpers.py.

Provides:
- generate_forecast: Main hybrid forecasting entry point combining Prophet + LLM reasoning
- explain_forecast: LLM-powered confidence reasoning
- calculate_accuracy: Cross-validation metrics calculation
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from prophet import Prophet

from raglite.forecasting.hybrid.forecast_helpers import (
    build_explanation_context,
    build_forecast_result,
    calculate_accuracy_and_improvement,
    generate_forecast_points_by_frequency,
    handle_initial_setup,
    prepare_and_fit_prophet_model,
    try_non_prophet_model,
)
from raglite.forecasting.hybrid.preprocessing import (
    ensure_historical_data,
    validate_timeseries_for_forecast,
)
from raglite.forecasting.models.base import MIN_DATA_POINTS
from raglite.forecasting.models.chronos_model import (
    generate_chronos_cold_start_forecast,
)
from raglite.shared.clients import get_mistral_client
from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastResult, TimeSeriesData

# Module-level constants
logger = get_logger(__name__)
MIN_CV_DATA_POINTS = 12  # Minimum points for cross-validation
POSITIVE_ONLY_METRICS = {"ebitda", "revenue", "capacity_utilization", "sales_volume"}

# Story 7b-6: Model selection cache integration
try:
    from raglite.external_data.storage import get_cached_model_selection
except ImportError:
    # Storage module may not be available in some test scenarios
    get_cached_model_selection = None  # type: ignore


async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData | None = None,
    periods_ahead: int = 4,
    external_regressors: dict[str, pd.Series] | None = None,
    frequency: str = "M",
    future_regressor_strategy: str = "constant",
    use_model_selection: bool = True,
) -> ForecastResult:
    """Generate forecast for financial metric using Prophet + LLM.

    Story 4.2 AC1-AC4: Hybrid forecasting with Prophet statistical model
    and Mistral Large for confidence reasoning.
    Story 6.3: Extended with multi-variate forecasting support.
    Story 7b-6: Integrated with model selection cache for automatic optimal model routing.
    Story 8: Refactored from 659 to ~150 lines using forecast_helpers.py.

    Args:
        metric: Metric name (e.g., "revenue", "cash_flow", "expenses")
        historical_data: Time-series data (DEPRECATED - use metric parameter)
        periods_ahead: Number of periods to forecast (default 4 quarters)
        external_regressors: Optional dict of external regressor series
        frequency: Data frequency - 'M' (monthly), 'Q' (quarterly), 'D' (daily)
        future_regressor_strategy: Strategy for future regressor values
        use_model_selection: If True, use cached model selection (default: True)

    Returns:
        ForecastResult with predictions, confidence intervals, and reasoning.

    Raises:
        InsufficientDataError: If <6 data points available
    """
    # Steps 1-2: Initial setup (deprecation, cache check, data loading)
    (
        model_source,
        model_selection_reason,
        selected_model,
        selected_regressors,
        historical_data,
        external_regressors,
        is_multivariate,
    ) = await handle_initial_setup(
        metric,
        historical_data,
        periods_ahead,
        external_regressors,
        use_model_selection,
        get_cached_model_selection,
        ensure_historical_data,
        logger,
        MIN_DATA_POINTS,
    )

    # Historical data should always be loaded at this point
    if historical_data is None:
        raise ValueError(f"Failed to load historical data for {metric}")

    # Cold-start check
    result = await handle_cold_start_scenario(
        metric, historical_data, periods_ahead, logger, MIN_DATA_POINTS
    )
    if result is not None:
        return result

    # Steps 3-4: Try non-Prophet model with fallback
    result, model_source, model_selection_reason, external_regressors = await try_non_prophet_model(
        selected_model,
        selected_regressors,
        external_regressors,
        metric,
        historical_data,
        periods_ahead,
        model_source,
        model_selection_reason,
        explain_forecast,
        logger,
    )
    if result is not None:
        return result

    # Run Prophet forecasting pipeline
    result = await run_prophet_forecasting_pipeline(
        metric=metric,
        historical_data=historical_data,
        external_regressors=external_regressors,
        periods_ahead=periods_ahead,
        frequency=frequency,
        future_regressor_strategy=future_regressor_strategy,
        is_multivariate=is_multivariate,
        model_source=model_source,
        model_selection_reason=model_selection_reason,
        logger=logger,
    )

    logger.info("Forecast generated", extra={"metric": metric, "model_type": result.model_type})
    return result


async def explain_forecast(forecast: ForecastResult, context: str) -> str:
    """Use Mistral Large to explain forecast with context.

    Story 4.2 AC1: LLM reasoning layer for confidence rationale.

    Args:
        forecast: Prophet forecast result
        context: Retrieved document context (trends, events)

    Returns:
        Natural language explanation with confidence rationale
    """
    logger.info("Generating forecast explanation with Mistral Large")

    client = get_mistral_client()

    # Build forecast summary for prompt
    forecast_summary = {
        "metric": forecast.metric_name,
        "periods_ahead": forecast.periods_ahead,
        "historical_points": len(forecast.historical_data),
        "predictions": [
            {
                "period": p.label,
                "value": round(p.value, 2),
                "range": f"{round(p.lower, 2)} - {round(p.upper, 2)}",
            }
            for p in forecast.forecast
        ],
    }

    prompt = f"""You are a financial analyst explaining a forecast to stakeholders.

Forecast Data:
{json.dumps(forecast_summary, indent=2)}

Context:
{context}

Please provide a clear, concise explanation that:
1. Summarizes the forecast values and confidence intervals
2. Explains why confidence intervals are what they are (data quality, trends)
3. Identifies 2-3 key risks
4. Identifies 1-2 opportunities

Format your response as JSON:
{{
    "summary": "2-3 sentence natural language explanation of the forecast",
    "confidence_rationale": "Why confidence intervals are narrow/wide",
    "risks": ["Risk 1", "Risk 2"],
    "opportunities": ["Opportunity 1"]
}}"""

    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        llm_response = response.choices[0].message.content if response.choices else ""

        # Parse JSON response and format as explanation text
        if llm_response:
            # Try to parse as JSON, fall back to raw text
            try:
                parsed = json.loads(llm_response)
                explanation = parsed.get("summary", "")
                if parsed.get("confidence_rationale"):
                    explanation += f" {parsed['confidence_rationale']}"
                return str(explanation)
            except json.JSONDecodeError:
                return llm_response

    except Exception as e:
        logger.warning(f"LLM explanation failed, using fallback: {e}")

    # Fallback explanation if LLM fails
    return (
        f"Forecast based on {len(forecast.historical_data)} historical data points. "
        f"Confidence intervals reflect model uncertainty over {forecast.periods_ahead} periods."
    )


def calculate_accuracy(model: Prophet, df: pd.DataFrame) -> dict[str, float]:
    """Calculate RMSE, MAE, MAPE using Prophet cross-validation.

    Story 6.3 AC5: Accuracy metrics calculation.

    Args:
        model: Fitted Prophet model
        df: Training DataFrame with 'ds' and 'y' columns

    Returns:
        Dictionary with 'rmse', 'mae', 'mape' metrics
    """
    # Only run CV if sufficient data (12+ points)
    if len(df) < MIN_CV_DATA_POINTS:
        logger.warning(
            f"Insufficient data for CV ({len(df)} < {MIN_CV_DATA_POINTS}). Returning zero metrics."
        )
        return {"rmse": 0.0, "mae": 0.0, "mape": 0.0}

    try:
        from prophet.diagnostics import cross_validation, performance_metrics

        # Calculate appropriate CV parameters based on data length
        data_span_days = (df["ds"].max() - df["ds"].min()).days

        # Initial training period: ~60% of data
        initial_days = int(data_span_days * 0.6)
        initial = f"{initial_days} days"

        # Period between cutoffs: ~30 days
        period = "30 days"

        # Horizon: ~90 days (3 months)
        horizon = "90 days"

        cv = cross_validation(model, initial=initial, period=period, horizon=horizon)
        metrics = performance_metrics(cv)

        return {
            "rmse": float(metrics["rmse"].mean()),
            "mae": float(metrics["mae"].mean()),
            "mape": float(metrics["mape"].mean()),
        }

    except Exception as e:
        logger.warning(f"Cross-validation failed: {e}. Returning zero metrics.")
        return {"rmse": 0.0, "mae": 0.0, "mape": 0.0}


def get_baseline_rmse(metric: str) -> float | None:
    """Get Epic 4 baseline RMSE from stored results.

    Story 6.3 AC5: Baseline RMSE lookup for improvement calculation.

    Args:
        metric: Metric name to look up

    Returns:
        Baseline RMSE if available, None otherwise
    """
    # Check environment variable first
    env_key = f"BASELINE_RMSE_{metric.upper()}"
    env_value = os.getenv(env_key)
    if env_value:
        try:
            return float(env_value)
        except ValueError:
            pass

    # Check accuracy tracking log file
    log_path = Path("docs/accuracy-tracking-log.jsonl")
    if log_path.exists():
        try:
            with open(log_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if (
                        entry.get("metric") == metric
                        and entry.get("type") == "baseline"
                        and "rmse" in entry
                    ):
                        return float(entry["rmse"])
        except (json.JSONDecodeError, OSError):
            pass

    return None


async def handle_cold_start_scenario(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    logger,
    min_data_points: int,
) -> ForecastResult | None:
    """Handle cold-start scenario with insufficient data.

    Args:
        metric: Metric name
        historical_data: Time-series data
        periods_ahead: Number of periods to forecast
        logger: Logger instance
        min_data_points: Minimum required data points

    Returns:
        ForecastResult if cold-start detected, None otherwise
    """
    if len(historical_data.points) < min_data_points:
        logger.info("Cold-start detected: routing to Chronos-2", extra={"metric": metric})
        return await generate_chronos_cold_start_forecast(
            metric=metric, historical_data=historical_data, periods_ahead=periods_ahead
        )
    return None


async def attach_llm_explanation(
    result: ForecastResult,
    metric: str,
    historical_data: TimeSeriesData,
    regressors_used: list[str],
) -> ForecastResult:
    """Attach LLM-generated explanation to forecast result.

    Args:
        result: Forecast result without explanation
        metric: Metric name
        historical_data: Historical time-series data
        regressors_used: List of regressors used in forecast

    Returns:
        ForecastResult with confidence_reasoning attached
    """
    context = build_explanation_context(metric, historical_data, regressors_used)
    result.confidence_reasoning = await explain_forecast(result, context)
    return result


async def run_prophet_forecasting_pipeline(
    metric: str,
    historical_data: TimeSeriesData,
    external_regressors: dict[str, pd.Series] | None,
    periods_ahead: int,
    frequency: str,
    future_regressor_strategy: str,
    is_multivariate: bool,
    model_source: str,
    model_selection_reason: str,
    logger,
) -> ForecastResult:
    """Run complete Prophet forecasting pipeline.

    Args:
        metric: Metric name
        historical_data: Time-series data
        external_regressors: Optional external regressors
        periods_ahead: Number of periods to forecast
        frequency: Data frequency
        future_regressor_strategy: Strategy for future regressor values
        is_multivariate: Whether using multivariate model
        model_source: Model source description
        model_selection_reason: Model selection reason
        logger: Logger instance

    Returns:
        ForecastResult with predictions and explanation
    """
    # Step 5: Pre-flight validation
    is_valid, validation_issues = validate_timeseries_for_forecast(
        metric=metric, points=historical_data.points
    )
    if not is_valid:
        logger.warning(f"Validation issues for {metric}: {validation_issues[:3]}")

    # Steps 6-7: Prepare data, configure model, add regressors, and fit
    model, df, regressors_used = prepare_and_fit_prophet_model(
        historical_data, metric, external_regressors, logger
    )

    # Step 8: Generate forecast based on frequency
    forecast_points = generate_forecast_points_by_frequency(
        model,
        df,
        periods_ahead,
        regressors_used,
        external_regressors,
        future_regressor_strategy,
        frequency,
        metric,
        logger,
    )

    # Step 9: Calculate accuracy metrics
    accuracy_metrics, improvement_vs_baseline = calculate_accuracy_and_improvement(
        is_multivariate, model, df, metric, get_baseline_rmse
    )

    # Step 10: Build result
    result = build_forecast_result(
        metric=metric,
        historical_data=historical_data,
        forecast_points=forecast_points,
        periods_ahead=periods_ahead,
        regressors_used=regressors_used,
        accuracy_metrics=accuracy_metrics,
        improvement_vs_baseline=improvement_vs_baseline,
        model_source=model_source,
        model_selection_reason=model_selection_reason,
    )

    # Step 11: Generate LLM explanation
    result = await attach_llm_explanation(result, metric, historical_data, regressors_used)

    return result

