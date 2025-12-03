"""Hybrid forecasting engine combining Prophet statistical + LLM reasoning.

Story 4.2: Forecasting Engine Implementation.
Target: ~100 lines per architecture spec.

PERFORMANCE FIX (2025-11-29): Prophet import is lazy-loaded to avoid
50-60s cold start penalty during pytest collection. Prophet is only
imported when generate_forecast() is actually called.
"""

import json
from typing import TYPE_CHECKING, cast

import pandas as pd

if TYPE_CHECKING:
    from prophet import Prophet

from raglite.shared.clients import get_mistral_client

# Lazy-load Prophet to avoid import-time penalty during test collection
# Prophet takes 3-5s to import due to Stan backend dependencies
_prophet_class = None


def _get_prophet_class() -> "type[Prophet]":
    """Lazy-load Prophet class on first use.

    Returns:
        Prophet class from prophet library
    """
    global _prophet_class
    if _prophet_class is None:
        from prophet import Prophet

        _prophet_class = Prophet
    return cast("type[Prophet]", _prophet_class)


from raglite.shared.logging import get_logger
from raglite.shared.models import (
    ForecastPoint,
    ForecastResult,
    TimeSeriesData,
)

logger = get_logger(__name__)

# Minimum data points required for reliable forecasting
# FIX (2025-12-01): Lowered from 8 to 6 to allow GROUP-level SQL data
# with occasional missing months (e.g., 7 months Feb-Sep missing June)
# Prophet can produce reasonable forecasts with 6+ monthly data points
MIN_DATA_POINTS = 6


class InsufficientDataError(Exception):
    """Exception raised when insufficient data for forecasting."""

    pass


