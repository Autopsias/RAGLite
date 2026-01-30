"""Model group taxonomy for ensemble forecasting.

Story: Ensemble Model Grouping (Phase 7)

Defines model groups for stratified voting ensemble:
- Statistical: ARIMA, ETS
- Statistical-Hybrid: Prophet
- ML Gradient Boosting: XGBoost, LightGBM, CatBoost
- ML Linear: Linear/Ridge/Lasso
- Deep Learning: Chronos, TFT

Group-based weighting prevents any single model from dominating.
"""

from __future__ import annotations

from enum import Enum


class ModelGroup(Enum):
    """Model group classification for stratified ensemble voting.

    Groups models by methodology to ensure diversity in ensemble:
    - STATISTICAL: Traditional univariate methods (ARIMA, ETS)
    - STATISTICAL_HYBRID: Decomposition-based (Prophet)
    - ML_GRADIENT_BOOSTING: Tree ensemble methods (XGBoost, LightGBM, CatBoost)
    - ML_LINEAR: Linear regression methods (Linear, Ridge, Lasso)
    - DEEP_LEARNING: Neural/foundation models (Chronos, TFT)
    """

    STATISTICAL = "statistical"
    STATISTICAL_HYBRID = "statistical_hybrid"
    ML_GRADIENT_BOOSTING = "ml_gb"
    ML_LINEAR = "ml_linear"
    DEEP_LEARNING = "deep"


# Model to group mapping for all 9 available models
MODEL_TO_GROUP: dict[str, ModelGroup] = {
    # Statistical models (univariate)
    "arima": ModelGroup.STATISTICAL,
    "ets": ModelGroup.STATISTICAL,
    # Statistical-hybrid (decomposition + trend)
    "prophet": ModelGroup.STATISTICAL_HYBRID,
    # ML linear models
    "linear": ModelGroup.ML_LINEAR,
    "ridge": ModelGroup.ML_LINEAR,
    "lasso": ModelGroup.ML_LINEAR,
    # ML gradient boosting models
    "xgboost": ModelGroup.ML_GRADIENT_BOOSTING,
    "lightgbm": ModelGroup.ML_GRADIENT_BOOSTING,
    "catboost": ModelGroup.ML_GRADIENT_BOOSTING,
    # Deep learning / foundation models
    "chronos": ModelGroup.DEEP_LEARNING,
    "tft": ModelGroup.DEEP_LEARNING,
}


# Default group weights (sum to 1.0)
# Weights distribute influence across methodologies, not individual models
GROUP_WEIGHTS: dict[ModelGroup, float] = {
    ModelGroup.STATISTICAL: 0.15,  # 15% - ARIMA, ETS share this
    ModelGroup.STATISTICAL_HYBRID: 0.25,  # 25% - Prophet alone
    ModelGroup.ML_GRADIENT_BOOSTING: 0.25,  # 25% - XGBoost, LightGBM, CatBoost share
    ModelGroup.ML_LINEAR: 0.10,  # 10% - Linear alone
    ModelGroup.DEEP_LEARNING: 0.25,  # 25% - Chronos, TFT share this
}


def get_models_in_group(group: ModelGroup) -> list[str]:
    """Get all models belonging to a specific group.

    Args:
        group: ModelGroup enum value

    Returns:
        List of model names in the group
    """
    return [model for model, g in MODEL_TO_GROUP.items() if g == group]


def get_group_for_model(model_name: str) -> ModelGroup | None:
    """Get the group for a specific model.

    Args:
        model_name: Model name (lowercase)

    Returns:
        ModelGroup enum value or None if not found
    """
    return MODEL_TO_GROUP.get(model_name.lower())


def get_active_groups(available_models: list[str]) -> list[ModelGroup]:
    """Get list of groups that have at least one available model.

    Args:
        available_models: List of model names that produced predictions

    Returns:
        List of ModelGroup enum values with active models
    """
    active_groups: set[ModelGroup] = set()
    for model in available_models:
        group = get_group_for_model(model)
        if group is not None:
            active_groups.add(group)
    return list(active_groups)
