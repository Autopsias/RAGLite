"""Weight management functions for adaptive ensemble.

Contains functions for retrieving, calculating, and adjusting model weights.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Weight caps per AC4
MIN_WEIGHT = 0.05  # 5% minimum
MAX_WEIGHT = 0.50  # 50% maximum
EPSILON = 0.001  # Prevent division by zero


def get_adaptive_weights(
    metric: str,
    has_regressors: bool = True,
    session: Session | None = None,
) -> dict[str, float]:
    """Get adaptive weights for a metric from PostgreSQL.

    Story 6.12 AC4: Retrieve stored weights with fallback logic.

    Behavior:
    - If weights exist in model_weights table, use them
    - If no weights exist, return static weights from config
    - If has_regressors=False, boost Prophet (or Chronos) weight per AC4

    Args:
        metric: Target metric name
        has_regressors: Whether external regressors are available
        session: Optional SQLAlchemy session (creates new if None)

    Returns:
        Dict mapping model_name -> weight (float)
    """
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session

    # Get session
    if session is None:
        session = get_session()

    storage = ExternalDataStorage(session)
    weights = storage.get_weights_for_metric(metric)

    if weights:
        # Adaptive weights exist
        logger.info(
            "Using adaptive weights from database",
            extra={"metric": metric, "weights": weights},
        )

        if not has_regressors:
            # Apply regressor-dependent adjustment per AC4
            weights = _adjust_weights_no_regressors(weights)

        return weights

    # Fallback to static weights from config
    logger.info(
        "No adaptive weights found, using static config weights",
        extra={"metric": metric},
    )
    return _get_static_weights()


def _get_static_weights() -> dict[str, float]:
    """Get static weights from config.py.

    Story 6.13: Added Chronos-2 weight.
    Story 6.14: Added TFT weight.

    Returns:
        Dict of model weights from settings, normalized to sum to 1.0
    """
    weights = {
        "prophet": settings.ensemble_weight_prophet,
        "linear": settings.ensemble_weight_linear,
        "xgboost": settings.ensemble_weight_xgboost,
        "lightgbm": settings.ensemble_weight_lightgbm,
        "catboost": settings.ensemble_weight_catboost,
        "chronos": settings.ensemble_weight_chronos,  # Story 6.13
        "tft": settings.ensemble_weight_tft,  # Story 6.14
    }

    # Normalize weights to sum to 1.0
    total = sum(weights.values())
    if total == 0:
        # If all weights are 0, assign equal weights
        n_models = len(weights)
        if n_models > 0:
            return dict.fromkeys(weights, 1.0 / n_models)
        else:
            return {}

    # Normalize each weight
    return {k: v / total for k, v in weights.items()}


def _adjust_weights_no_regressors(weights: dict[str, float]) -> dict[str, float]:
    """Adjust weights when no external regressors are available.

    Story 6.12 AC4: No regressors → Prophet/Chronos weight x2,
    regressor-dependent models x0.3

    Regressor-dependent models: linear, xgboost, lightgbm, catboost
    Non-regressor models: prophet (and future chronos)

    Args:
        weights: Current model weights

    Returns:
        Adjusted weights (re-normalized)
    """
    regressor_dependent = {"linear", "xgboost", "lightgbm", "catboost"}
    non_regressor = {"prophet", "chronos"}  # Chronos prep for 6.13

    adjusted: dict[str, float] = {}
    for model, weight in weights.items():
        if model in non_regressor:
            adjusted[model] = weight * 2.0
        elif model in regressor_dependent:
            adjusted[model] = weight * 0.3
        else:
            adjusted[model] = weight

    # Re-normalize
    total = sum(adjusted.values())
    if total > 0:
        adjusted = {k: v / total for k, v in adjusted.items()}

    logger.info(
        "Adjusted weights for no-regressor scenario",
        extra={"original": weights, "adjusted": adjusted},
    )
    return adjusted


def apply_weight_caps(weights: dict[str, float]) -> dict[str, float]:
    """Apply minimum and maximum weight caps.

    Story 6.12 AC4: Weight caps: Min 5%, Max 50% per model.

    Args:
        weights: Uncapped weights

    Returns:
        Capped and re-normalized weights
    """
    # Apply caps
    capped = {k: max(MIN_WEIGHT, min(MAX_WEIGHT, v)) for k, v in weights.items()}

    # Re-normalize
    total = sum(capped.values())
    if total > 0:
        capped = {k: v / total for k, v in capped.items()}

    return capped


def handle_model_failure(weights: dict[str, float], failed_model: str) -> dict[str, float]:
    """Handle model failure by removing and re-normalizing weights.

    Story 6.12 AC4: Model fails → Removed from ensemble, weights re-normalized.
    """
    if failed_model not in weights:
        return weights
    remaining = {k: v for k, v in weights.items() if k != failed_model}
    if not remaining:
        logger.error("All models failed, cannot re-normalize")
        return {}
    total = sum(remaining.values())
    if total > 0:
        remaining = {k: v / total for k, v in remaining.items()}
    logger.info(
        "Re-normalized weights after model failure",
        extra={"failed_model": failed_model, "remaining": remaining},
    )
    return remaining


def _calculate_weights_from_rmse(
    results: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    """Calculate normalized, capped weights from backtest RMSE.

    Story 6.12 AC3: Weight formula: weight = 1 / (RMSE + epsilon)

    Args:
        results: Dict with model results containing 'rmse'

    Returns:
        Same dict with 'weight' added to each model
    """
    # Calculate raw weights (inverse RMSE)
    raw_weights: dict[str, float] = {}
    for model, metrics in results.items():
        rmse = metrics.get("rmse", float("inf"))
        raw_weights[model] = 1.0 / (rmse + EPSILON)

    # Normalize to sum to 1.0
    total = sum(raw_weights.values())
    if total > 0:
        normalized = {k: v / total for k, v in raw_weights.items()}
    else:
        # Equal weights if all failed
        n = len(raw_weights)
        equal_weight = 1.0 / n
        normalized = dict.fromkeys(raw_weights, equal_weight)

    # Apply caps (AC4)
    capped = {k: max(MIN_WEIGHT, min(MAX_WEIGHT, v)) for k, v in normalized.items()}

    # Re-normalize after capping
    total_capped = sum(capped.values())
    final_weights = {k: v / total_capped for k, v in capped.items()}

    # Add weights to results
    for model in results:
        results[model]["weight"] = final_weights.get(model, 0.0)

    return results
