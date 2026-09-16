"""Data preparation for ensemble forecasting.

Extracted from ensemble_helpers.py (Story 8 refactoring).
"""

from __future__ import annotations

from logging import Logger

import numpy as np
import pandas as pd

from raglite.forecasting.models.base import MIN_DATA_POINTS, InsufficientDataError
from raglite.shared.models import TimeSeriesData


def prepare_ensemble_data(
    historical_data: TimeSeriesData,
    external_regressors: dict[str, pd.Series] | None,
    logger: Logger,
    metric: str | None = None,
) -> tuple[pd.DataFrame, pd.Series, list[str], dict[str, pd.Series]]:
    """Prepare data for ensemble forecasting. Returns (X, y, selected, prepared).

    Forecast reliability fix (2026-02-02): Added metric parameter for appropriate
    correlation threshold selection (lower for profit metrics like EBITDA).
    """
    from raglite.forecasting.ensemble import prepare_regressors, select_regressors

    # Validate minimum data requirement
    if len(historical_data.points) < MIN_DATA_POINTS:
        raise InsufficientDataError(
            f"Insufficient data for forecast. Minimum {MIN_DATA_POINTS} data points required. "
            f"Got {len(historical_data.points)}."
        )

    # Prepare DataFrame
    df = pd.DataFrame(
        {
            "ds": [p.date for p in historical_data.points],
            "y": [p.value for p in historical_data.points],
        }
    )

    # Select and prepare regressors
    target_series = pd.Series(df["y"].values, index=pd.DatetimeIndex(df["ds"]))
    selected: list[str] = []
    prepared: dict[str, pd.Series] = {}

    if external_regressors:
        # Forecast reliability fix: Pass metric name for appropriate threshold
        # Note: return_lag_info defaults to False, so this returns list[str]
        result = select_regressors(target_series, external_regressors, metric_name=metric)
        # Type narrowing: result is list[str] when return_lag_info=False (default)
        if isinstance(result, list):
            selected = result
        if selected:
            prepared = prepare_regressors(
                {k: v for k, v in external_regressors.items() if k in selected},
                pd.DatetimeIndex(df["ds"]),
                target_series=target_series,
            )

    # Build feature matrix
    X = pd.DataFrame(prepared) if prepared else pd.DataFrame()
    y = target_series

    return X, y, selected, prepared


def prepare_future_features(X: pd.DataFrame, periods_ahead: int) -> pd.DataFrame | None:
    """Prepare future feature values using constant extrapolation.

    Args:
        X: Feature matrix
        periods_ahead: Number of periods to forecast

    Returns:
        DataFrame with extrapolated features or None if no features
    """
    if len(X.columns) == 0:
        return None
    last_row = X.iloc[-1:].values
    return pd.DataFrame(np.tile(last_row, (periods_ahead, 1)), columns=X.columns)
