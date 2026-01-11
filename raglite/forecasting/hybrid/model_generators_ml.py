"""ML model generators (XGBoost, LightGBM, CatBoost, Linear).

Part of Story 8.1 refactoring - extracted from model_generators.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData

if TYPE_CHECKING:
    pass


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