async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int = 4,
) -> ForecastResult:
    """Generate forecast for financial metric using Prophet + LLM.

    Story 4.2 AC1-AC4: Hybrid forecasting with Prophet statistical model
    and Mistral Large for confidence reasoning.

    Args:
        metric: Metric name (e.g., "revenue", "cash_flow", "expenses")
        historical_data: Time-series data from Story 4.1 extraction
        periods_ahead: Number of periods to forecast (default 4 quarters)

    Returns:
        ForecastResult with predictions, confidence intervals, and reasoning

    Raises:
        InsufficientDataError: If <8 data points available (NFR10 requirement)
    """
    logger.info(
        "Generating forecast",
        extra={
            "metric": metric,
            "data_points": len(historical_data.points),
            "periods": periods_ahead,
        },
    )

    # Validate minimum data requirement (AC4: 8+ quarters for ±15% accuracy)
    if len(historical_data.points) < MIN_DATA_POINTS:
        raise InsufficientDataError(
            f"Insufficient data for forecast. Minimum {MIN_DATA_POINTS} data points required "
            f"for reliable predictions. Got {len(historical_data.points)}."
        )

    # Step 1: Prepare DataFrame for Prophet (requires 'ds' and 'y' columns)
    df = pd.DataFrame(
        {
            "ds": [p.date for p in historical_data.points],
            "y": [p.value for p in historical_data.points],
        }
    )

    # Step 2: Configure Prophet based on data availability
    # CRITICAL: Only enable yearly seasonality if we have 12+ months of data.
    # With less data, Prophet hallucinates seasonal patterns causing negative forecasts.
    data_span_days = (df["ds"].max() - df["ds"].min()).days
    has_full_year_data = data_span_days >= 335  # ~11 months minimum for yearly seasonality

    # For short data spans, use simpler model (trend only)
    Prophet = _get_prophet_class()  # Lazy-load Prophet on first use
    model = Prophet(
        yearly_seasonality=has_full_year_data,  # Only if we have 12+ months
        weekly_seasonality=False,  # Financial data is quarterly/monthly, not weekly
        daily_seasonality=False,
        changepoint_prior_scale=0.05
        if not has_full_year_data
        else 0.2,  # More conservative for short data
        interval_width=0.95,
        uncertainty_samples=1000,
    )

    logger.info(
        "Prophet configured",
        extra={
            "data_points": len(df),
            "data_span_days": data_span_days,
            "yearly_seasonality": has_full_year_data,
            "changepoint_prior_scale": 0.05 if not has_full_year_data else 0.2,
        },
    )

    # Step 3: Fit model and generate forecast
    # CRITICAL FIX: Prophet must forecast at the same frequency as input data.
    # If input is monthly, forecast monthly then aggregate to quarterly.
    model.fit(df)

    # Determine input data frequency
    if len(df) >= 2:
        date_diff = (df["ds"].iloc[1] - df["ds"].iloc[0]).days
        is_monthly_data = 25 <= date_diff <= 35
    else:
        is_monthly_data = False

    if is_monthly_data:
        # Monthly input: forecast monthly for 12 months (covers 4 quarters), then aggregate
        monthly_periods = periods_ahead * 3  # 3 months per quarter
        future = model.make_future_dataframe(periods=monthly_periods, freq="ME")
        prophet_forecast = model.predict(future)

        # Get only the future monthly predictions (not historical)
        forecast_months = prophet_forecast.tail(monthly_periods)

        # Aggregate monthly forecasts into quarterly
        forecast_points = []
        for q_idx in range(periods_ahead):
            # Get 3 months for this quarter
            start_idx = q_idx * 3
            end_idx = start_idx + 3
            quarter_months = forecast_months.iloc[start_idx:end_idx]

            # Sum monthly values to get quarterly total
            quarterly_value = quarter_months["yhat"].sum()
            quarterly_lower = quarter_months["yhat_lower"].sum()
            quarterly_upper = quarter_months["yhat_upper"].sum()

            # Use the last month's date as the quarter-end date
            quarter_end_date = quarter_months.iloc[-1]["ds"]
            quarter = (quarter_end_date.month - 1) // 3 + 1
            label = f"Q{quarter} {quarter_end_date.year}"

            forecast_points.append(
                ForecastPoint(
                    date=quarter_end_date.to_pydatetime(),
                    value=quarterly_value,
                    lower=quarterly_lower,
                    upper=quarterly_upper,
                    label=label,
                )
            )

            logger.debug(
                f"Quarterly aggregation: {label} = sum of 3 monthly forecasts",
                extra={
                    "quarter": label,
                    "monthly_values": quarter_months["yhat"].tolist(),
                    "quarterly_total": quarterly_value,
                },
            )
    else:
        # Non-monthly input: use original quarterly forecast
        future = model.make_future_dataframe(periods=periods_ahead, freq="QE")
        prophet_forecast = model.predict(future)

        # Step 4: Extract forecast points (only the predicted periods, not historical)
        forecast_points = []
        forecast_rows = prophet_forecast.tail(periods_ahead)

        for _, row in forecast_rows.iterrows():
            # Generate quarter label
            quarter = (row["ds"].month - 1) // 3 + 1
            label = f"Q{quarter} {row['ds'].year}"

            forecast_points.append(
                ForecastPoint(
                    date=row["ds"].to_pydatetime(),
                    value=row["yhat"],
                    lower=row["yhat_lower"],
                    upper=row["yhat_upper"],
                    label=label,
                )
            )

    # Step 5: Build initial ForecastResult
    result = ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        basis=f"Prophet model trained on {len(historical_data.points)} data points",
        accuracy_estimate="±15% (NFR10 target)",
        periods_ahead=periods_ahead,
    )

    # Step 6: Generate LLM explanation for confidence reasoning
    context = f"Historical {metric} data from {len(historical_data.source_documents)} documents"
    explanation = await explain_forecast(result, context)
    result.confidence_reasoning = explanation

    logger.info(
        "Forecast generated",
        extra={"metric": metric, "forecast_points": len(forecast_points)},
    )

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
