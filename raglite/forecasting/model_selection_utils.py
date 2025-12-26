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
    """Fit ML model (XGBoost, LightGBM, CatBoost, Linear) and generate predictions.

    Epic 7 Enhancement: Uses enhanced feature engineering with rolling statistics,
    momentum features, and volatility indicators for improved prediction accuracy.
    """
    # Create enhanced lagged features
    n_lags = min(12, len(y_train) // 2)
    X_train_ml = create_lagged_features(y_train, n_lags)

    # Get the feature columns used during training (for prediction alignment)
    training_columns = list(X_train_ml.columns)

    # Align y_train to match X_train_ml length (features have NaN dropped)
    # The features DataFrame starts where all features are valid
    y_train_ml = y_train.iloc[-len(X_train_ml) :].values

    # Add external regressors if provided (must match lagged feature length)
    if X_train is not None and len(X_train) == len(y_train):
        X_reg_aligned = X_train.iloc[-len(X_train_ml) :].reset_index(drop=True)
        # Ensure lengths match before concat
        if len(X_reg_aligned) == len(X_train_ml):
            X_train_ml = pd.concat([X_train_ml.reset_index(drop=True), X_reg_aligned], axis=1)

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
    # Keep enough history for rolling features (12 periods for rolling_std_12)
    history = y_train.values.tolist()

    for i in range(horizon):
        # Build prediction features matching training columns
        X_pred = _build_prediction_features(history, n_lags, training_columns)

        # Add external regressors if available
        if X_future is not None:
            if i < len(X_future):
                reg_row = pd.DataFrame([X_future.iloc[i].values], columns=X_future.columns)
            else:
                reg_row = pd.DataFrame([X_future.iloc[-1].values], columns=X_future.columns)
            X_pred = pd.concat([X_pred.reset_index(drop=True), reg_row], axis=1)

        pred = model.predict(X_pred)[0]
        predictions.append(pred)
        history.append(pred)

    return np.array(predictions)


def _build_prediction_features(
    history: list, n_lags: int, training_columns: list[str]
) -> pd.DataFrame:
    """Build prediction features matching training feature structure.

    Epic 7 Enhancement: Computes all enhanced features for a single prediction step.

    Args:
        history: Historical values including any prior predictions
        n_lags: Number of lag features
        training_columns: Column names from training (for alignment)

    Returns:
        Single-row DataFrame with features matching training structure
    """
    features = {}

    # 1. Simple lags
    for j in range(1, n_lags + 1):
        if len(history) >= j:
            features[f"lag_{j}"] = history[-j]
        else:
            features[f"lag_{j}"] = np.nan

    # 2. Rolling statistics (compute from history)
    arr = np.array(history)
    for window in [3, 6, 12]:
        col_mean = f"rolling_mean_{window}"
        col_std = f"rolling_std_{window}"
        if col_mean in training_columns:
            if len(arr) >= window:
                features[col_mean] = np.mean(arr[-window:])
                features[col_std] = np.std(arr[-window:], ddof=1) if len(arr) >= window else 0.0
            else:
                features[col_mean] = np.mean(arr) if len(arr) > 0 else 0.0
                features[col_std] = np.std(arr, ddof=1) if len(arr) > 1 else 0.0

    # 3. Momentum features
    if "diff_1" in training_columns:
        features["diff_1"] = history[-1] - history[-2] if len(history) >= 2 else 0.0

    if "pct_change_1" in training_columns:
        if len(history) >= 2 and history[-2] != 0:
            features["pct_change_1"] = (history[-1] - history[-2]) / abs(history[-2])
        else:
            features["pct_change_1"] = 0.0

    if "diff_12" in training_columns:
        features["diff_12"] = history[-1] - history[-12] if len(history) >= 12 else 0.0

    # 4. Volatility features
    if "rolling_range_6" in training_columns:
        if len(arr) >= 6:
            features["rolling_range_6"] = float(np.max(arr[-6:]) - np.min(arr[-6:]))
        else:
            features["rolling_range_6"] = float(np.max(arr) - np.min(arr)) if len(arr) > 0 else 0.0

    return pd.DataFrame([features])


def create_lagged_features(y: pd.Series, n_lags: int) -> pd.DataFrame:
    """Create enhanced lagged features from time series.

    Epic 7 Enhancement: Added rolling statistics, momentum, and volatility features
    based on time series forecasting best practices (Hyndman 2006, McKinsey).

    Features created:
    - Simple lags (1 to n_lags)
    - Rolling statistics (mean, std over 3, 6, 12 periods)
    - Momentum features (first difference, percentage change, YoY diff)
    - Volatility features (rolling range)

    Args:
        y: Time series data
        n_lags: Number of simple lag features to create

    Returns:
        DataFrame with all engineered features, NaN rows dropped
    """
    features = {}

    # 1. Simple lags (existing behavior)
    for i in range(1, n_lags + 1):
        features[f"lag_{i}"] = y.shift(i)

    # 2. Rolling statistics (NEW - shifted to prevent data leakage)
    # For very short series, only create rolling features that preserve training samples
    # Require: (window + shift) + n_lags < len(y) to ensure at least 1 training sample
    for window in [3, 6, 12]:
        # Ensure rolling window won't eliminate all training samples
        # Need: window (for rolling) + 1 (for shift) + n_lags (for lags) <= len(y)
        if len(y) > (window + 1 + n_lags):
            features[f"rolling_mean_{window}"] = y.rolling(window=window).mean().shift(1)
            features[f"rolling_std_{window}"] = y.rolling(window=window).std().shift(1)

    # 3. Momentum features (NEW - shifted to prevent data leakage)
    features["diff_1"] = y.diff(1).shift(1)
    features["pct_change_1"] = y.pct_change(1).shift(1)
    # For diff_12, we need: 12 (diff period) + 1 (shift) + n_lags <= len(y)
    if len(y) > (12 + 1 + n_lags):
        features["diff_12"] = y.diff(12).shift(1)  # YoY momentum

    # 4. Volatility features (NEW - shifted to prevent data leakage)
    # Same check as rolling features to preserve training samples
    if len(y) > (6 + 1 + n_lags):
        features["rolling_range_6"] = (y.rolling(6).max() - y.rolling(6).min()).shift(1)

    df = pd.DataFrame(features)
    return df.dropna()  # Drop rows with NaN from any feature


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


# =============================================================================
# Epic 7 Enhancement: Bias Correction Utilities
# =============================================================================


def calculate_bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate forecast bias (mean error).

    Positive bias = model tends to over-predict
    Negative bias = model tends to under-predict

    Args:
        y_true: Array of true values
        y_pred: Array of predicted values

    Returns:
        Mean error (bias) in original units
    """
    return float(np.mean(y_pred - y_true))


def apply_bias_correction(
    predictions: np.ndarray,
    historical_bias: float,
    correction_factor: float = 1.0,
) -> np.ndarray:
    """Apply bias correction to predictions.

    Epic 7 Enhancement: Reduces systematic over/under-prediction by subtracting
    historical bias from predictions.

    Args:
        predictions: Array of predictions to correct
        historical_bias: Measured bias from validation (positive = over-predicting)
        correction_factor: Fraction of bias to correct (0.0-1.0, default 1.0)
            Use <1.0 for partial correction to avoid over-correction

    Returns:
        Bias-corrected predictions
    """
    correction = historical_bias * correction_factor
    return predictions - correction


def estimate_rolling_bias(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    window: int = 6,
) -> np.ndarray:
    """Estimate rolling bias over a sliding window.

    Useful for detecting if bias is changing over time (e.g., regime changes).

    Args:
        y_true: Array of true values
        y_pred: Array of predicted values
        window: Rolling window size

    Returns:
        Array of rolling bias values
    """
    errors = y_pred - y_true
    rolling_bias = pd.Series(errors).rolling(window=window, min_periods=1).mean()
    return np.asarray(rolling_bias)


def detect_bias_regime_change(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold: float = 2.0,
) -> tuple[bool, float, float]:
    """Detect if there's a significant bias regime change.

    Compares bias in first half vs second half of the series.

    Args:
        y_true: Array of true values
        y_pred: Array of predicted values
        threshold: Ratio threshold for detecting change (default 2.0 = 2x difference)

    Returns:
        Tuple of (regime_change_detected, first_half_bias, second_half_bias)
    """
    mid_point = len(y_true) // 2

    first_half_bias = calculate_bias(y_true[:mid_point], y_pred[:mid_point])
    second_half_bias = calculate_bias(y_true[mid_point:], y_pred[mid_point:])

    # Avoid division by zero
    if abs(first_half_bias) < 1e-10:
        regime_change = abs(second_half_bias) > threshold
    else:
        ratio = abs(second_half_bias / first_half_bias)
        regime_change = ratio > threshold or ratio < 1 / threshold

    return regime_change, first_half_bias, second_half_bias
