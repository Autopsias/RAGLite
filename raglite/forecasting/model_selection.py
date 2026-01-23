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

import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from raglite.forecasting.data_analyzer import (
    DataCharacteristics,
    VolatilityLevel,
    analyze_data_characteristics,
)

# Import internal implementation details
from raglite.forecasting.model_selection_internal import (
    _align_regressors,
    _run_cv_comparison,
    _select_best_from_results,
)

logger = logging.getLogger(__name__)


def _get_candidate_models() -> list[str]:
    """Get candidate models, with CI optimization.

    In CI environments, skip Chronos and TFT models which use ProcessPoolExecutor
    and conflict with pytest-xdist fork mode. These models add ~40% to CV runtime
    and can deadlock when fork() + PyTorch interact.

    P0 FIX (2026-01-23): CI tests were hanging at 28% due to ProcessPoolExecutor
    conflicts with xdist workers. Skipping these models in CI resolves the hang.
    """
    import os

    all_models = [
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

    # Skip ProcessPoolExecutor models in CI (PyTorch fork safety issues)
    is_ci = os.environ.get("CI") == "true"
    if is_ci:
        # Chronos and TFT use ProcessPoolExecutor which conflicts with xdist fork
        ci_models = [m for m in all_models if m not in ("chronos", "tft")]
        logger.info(f"CI mode: skipping chronos/tft models, using {len(ci_models)} models")
        return ci_models

    return all_models


# All 9 available models (or 7 in CI)
CANDIDATE_MODELS: list[str] = _get_candidate_models()


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

    # 3. Pre-filter based on data characteristics
    models_to_test = _filter_candidates(data_chars, CANDIDATE_MODELS.copy())

    # 4. Align regressors to target index
    aligned_regressors = _align_regressors(variable_name, historical_data, external_regressors)

    # 5. Run cross-validation comparison
    tscv = TimeSeriesSplit(n_splits=cv_folds)
    use_recency_weights = data_chars.volatility_level == VolatilityLevel.HIGH
    results = await _run_cv_comparison(
        variable_name,
        historical_data,
        models_to_test,
        aligned_regressors,
        tscv,
        use_recency_weights,
    )

    # 6. Select best model from results
    best_model_name, best_result = _select_best_from_results(variable_name, results, data_chars)

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

    Epic 7 Enhancement: Smart model pre-filtering to skip unsuitable models
    based on data characteristics, improving efficiency and avoiding known
    failure modes for certain model/data combinations.

    Args:
        data_chars: Analyzed characteristics of the time series data
        candidates: List of candidate model names to filter

    Returns:
        Filtered list of model names suitable for the data characteristics
    """
    filtered = candidates.copy()

    # 1. High volatility: Skip ETS (struggles with regime changes/structural breaks)
    if data_chars.volatility_level == VolatilityLevel.HIGH:
        if "ets" in filtered:
            filtered.remove("ets")
            logger.debug(
                "Filtered out ETS: high volatility data",
                extra={"cv": data_chars.coefficient_of_variation},
            )

    # 2. Short series (<36 points): Skip TFT (needs encoder_length + horizon)
    if data_chars.data_length < 36:
        if "tft" in filtered:
            filtered.remove("tft")
            logger.debug(
                "Filtered out TFT: series too short",
                extra={"data_length": data_chars.data_length},
            )

    # 3. Very short series (<18 points): Skip complex ML models
    if data_chars.data_length < 18:
        for model in ["xgboost", "lightgbm", "catboost"]:
            if model in filtered:
                filtered.remove(model)
                logger.debug(
                    f"Filtered out {model}: series too short for ML",
                    extra={"data_length": data_chars.data_length},
                )

    # 4. High volatility + non-stationary: Prioritize ML models
    if (
        data_chars.volatility_level == VolatilityLevel.HIGH
        and data_chars.coefficient_of_variation > 0.5
    ):
        ml_priority = ["xgboost", "lightgbm", "catboost"]
        for model in reversed(ml_priority):
            if model in filtered:
                filtered.remove(model)
                filtered.insert(0, model)
        logger.debug(
            "Prioritized ML models for high volatility series",
            extra={"cv": data_chars.coefficient_of_variation},
        )

    # 5. Very few data points (<12): Only keep robust models
    if data_chars.data_length < 12:
        robust_models = ["chronos", "prophet", "ets", "arima", "linear"]
        filtered = [m for m in filtered if m in robust_models]
        logger.debug(
            "Limited to robust models for very short series",
            extra={"data_length": data_chars.data_length},
        )

    # Ensure we don't filter out everything
    if not filtered:
        logger.warning(
            "All models filtered out - falling back to prophet",
            extra={"original_count": len(candidates)},
        )
        filtered = ["prophet"]

    return filtered
