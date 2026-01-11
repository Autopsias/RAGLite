"""Statistical model generators (ARIMA, ETS).

Part of Story 8.1 refactoring - extracted from model_generators.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from raglite.forecasting.models.arima_model import fit_arima
from raglite.forecasting.models.ets_model import fit_ets
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData

if TYPE_CHECKING:
    pass


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
