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
    y_train_ml = y_train.iloc[n_lags:].values

    # Add external regressors if provided (must match lagged feature length)
    if X_train is not None and len(X_train) == len(y_train):
        X_reg_aligned = X_train.iloc[n_lags:].reset_index(drop=True)
        # Ensure lengths match before concat
        if len(X_reg_aligned) == len(X_train_ml):
            X_train_ml = pd.concat([X_train_ml.reset_index(drop=True), X_reg_aligned], axis=1)
        else:
            # Skip regressors if alignment fails
            pass

    # Choose and fit model
    if model_name == "xgboost":
        from xgboost import XGBRegressor

        model = XGBRegressor(
            n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42, verbosity=0
        )
    elif model_name == "lightgbm":
        from lightgbm import LGBMRegressor

        model = LGBMRegressor(
            n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42, verbosity=-1
        )
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
            # Fix: Bounds check to prevent IndexError when horizon > len(X_future)
            if i < len(X_future):
                X_pred = pd.concat(
                    [X_pred, pd.DataFrame([X_future.iloc[i].values], columns=X_future.columns)],
                    axis=1,
                )
            else:
                # Use last available row if beyond X_future length
                X_pred = pd.concat(
                    [X_pred, pd.DataFrame([X_future.iloc[-1].values], columns=X_future.columns)],
                    axis=1,
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
    """Fit Chronos-2 model (zero-shot) and generate predictions.

    Uses ProcessPoolExecutor to avoid GIL deadlocks with PyTorch.
    Note: Chronos-2 inference typically takes 3-10 seconds per call.
    """
    import asyncio
    from concurrent.futures import ProcessPoolExecutor

    try:
        # Use ProcessPoolExecutor to run in a separate process (avoids GIL)
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(
                executor,
                _run_chronos_inference,
                y_train.index.tolist(),
                y_train.values.tolist(),
                horizon,
            )
    except Exception:
        return np.full(horizon, np.nan)

    # Handle case when Chronos fails
    if result is None:
        return np.full(horizon, np.nan)

    predictions = result["values"]

    # Pad if needed
    if len(predictions) < horizon:
        predictions = predictions + [predictions[-1]] * (horizon - len(predictions))

    return np.array(predictions[:horizon])


def _run_chronos_inference(dates: list, values: list, horizon: int) -> dict | None:
    """Run Chronos inference in a subprocess (to avoid GIL issues)."""
    import pandas as pd

    from raglite.forecasting.models.chronos_model import fit_and_forecast_chronos

    # Reconstruct the Series in the subprocess
    y = pd.Series(values, index=pd.DatetimeIndex(dates))

    return fit_and_forecast_chronos(
        y=y,
        periods_ahead=horizon,
        external_regressors=None,
    )


async def fit_tft(
    y_train: pd.Series,
    horizon: int,
    external_regressors: dict[str, pd.Series] | None = None,
) -> np.ndarray:
    """Fit TFT model using pre-trained checkpoint and generate predictions.

    TFT requires offline training - uses cached checkpoint for inference.
    If no checkpoint available, returns array of NaN (model will be skipped).
    Uses ProcessPoolExecutor to avoid GIL deadlocks with PyTorch.
    Note: TFT inference typically takes 5-10 seconds per call.

    Args:
        y_train: Training time series
        horizon: Forecast horizon
        external_regressors: Optional dict of regressor name -> Series

    Returns:
        Array of predictions, or NaN array if no checkpoint available
    """
    import asyncio
    from concurrent.futures import ProcessPoolExecutor

    # TFT requires encoder_length + prediction_length data points
    # Encoder needs 12 points, plus we need horizon points for prediction
    # Fix #4: Add +1 to match tft_model.py requirement (encoder + horizon + 1)
    min_encoder_length = 12
    min_required = min_encoder_length + horizon + 1
    if len(y_train) < min_required:
        return np.full(horizon, np.nan)

    # Serialize regressors for subprocess (convert Series to dict of lists)
    regressors_data: dict[str, dict[str, list]] | None = None
    if external_regressors:
        regressors_data = {}
        for name, series in external_regressors.items():
            regressors_data[name] = {
                "dates": [
                    d.isoformat() if hasattr(d, "isoformat") else str(d) for d in series.index
                ],
                "values": series.values.tolist(),
            }

    try:
        # Use ProcessPoolExecutor to run in a separate process (avoids GIL)
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(
                executor,
                _run_tft_inference,
                y_train.index.tolist(),
                y_train.values.tolist(),
                horizon,
                regressors_data,
            )
    except Exception:
        return np.full(horizon, np.nan)

    # Handle case when no checkpoint available
    if result is None:
        return np.full(horizon, np.nan)

    predictions = result["values"]

    # Pad if needed
    if len(predictions) < horizon:
        predictions = predictions + [predictions[-1]] * (horizon - len(predictions))

    return np.array(predictions[:horizon])


def _run_tft_inference(
    dates: list,
    values: list,
    horizon: int,
    regressors_data: dict[str, dict] | None = None,
) -> dict | None:
    """Run TFT inference in a subprocess (to avoid GIL issues).

    Args:
        dates: List of date strings
        values: List of target values
        horizon: Forecast horizon
        regressors_data: Optional serialized regressors dict with 'dates' and 'values' for each

    Returns:
        Forecast result dict or None if failed
    """
    import pandas as pd

    from raglite.forecasting.models.tft_model import fit_and_forecast_tft

    # Reconstruct the Series in the subprocess
    y = pd.Series(values, index=pd.DatetimeIndex(dates))

    # Reconstruct external regressors if provided
    external_regressors: dict[str, pd.Series] | None = None
    if regressors_data:
        external_regressors = {}
        for name, data in regressors_data.items():
            reg_dates = pd.DatetimeIndex(data["dates"])
            reg_values = data["values"]
            external_regressors[name] = pd.Series(reg_values, index=reg_dates)

    return fit_and_forecast_tft(
        y=y,
        periods_ahead=horizon,
        external_regressors=external_regressors,
    )


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
