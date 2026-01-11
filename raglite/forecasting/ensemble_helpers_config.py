"""Configuration and weight management for ensemble forecasting.

Extracted from ensemble_helpers.py (Story 8 refactoring).
"""

from __future__ import annotations

from logging import Logger

import pandas as pd


def get_initial_weights(
    metric: str,
    external_regressors: dict[str, pd.Series] | None,
    logger: Logger,
) -> dict[str, float]:
    """Get initial weights for ensemble models (Story 6.12 AC4)."""
    from raglite.forecasting.adaptive_weights import get_adaptive_weights
    from raglite.shared.config import settings

    has_regressors = external_regressors is not None and len(external_regressors) > 0

    try:
        weights = get_adaptive_weights(metric, has_regressors=has_regressors)
        logger.info(
            "Using adaptive weights",
            extra={"metric": metric, "weights": weights, "has_regressors": has_regressors},
        )
        return weights
    except Exception as e:
        logger.warning(
            f"Failed to get adaptive weights, using static: {e}",
            extra={"metric": metric},
        )
        return {
            "prophet": settings.ensemble_weight_prophet,
            "linear": settings.ensemble_weight_linear,
            "xgboost": settings.ensemble_weight_xgboost,
            "lightgbm": settings.ensemble_weight_lightgbm,
            "catboost": settings.ensemble_weight_catboost,
            "chronos": settings.ensemble_weight_chronos,
            "tft": settings.ensemble_weight_tft,
        }


def renormalize_weights(
    weights: dict[str, float],
    failed_models: list[str],
    successful_models: list[str],
    logger: Logger,
) -> dict[str, float]:
    """Re-normalize weights after model failures.

    Story 6.12 AC4: Handle failures with weight re-normalization.

    Args:
        weights: Original model weights
        failed_models: List of failed model names
        successful_models: List of successful model names
        logger: Logger instance

    Returns:
        Re-normalized weights dictionary
    """
    from raglite.forecasting.adaptive_weights import handle_model_failure

    # Re-normalize after failures
    if failed_models:
        for failed in failed_models:
            weights = handle_model_failure(weights, failed)
        logger.info(
            "Weights re-normalized after model failures",
            extra={"failed_models": failed_models, "new_weights": weights},
        )

    # Normalize to successful models only
    if successful_models:
        remaining = {k: weights.get(k, 0.0) for k in successful_models if weights.get(k, 0.0) > 0}
        if remaining:
            total = sum(remaining.values())
            if total > 0:
                weights = {k: v / total for k, v in remaining.items()}
                logger.info(
                    "Weights normalized to successful models only",
                    extra={"successful_models": successful_models, "final_weights": weights},
                )

    return weights


def initialize_ensemble_config(
    models: list[str] | None,
    weights: dict[str, float] | None,
    fast_mode: bool,
    metric: str,
    external_regressors: dict[str, pd.Series] | None,
    logger: Logger,
) -> tuple[list[str], dict[str, float], bool]:
    """Initialize ensemble configuration (models, weights, fast_mode).

    Args:
        models: Models to use (None = use settings default)
        weights: Model weights (None = use adaptive/static weights)
        fast_mode: Use fast hyperparameter grid
        metric: Metric name for adaptive weights
        external_regressors: External regressors dict
        logger: Logger instance

    Returns:
        Tuple of (models, weights, fast_mode)
    """
    from raglite.shared.config import settings

    if models is None:
        models = settings.forecasting_models.split(",")

    if weights is None:
        weights = get_initial_weights(metric, external_regressors, logger)

    if fast_mode is False:
        fast_mode = settings.ensemble_fast_mode

    return models, weights, fast_mode
