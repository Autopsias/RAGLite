"""Per-Variable Model Selection via Cross-Validation.

Story 7b-3: Implements intelligent model selection by testing all 9 available
models against each variable and selecting the best based on cross-validated
MAPE/MASE scores.

Models tested:
- arima: ARIMA/SARIMA (Story 7b-1)
- ets: Exponential Smoothing (Story 7b-1)
- prophet: Facebook Prophet
- xgboost: XGBoost gradient boosting
- lightgbm: LightGBM gradient boosting
- catboost: CatBoost gradient boosting
- chronos: Chronos-2 zero-shot
- tft: Temporal Fusion Transformer
- linear: Linear/Ridge/Lasso regression
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from raglite.forecasting.data_analyzer import (
    DataCharacteristics,
    analyze_data_characteristics,
)
from raglite.forecasting.model_selection_utils import (
    calculate_mape,
    calculate_mase,
    fit_chronos,
    fit_ml_model,
    fit_prophet,
    fit_tft,
)

logger = logging.getLogger(__name__)

# All 9 available models
CANDIDATE_MODELS: list[str] = [
    "arima",
    "ets",
    "prophet",
    "xgboost",
    "lightgbm",
    "catboost",
    "chronos",
    "tft",
    "linear",
]


@dataclass
class ModelSelectionResult:
    """Result of model selection for a variable."""

    variable_name: str
    best_model: str
    best_mape: float
    best_mase: float
    best_with_regressors: bool
    best_regressor_set: list[str] = field(default_factory=list)
    candidate_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    data_characteristics: DataCharacteristics | None = None
    cv_folds: int = 5
    runtime_seconds: float = 0.0


class ModelSelectionError(Exception):
    """Raised when model selection fails completely."""

    pass


async def select_best_model(
    variable_name: str,
    historical_data: pd.Series,
    external_regressors: dict[str, pd.Series] | None = None,
    cv_folds: int = 5,
    force_refresh: bool = False,
) -> ModelSelectionResult:
    """Select best model for variable via cross-validation.

    Tests all 9 models (or specified candidates) with and without regressors,
    using TimeSeriesSplit cross-validation. Selects winner by MASE (primary)
    and MAPE (secondary tiebreaker). MASE is preferred because it's reliable
    for near-zero/negative values where MAPE fails.

    Args:
        variable_name: Name of the variable being forecasted
        historical_data: Time series of historical values (pd.Series with DatetimeIndex)
        external_regressors: Optional dict of regressor name -> Series
        cv_folds: Number of cross-validation folds (default: 5)
        force_refresh: Ignore cached results (not implemented yet)

    Returns:
        ModelSelectionResult with best model and all candidate results

    Raises:
        ValueError: If no models complete successfully or data is insufficient
        ModelSelectionError: If all models fail
    """
    start_time = time.time()

    # 1. Validate minimum data points
    if len(historical_data) < 12:
        raise ValueError(
            f"Variable {variable_name} has only {len(historical_data)} points, "
            "minimum 12 required for cross-validation"
        )

    # 2. Analyze data characteristics
    data_chars = analyze_data_characteristics(historical_data)

    # 3. Pre-filter based on data characteristics (optional, currently returns all)
    models_to_test = _filter_candidates(data_chars, CANDIDATE_MODELS.copy())

    # 4. Cross-validate each model
    tscv = TimeSeriesSplit(n_splits=cv_folds)
    results: dict[str, dict[str, Any]] = {}

    # Handle empty regressors dict as None
    if external_regressors is not None and len(external_regressors) == 0:
        external_regressors = None

    # Align regressors to target index BEFORE CV (critical for correct slicing)
    aligned_regressors: dict[str, pd.Series] | None = None
    if external_regressors:
        aligned_regressors = {}
        target_index = historical_data.index

        # BUG FIX: Normalize target index to month-start for consistent alignment
        # External time series may use month-end dates (2017-10-31) while regressors
        # use month-start dates (2017-10-01), causing 0% overlap without normalization
        normalized_target = target_index.to_period("M").to_timestamp()

        for reg_name, reg_series in external_regressors.items():
            # Normalize regressor index to month-start as well
            reg_normalized = reg_series.copy()
            reg_normalized.index = reg_series.index.to_period("M").to_timestamp()
            # Deduplicate if normalization created duplicates (take mean)
            reg_normalized = reg_normalized.groupby(reg_normalized.index).mean()

            # Reindex regressor to match normalized target dates, forward-fill gaps
            aligned = reg_normalized.reindex(normalized_target, method="ffill")

            # Map back to original target index for CV slicing
            aligned.index = target_index

            # Only keep if we have enough non-null values
            if aligned.notna().sum() >= len(target_index) * 0.8:
                aligned_regressors[reg_name] = aligned
            else:
                logger.warning(
                    f"Regressor {reg_name} dropped: insufficient overlap with target index "
                    f"({aligned.notna().sum()}/{len(target_index)} values)"
                )
        if not aligned_regressors:
            logger.warning("No regressors survived alignment - testing without regressors")
            aligned_regressors = None
        else:
            logger.info(
                f"Aligned {len(aligned_regressors)} regressors to target index",
                extra={"regressors": list(aligned_regressors.keys())},
            )

    for model_name in models_to_test:
        # Test without regressors
        config_key_no_regs = f"{model_name}_False"
        try:
            cv_metrics = await _cv_evaluate(model_name, historical_data, None, tscv)
            results[config_key_no_regs] = {
                **cv_metrics,
                "with_regressors": False,
                "regressor_set": [],
            }
            logger.info(
                f"Model {config_key_no_regs} CV complete",
                extra={
                    "variable": variable_name,
                    "mape": cv_metrics["mape"],
                    "mase": cv_metrics["mase"],
                },
            )
        except Exception as e:
            logger.warning(
                f"Model {model_name} (no regressors) failed for {variable_name}: {e}",
                extra={"model": model_name, "error": str(e)},
            )
            results[config_key_no_regs] = {
                "error": str(e),
                "mape": float("inf"),
                "mase": float("inf"),
            }

        # Test with regressors if provided (skip chronos, ets - they don't support regressors)
        # Note: TFT DOES support regressors via external_regressors parameter
        if aligned_regressors and model_name not in ("chronos", "ets"):
            config_key_with_regs = f"{model_name}_True"
            try:
                cv_metrics = await _cv_evaluate(
                    model_name, historical_data, aligned_regressors, tscv
                )
                results[config_key_with_regs] = {
                    **cv_metrics,
                    "with_regressors": True,
                    "regressor_set": list(aligned_regressors.keys()),
                }
                logger.info(
                    f"Model {config_key_with_regs} CV complete",
                    extra={
                        "variable": variable_name,
                        "mape": cv_metrics["mape"],
                        "mase": cv_metrics["mase"],
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Model {model_name} (with regressors) failed for {variable_name}: {e}",
                    extra={"model": model_name, "error": str(e)},
                )
                results[config_key_with_regs] = {
                    "error": str(e),
                    "mape": float("inf"),
                    "mase": float("inf"),
                }

    # 5. Ensure at least one model succeeded
    valid_results = {k: v for k, v in results.items() if "error" not in v}
    if not valid_results:
        raise ModelSelectionError(
            f"All models failed for variable {variable_name}. Errors: {results}"
        )

    # 6. Select best by MASE (primary), then MAPE (secondary)
    # Story 7b-3: Changed from MAPE-primary to MASE-primary because:
    # - MASE is scale-independent and benchmarks against naive forecast
    # - MAPE is unreliable for near-zero/negative values (causes infinite errors)
    # - MASE < 1.0 = better than naive, regardless of value scale
    best_key = min(
        valid_results.keys(), key=lambda k: (valid_results[k]["mase"], valid_results[k]["mape"])
    )
    best_result = valid_results[best_key]

    # Parse model name from key
    best_model_name = best_key.rsplit("_", 1)[0]

    runtime = time.time() - start_time

    return ModelSelectionResult(
        variable_name=variable_name,
        best_model=best_model_name,
        best_mape=best_result["mape"],
        best_mase=best_result["mase"],
        best_with_regressors=best_result.get("with_regressors", False),
        best_regressor_set=best_result.get("regressor_set", []),
        candidate_results=results,
        data_characteristics=data_chars,
        cv_folds=cv_folds,
        runtime_seconds=runtime,
    )


def _filter_candidates(
    data_chars: DataCharacteristics,
    candidates: list[str],
) -> list[str]:
    """Pre-filter models based on data characteristics.

    Currently returns all candidates, but can be enhanced later for
    performance optimization by skipping unsuitable models.

    Args:
        data_chars: Analyzed characteristics of the time series data
        candidates: List of candidate model names to filter

    Returns:
        Filtered list of model names suitable for the data characteristics
    """
    # For now, return all candidates
    # Future: filter based on stationarity, seasonality, volatility
    return candidates


async def _cv_evaluate(
    model_name: str,
    y: pd.Series,
    regressors: dict[str, pd.Series] | None,
    tscv: TimeSeriesSplit,
) -> dict[str, float]:
    """Cross-validate a single model and return average metrics.

    Performs time-series cross-validation using the provided TimeSeriesSplit object,
    calculating MAPE and MASE for each fold and returning the average.

    Args:
        model_name: Name of the model to evaluate (e.g., 'arima', 'prophet')
        y: Time series data with DatetimeIndex
        regressors: Optional dictionary mapping regressor names to aligned Series
        tscv: TimeSeriesSplit object for cross-validation fold generation

    Returns:
        Dictionary with average 'mape' and 'mase' scores across all folds

    Raises:
        Exception: Propagated from model fitting or prediction failures
    """
    mape_scores = []
    mase_scores = []

    for train_idx, test_idx in tscv.split(y):
        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]

        X_train = None
        X_test = None
        if regressors:
            X_train = pd.DataFrame({k: v.iloc[train_idx] for k, v in regressors.items()})
            X_test = pd.DataFrame({k: v.iloc[test_idx] for k, v in regressors.items()})

        # Fit and predict
        predictions = await _fit_and_predict(model_name, y_train, X_train, len(y_test), X_test)

        # Calculate metrics
        mape = calculate_mape(y_test.values, predictions)
        mase = calculate_mase(y_train.values, y_test.values, predictions)

        mape_scores.append(mape)
        mase_scores.append(mase)

    return {
        "mape": float(np.mean(mape_scores)),
        "mase": float(np.mean(mase_scores)),
    }


async def _fit_and_predict(
    model_name: str,
    y_train: pd.Series,
    X_train: pd.DataFrame | None,
    horizon: int,
    X_future: pd.DataFrame | None,
) -> np.ndarray:
    """Fit model and generate predictions.

    Args:
        model_name: Name of the model to fit
        y_train: Training time series
        X_train: Training regressors (optional)
        horizon: Forecast horizon
        X_future: Future regressors (optional)

    Returns:
        Array of predictions
    """
    if model_name == "arima":
        from raglite.forecasting.models.arima_model import fit_arima

        _, _, predictions, _ = await fit_arima(
            y_train, X_train=X_train, X_future=X_future, forecast_horizon=horizon
        )
        return predictions

    elif model_name == "ets":
        from raglite.forecasting.models.ets_model import fit_ets

        _, _, predictions, _ = await fit_ets(y_train, forecast_horizon=horizon)
        return predictions

    elif model_name == "prophet":
        return await fit_prophet(y_train, X_train, horizon, X_future)

    elif model_name in ("xgboost", "lightgbm", "catboost", "linear"):
        return await fit_ml_model(model_name, y_train, X_train, horizon, X_future)

    elif model_name == "chronos":
        return await fit_chronos(y_train, horizon)

    elif model_name == "tft":
        # TFT uses pre-trained checkpoint for inference
        # Returns NaN array if no checkpoint available (model will be skipped)
        # Convert DataFrame to dict of Series for TFT regressor format
        tft_regressors: dict[str, pd.Series] | None = None
        if X_train is not None and not X_train.empty:
            tft_regressors = {col: X_train[col] for col in X_train.columns}
        return await fit_tft(y_train, horizon, external_regressors=tft_regressors)

    else:
        raise ValueError(f"Unknown model: {model_name}")
