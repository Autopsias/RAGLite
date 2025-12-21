"""Utility functions for model selection cross-validation.

Helper functions for fitting individual models during cross-validation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


async def fit_prophet(
    y_train: pd.Series,
    X_train: pd.DataFrame | None,
    horizon: int,
    X_future: pd.DataFrame | None,
) -> np.ndarray:
    """Fit Prophet model and generate predictions."""
    from prophet import Prophet

    # Prepare data for Prophet
    df = pd.DataFrame({"ds": y_train.index, "y": y_train.values})

    # Add regressors if provided
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)

    if X_train is not None:
        for col in X_train.columns:
            model.add_regressor(col)
            df[col] = X_train[col].values

    # Fit model
    model.fit(df)

    # Create future dataframe
    future = model.make_future_dataframe(periods=horizon, freq="MS")

    # Add future regressors
    if X_future is not None:
        for col in X_future.columns:
            # Extend with future values
            future_values = np.concatenate([X_train[col].values, X_future[col].values])  # type: ignore[index] # type: ignore[index]
            future[col] = future_values[: len(future)]

    # Predict
    forecast = model.predict(future)
    predictions = forecast["yhat"].iloc[-horizon:].values

    return predictions  # type: ignore[no-any-return] # type: ignore[no-any-return]


async def fit_ml_model(
    model_name: str,
    y_train: pd.Series,
    X_train: pd.DataFrame | None,
    horizon: int,
    X_future: pd.DataFrame | None,
) -> np.ndarray:
    """Fit ML model (XGBoost, LightGBM, CatBoost, Linear) and generate predictions."""
    # Create lagged features
    n_lags = min(12, len(y_train) // 2)
    X_train_ml = create_lagged_features(y_train, n_lags)

    # Add external regressors if provided
    if X_train is not None:
        X_reg_aligned = X_train.iloc[n_lags:]
        X_train_ml = pd.concat([X_train_ml, X_reg_aligned.reset_index(drop=True)], axis=1)

    y_train_ml = y_train.iloc[n_lags:].values

    # Choose and fit model
    if model_name == "xgboost":
        from xgboost import XGBRegressor

        model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
    elif model_name == "lightgbm":
        from lightgbm import LGBMRegressor

        model = LGBMRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
    elif model_name == "catboost":
        from catboost import CatBoostRegressor

        model = CatBoostRegressor(
            iterations=100, depth=3, learning_rate=0.1, random_seed=42, verbose=0
        )
    elif model_name == "linear":
        from sklearn.linear_model import Ridge

        model = Ridge(alpha=1.0)
    else:
        raise ValueError(f"Unknown ML model: {model_name}")

    model.fit(X_train_ml, y_train_ml)

    # Generate predictions iteratively
    predictions = []
    last_values = y_train.values[-n_lags:].tolist()

    for i in range(horizon):
        X_pred = pd.DataFrame(
            [last_values[-n_lags:]], columns=[f"lag_{j}" for j in range(1, n_lags + 1)]
        )

        if X_future is not None:
            X_pred = pd.concat(
                [X_pred, pd.DataFrame([X_future.iloc[i].values], columns=X_future.columns)], axis=1
            )

        pred = model.predict(X_pred)[0]
        predictions.append(pred)
        last_values.append(pred)

    return np.array(predictions)


def create_lagged_features(y: pd.Series, n_lags: int) -> pd.DataFrame:
    """Create lagged features from time series."""
    lagged = {}
    for i in range(1, n_lags + 1):
        lagged[f"lag_{i}"] = y.shift(i)
    df = pd.DataFrame(lagged)
    return df.iloc[n_lags:]  # Drop rows with NaN


async def fit_chronos(y_train: pd.Series, horizon: int) -> np.ndarray:
    """Fit Chronos-2 model (zero-shot) and generate predictions."""
    from raglite.forecasting.models.chronos_model import generate_chronos_cold_start_forecast
    from raglite.shared.models import TimeSeriesData

    # Convert pd.Series to TimeSeriesData
    time_series_data = TimeSeriesData(  # type: ignore[call-arg]
        timestamps=y_train.index.tolist(), values=y_train.values.tolist()
    )

    # Call with correct signature
    forecast_result = await generate_chronos_cold_start_forecast(
        metric="cv_metric",  # Placeholder metric name for CV
        historical_data=time_series_data,
        periods_ahead=horizon,
    )

    # Extract predictions from ForecastResult
    predictions = [point.predicted_value for point in forecast_result.forecast]  # type: ignore[attr-defined]
    return np.array(predictions)


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Mean Absolute Percentage Error.

    Args:
        y_true: Array of true values
        y_pred: Array of predicted values

    Returns:
        MAPE as a percentage (0-100+)

    Raises:
        ValueError: If arrays have different lengths
    """
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"Length mismatch: y_true has {len(y_true)} values, y_pred has {len(y_pred)} values"
        )

    mask = y_true != 0
    if not mask.any():
        return float("inf")
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    return float(mape)


def calculate_mase(y_train: np.ndarray, y_test: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Mean Absolute Scaled Error."""
    mae_pred = np.mean(np.abs(y_test - y_pred))
    naive_forecast = y_train[:-1]
    naive_actual = y_train[1:]
    mae_naive = np.mean(np.abs(naive_actual - naive_forecast))

    if mae_naive == 0:
        return float("inf") if mae_pred > 0 else 0.0

    return float(mae_pred / mae_naive)
