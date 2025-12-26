"""Hybrid forecasting - Individual model forecast generators.

Part of Story 8.1 refactoring to split hybrid.py.

Provides:
- _route_to_model: Route forecast requests to appropriate model
- _generate_*_forecast: Individual model wrappers (ARIMA, ETS, Prophet, XGBoost, etc.)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pandas as pd

if TYPE_CHECKING:
    # Avoid circular import - generate_forecast is in ensemble.py
    pass

from raglite.forecasting.models.arima_model import fit_arima
from raglite.forecasting.models.chronos_model import (
    generate_chronos_cold_start_forecast,
)
from raglite.forecasting.models.ets_model import fit_ets
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData


async def _route_to_model(
    model_name: str,
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Route forecast request to appropriate model function.

    Story 7b-6 AC-7b.6.2: Routes to correct model based on cached selection.

    Args:
        model_name: Name of the model to use (e.g., 'arima', 'prophet', 'xgboost')
        metric: Metric being forecast
        historical_data: Historical time series data
        periods_ahead: Forecast horizon
        external_regressors: Optional external regressors

    Returns:
        ForecastResult from the selected model

    Raises:
        ValueError: If model_name is unknown
    """
    model_routers = {
        "arima": _generate_arima_forecast,
        "ets": _generate_ets_forecast,
        "prophet": _generate_prophet_forecast,
        "xgboost": _generate_xgboost_forecast,
        "lightgbm": _generate_lightgbm_forecast,
        "catboost": _generate_catboost_forecast,
        "chronos": _generate_chronos_forecast,
        "tft": _generate_tft_forecast,
        "linear": _generate_linear_forecast,
    }

    if model_name not in model_routers:
        raise ValueError(f"Unknown model: {model_name}")

    generator = model_routers[model_name]
    return await generator(  # type: ignore[no-any-return,operator]
        metric=metric,
        historical_data=historical_data,
        periods_ahead=periods_ahead,
        external_regressors=external_regressors,
    )


async def _generate_arima_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
    model_source: str = "cached",
) -> ForecastResult:
    """Generate forecast using ARIMA model.

    Story 7b-6 AC-7b.6.2: ARIMA model wrapper.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors
        model_source: Source of model selection ('cached', 'default', 'fallback')

    Returns:
        ForecastResult from ARIMA model
    """

    # Prepare data - ARIMA expects pandas Series
    dates = pd.to_datetime([p.date for p in historical_data.points])
    values = pd.Series([p.value for p in historical_data.points], index=dates)

    # Prepare exogenous variables if provided
    X_train = None
    X_future = None
    if external_regressors:
        # Align regressors to historical dates
        X_train = pd.DataFrame()
        for name, series in external_regressors.items():
            # Fix: Add NaN handling to prevent Ridge/ML model failures
            aligned = series.reindex(dates).interpolate(method="linear").ffill().bfill()
            X_train[name] = aligned

        # Generate future dates for forecast
        last_date = dates[-1]
        freq = "MS" if len(dates) >= 2 else "MS"  # Monthly by default
        pd.date_range(start=last_date, periods=periods_ahead + 1, freq=freq)[1:]

        # Prepare future regressors using last known values (constant strategy)
        X_future = pd.DataFrame()
        for name, series in external_regressors.items():
            last_value = series.iloc[-1] if len(series) > 0 else 0.0
            X_future[name] = [last_value] * periods_ahead

    # Fit ARIMA model
    model, metrics, predictions, conf_int = await fit_arima(
        y_train=values,
        X_train=X_train,
        X_future=X_future,
        forecast_horizon=periods_ahead,
    )

    # Convert predictions to ForecastPoints
    forecast_points = []
    last_date = dates[-1]
    for i in range(periods_ahead):
        # Generate next date
        next_date = last_date + pd.DateOffset(months=i + 1)
        label = next_date.strftime("%b %Y")

        forecast_points.append(
            ForecastPoint(
                date=next_date.to_pydatetime(),
                value=float(predictions[i]),
                lower=float(conf_int[i][0]),
                upper=float(conf_int[i][1]),
                label=label,
            )
        )

    # Build result
    regressors_used = list(external_regressors.keys()) if external_regressors else []
    model_type = "arima_multivariate" if regressors_used else "arima_univariate"
    basis_text = f"ARIMA{metrics['order']} model with {len(historical_data.points)} data points"
    if regressors_used:
        basis_text += f" and {len(regressors_used)} regressors"

    return ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        basis=basis_text,
        accuracy_estimate="±10% (ARIMA model)",
        periods_ahead=periods_ahead,
        model_type=model_type,
        regressors_used=regressors_used,
        model_source=model_source,  # type: ignore[arg-type]
    )


async def _generate_ets_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
    model_source: str = "cached",
) -> ForecastResult:
    """Generate forecast using ETS model.

    Story 7b-6 AC-7b.6.2: ETS model wrapper.
    Note: ETS does not support exogenous regressors.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors (ignored for ETS)
        model_source: Source of model selection ('cached', 'default', 'fallback')

    Returns:
        ForecastResult from ETS model
    """
    # Extract time series data
    dates = pd.to_datetime([p.date for p in historical_data.points])
    values = pd.Series([p.value for p in historical_data.points], index=dates)

    # Fit ETS model
    model, metrics, predictions, conf_int = await fit_ets(
        y_train=values,
        forecast_horizon=periods_ahead,
        frequency="M",
    )

    # Convert predictions to ForecastPoints
    forecast_points = []
    last_date = dates[-1]
    for i in range(periods_ahead):
        # Generate next date
        next_date = last_date + pd.DateOffset(months=i + 1)
        label = next_date.strftime("%b %Y")

        forecast_points.append(
            ForecastPoint(
                date=next_date.to_pydatetime(),
                value=float(predictions[i]),
                lower=float(conf_int[i][0]),
                upper=float(conf_int[i][1]),
                label=label,
            )
        )

    # Build result
    basis_text = f"ETS model with {len(historical_data.points)} data points"

    return ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        basis=basis_text,
        accuracy_estimate="±10% (ETS model)",
        periods_ahead=periods_ahead,
        model_type="ets",
        regressors_used=[],
        model_source=model_source,  # type: ignore[arg-type]
    )


