"""Hybrid forecasting - Individual model forecast generators.

Part of Story 8.1 refactoring to split hybrid.py.

Provides:
- _route_to_model: Route forecast requests to appropriate model
- _generate_*_forecast: Individual model wrappers (ARIMA, ETS, Prophet, XGBoost, etc.)

This module has been refactored to split model generators into domain-specific files:
- model_generators_statistical.py: ARIMA, ETS
- model_generators_ml.py: XGBoost, LightGBM, CatBoost, Linear
- model_generators_deep.py: Chronos, TFT

All functions are re-exported from this facade for backward compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

# Re-export deep learning models
from raglite.forecasting.hybrid.model_generators_deep import (
    _generate_chronos_forecast,
    _generate_tft_forecast,
)

# Re-export ML models
from raglite.forecasting.hybrid.model_generators_ml import (
    _generate_catboost_forecast,
    _generate_lightgbm_forecast,
    _generate_linear_forecast,
    _generate_xgboost_forecast,
)

# Re-export statistical models
from raglite.forecasting.hybrid.model_generators_statistical import (
    _generate_arima_forecast,
    _generate_ets_forecast,
)
from raglite.shared.models import ForecastResult, TimeSeriesData

if TYPE_CHECKING:
    # Avoid circular import - generate_forecast is in ensemble.py
    pass


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


__all__ = [
    "_route_to_model",
    "_generate_arima_forecast",
    "_generate_ets_forecast",
    "_generate_prophet_forecast",
    "_generate_xgboost_forecast",
    "_generate_lightgbm_forecast",
    "_generate_catboost_forecast",
    "_generate_chronos_forecast",
    "_generate_tft_forecast",
    "_generate_linear_forecast",
]
