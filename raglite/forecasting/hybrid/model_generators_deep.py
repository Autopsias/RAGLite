"""Deep learning model generators (Chronos, TFT).

Part of Story 8.1 refactoring - extracted from model_generators.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pandas as pd

from raglite.forecasting.models.chronos_model import (
    generate_chronos_cold_start_forecast,
)
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData

if TYPE_CHECKING:
    pass


async def _generate_chronos_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using Chronos model.

    Story 7b-6 AC-7b.6.2: Chronos model wrapper.
    Chronos-2 is a zero-shot foundation model that doesn't use external regressors.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Ignored (Chronos doesn't support regressors)

    Returns:
        ForecastResult from Chronos model
    """
    # Chronos-2 is a zero-shot model - external_regressors are not used
    # Delegate to the existing cold-start forecast function
    return await generate_chronos_cold_start_forecast(
        metric=metric,
        historical_data=historical_data,
        periods_ahead=periods_ahead,
    )


async def _generate_tft_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
    model_source: Literal["cached", "default", "fallback"] = "cached",
) -> ForecastResult:
    """Generate forecast using TFT (Temporal Fusion Transformer) model.

    Story 7b-6 AC-7b.6.2: TFT model wrapper.
    TFT requires a pre-trained checkpoint from offline training.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors (TFT uses them during training)
        model_source: Source indicator (cached, fallback)

    Returns:
        ForecastResult from TFT model

    Raises:
        ValueError: If no TFT checkpoint available
    """
    import asyncio

    from raglite.forecasting.models.tft_model import (
        _get_tft_model_with_timeout,
        fit_and_forecast_tft_with_model,
    )

    # Load TFT model with async timeout to avoid blocking event loop
    # This wraps sync DB access in an executor with timeout protection
    model = await _get_tft_model_with_timeout(timeout=15.0)
    if model is None:
        raise ValueError(
            f"TFT forecast failed for {metric}: no checkpoint available or loading timed out. "
            "Run offline TFT training first."
        )

    # Convert TimeSeriesData to pandas Series
    dates = pd.to_datetime([p.date for p in historical_data.points])
    values = pd.Series([p.value for p in historical_data.points], index=dates)

    # Prepare external regressors DataFrame if provided
    X_regressors: pd.DataFrame | None = None
    if external_regressors:
        X_regressors = pd.DataFrame()
        for name, series in external_regressors.items():
            # Fix: Add NaN handling to prevent model failures
            aligned = series.reindex(dates).interpolate(method="linear").ffill().bfill()
            X_regressors[name] = aligned

    # TFT inference is synchronous, run in executor to avoid blocking
    # Model is already loaded, so this should be fast
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: fit_and_forecast_tft_with_model(
            model=model,
            y=values,
            periods_ahead=periods_ahead,
            external_regressors=X_regressors,
        ),
    )

    # Handle case when no checkpoint available
    if result is None:
        raise ValueError(
            f"TFT forecast failed for {metric}: no checkpoint available. "
            "Run offline TFT training first."
        )

    # Extract predictions
    predictions = result["values"]

    # Build ForecastResult
    conf_margin = 0.15  # TFT doesn't output confidence by default
    forecast_points: list[ForecastPoint] = []
    last_date = dates[-1]

    for i in range(periods_ahead):
        next_date = last_date + pd.DateOffset(months=i + 1)
        label = next_date.strftime("%b %Y")
        pred_value = float(predictions[i]) if i < len(predictions) else float(predictions[-1])
        forecast_points.append(
            ForecastPoint(
                date=next_date.to_pydatetime(),
                value=pred_value,
                lower=pred_value * (1 - conf_margin),
                upper=pred_value * (1 + conf_margin),
                label=label,
            )
        )

    regressors_used = list(external_regressors.keys()) if external_regressors else []
    model_type = "tft_multivariate" if regressors_used else "tft_univariate"
    basis_text = f"TFT (Temporal Fusion Transformer) with {len(historical_data.points)} data points"

    return ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        basis=basis_text,
        accuracy_estimate="±15% (TFT deep learning model)",
        periods_ahead=periods_ahead,
        model_type=model_type,
        regressors_used=regressors_used,
        model_source=model_source,
    )