async def _generate_prophet_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using Prophet model.

    Story 7b-6 AC-7b.6.2: Prophet model wrapper.
    This uses the existing generate_forecast logic.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from Prophet model
    """
    # Import at runtime to avoid circular import
    from raglite.forecasting.hybrid.ensemble import generate_forecast

    # Delegate to main Prophet logic with use_model_selection=False to avoid recursion
    return await generate_forecast(
        metric=metric,
        historical_data=historical_data,
        periods_ahead=periods_ahead,
        external_regressors=external_regressors,
        use_model_selection=False,  # Prevent recursion back to _route_to_model
    )


async def _generate_ml_forecast(
    model_name: str,
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
    model_source: str = "cached",
) -> ForecastResult:
    """Generate forecast using ML model (XGBoost, LightGBM, CatBoost, Linear).

    Story 7b-6 AC-7b.6.2: Shared ML model wrapper.

    Args:
        model_name: Name of model ('xgboost', 'lightgbm', 'catboost', 'linear')
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors
        model_source: Source of model selection

    Returns:
        ForecastResult from ML model
    """
    from raglite.forecasting.model_selection_utils import fit_ml_model

    # Prepare data
    dates = pd.to_datetime([p.date for p in historical_data.points])
    values = pd.Series([p.value for p in historical_data.points], index=dates)

    # Prepare regressors if provided
    X_train = None
    X_future = None
    if external_regressors:
        X_train = pd.DataFrame()
        for name, series in external_regressors.items():
            # Fix: Add NaN handling to prevent Ridge/ML model failures
            aligned = series.reindex(dates).interpolate(method="linear").ffill().bfill()
            X_train[name] = aligned

        # Prepare future regressors using last known values
        X_future = pd.DataFrame()
        for name, series in external_regressors.items():
            last_value = series.iloc[-1] if len(series) > 0 else 0.0
            X_future[name] = [last_value] * periods_ahead

    # Fit model and generate predictions
    predictions = await fit_ml_model(
        model_name=model_name,
        y_train=values,
        X_train=X_train,
        horizon=periods_ahead,
        X_future=X_future,
    )

    # Generate confidence intervals (approximate: ±15% for ML models)
    conf_margin = 0.15

    # Convert predictions to ForecastPoints
    forecast_points = []
    last_date = dates[-1]
    for i in range(periods_ahead):
        next_date = last_date + pd.DateOffset(months=i + 1)
        label = next_date.strftime("%b %Y")
        pred_value = float(predictions[i])

        forecast_points.append(
            ForecastPoint(
                date=next_date.to_pydatetime(),
                value=pred_value,
                lower=pred_value * (1 - conf_margin),
                upper=pred_value * (1 + conf_margin),
                label=label,
            )
        )

    # Build result
    regressors_used = list(external_regressors.keys()) if external_regressors else []
    model_type = f"{model_name}_multivariate" if regressors_used else f"{model_name}_univariate"
    basis_text = f"{model_name.upper()} model with {len(historical_data.points)} data points"
    if regressors_used:
        basis_text += f" and {len(regressors_used)} regressors"

    return ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        basis=basis_text,
        accuracy_estimate=f"±15% ({model_name.upper()} model)",
        periods_ahead=periods_ahead,
        model_type=model_type,
        regressors_used=regressors_used,
        model_source=model_source,  # type: ignore[arg-type]
    )


async def _generate_xgboost_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using XGBoost model.

    Story 7b-6 AC-7b.6.2: XGBoost model wrapper.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from XGBoost model
    """
    return await _generate_ml_forecast(
        model_name="xgboost",
        metric=metric,
        historical_data=historical_data,
        periods_ahead=periods_ahead,
        external_regressors=external_regressors,
    )


async def _generate_lightgbm_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using LightGBM model.

    Story 7b-6 AC-7b.6.2: LightGBM model wrapper.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from LightGBM model
    """
    return await _generate_ml_forecast(
        model_name="lightgbm",
        metric=metric,
        historical_data=historical_data,
        periods_ahead=periods_ahead,
        external_regressors=external_regressors,
    )


async def _generate_catboost_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using CatBoost model.

    Story 7b-6 AC-7b.6.2: CatBoost model wrapper.

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from CatBoost model
    """
    return await _generate_ml_forecast(
        model_name="catboost",
        metric=metric,
        historical_data=historical_data,
        periods_ahead=periods_ahead,
        external_regressors=external_regressors,
    )


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

    from raglite.forecasting.models.tft_model import fit_and_forecast_tft

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

    # TFT is synchronous, run in executor to avoid blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: fit_and_forecast_tft(
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


async def _generate_linear_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int,
    external_regressors: dict[str, pd.Series] | None,
) -> ForecastResult:
    """Generate forecast using Linear Regression model.

    Story 7b-6 AC-7b.6.2: Linear model wrapper (Ridge/Lasso).

    Args:
        metric: Metric name
        historical_data: Historical data
        periods_ahead: Forecast horizon
        external_regressors: Optional regressors

    Returns:
        ForecastResult from Linear model
    """
    return await _generate_ml_forecast(
        model_name="linear",
        metric=metric,
        historical_data=historical_data,
        periods_ahead=periods_ahead,
        external_regressors=external_regressors,
    )
