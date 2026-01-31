"""Result building and aggregation for ensemble forecasting.

Extracted from ensemble_helpers.py (Story 8 refactoring).
EBITDA bug fix (2026-01-29): Fixed confidence interval calculation to use
historical volatility instead of hardcoded ±20% multipliers.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData

logger = get_logger(__name__)


def _calculate_volatility_based_ci(
    value: float,
    historical_values: np.ndarray,
    confidence_level: float = 0.95,
) -> tuple[float, float]:
    """Calculate confidence interval based on historical volatility.

    EBITDA bug fix: Uses historical standard deviation instead of hardcoded ±20%.

    Args:
        value: Point estimate for the forecast
        historical_values: Array of historical values for volatility calculation
        confidence_level: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if len(historical_values) < 3:
        # Not enough data for meaningful volatility - use conservative 25%
        half_width = abs(value) * 0.25
        return value - half_width, value + half_width

    # Calculate coefficient of variation (CV) as relative volatility measure
    mean_val = np.mean(historical_values)
    std_val = np.std(historical_values, ddof=1)  # Sample std dev

    if mean_val == 0 or np.isnan(std_val):
        # Fallback for edge cases
        half_width = abs(value) * 0.20
        return value - half_width, value + half_width

    # Use z-score for confidence level (1.96 for 95%, 1.645 for 90%)
    z_score = 1.96 if confidence_level >= 0.95 else 1.645

    # Scale uncertainty by relative volatility (CV) of historical data
    cv = abs(std_val / mean_val)
    # Cap CV at 0.5 (50%) to avoid unreasonably wide intervals
    cv = min(cv, 0.5)

    half_width = abs(value) * cv * z_score

    lower = value - half_width
    upper = value + half_width

    return lower, upper


def _adjust_ci_for_point_estimate(
    value: float,
    lower: float,
    upper: float,
) -> tuple[float, float]:
    """Ensure point estimate falls within CI bounds.

    EBITDA bug fix: Adjusts CI bounds if point estimate falls outside.

    Args:
        value: Point estimate
        lower: Original lower bound
        upper: Original upper bound

    Returns:
        Tuple of (adjusted_lower, adjusted_upper)
    """
    # Point estimate should always be within bounds
    if value < lower:
        # Shift bounds down, maintaining width
        width = upper - lower
        lower = value - width * 0.3  # 30% below point
        upper = value + width * 0.7  # 70% above point
        logger.debug(
            "Adjusted CI bounds (value below lower)",
            extra={"value": value, "new_lower": lower, "new_upper": upper},
        )
    elif value > upper:
        # Shift bounds up, maintaining width
        width = upper - lower
        lower = value - width * 0.7  # 70% below point
        upper = value + width * 0.3  # 30% above point
        logger.debug(
            "Adjusted CI bounds (value above upper)",
            extra={"value": value, "new_lower": lower, "new_upper": upper},
        )

    return lower, upper


def build_forecast_points(
    ensemble_values: list[float],
    prophet_result: ForecastResult | None,
    df: pd.DataFrame,
    periods_ahead: int,
) -> list[ForecastPoint]:
    """Build forecast points from ensemble values.

    EBITDA bug fix (2026-01-29):
    - When Prophet CI is used, adjusts bounds if ensemble value differs significantly
    - When no Prophet, calculates CI from historical volatility (not hardcoded ±20%)

    Args:
        ensemble_values: Weighted ensemble predictions
        prophet_result: Prophet result (if available) for CI
        df: Historical DataFrame with 'ds' and 'y' columns
        periods_ahead: Number of periods

    Returns:
        List of ForecastPoint objects with valid CI bounds
    """
    historical_values = df["y"].values if "y" in df.columns else np.array([])

    if prophet_result:
        forecast_points = []
        for i, p in enumerate(prophet_result.forecast):
            value = ensemble_values[i] if i < len(ensemble_values) else p.value
            lower, upper = p.lower, p.upper

            # EBITDA bug fix: Adjust CI if ensemble value differs from Prophet
            # Prophet's CI was calculated for Prophet's estimate, not ensemble
            lower, upper = _adjust_ci_for_point_estimate(value, lower, upper)

            forecast_points.append(
                ForecastPoint(
                    date=p.date,
                    value=value,
                    lower=lower,
                    upper=upper,
                    label=p.label,
                )
            )
        return forecast_points

    # Build from scratch (no Prophet available) - use volatility-based CI
    last_date = df["ds"].max()
    forecast_points = []
    for i in range(periods_ahead):
        next_date = last_date + pd.DateOffset(months=3 * (i + 1))
        quarter = (next_date.month - 1) // 3 + 1
        label = f"Q{quarter} {next_date.year}"
        value = ensemble_values[i] if i < len(ensemble_values) else 0.0

        # EBITDA bug fix: Calculate CI from historical volatility, not hardcoded ±20%
        lower, upper = _calculate_volatility_based_ci(value, historical_values)

        forecast_points.append(
            ForecastPoint(
                date=next_date.to_pydatetime(),
                value=value,
                lower=lower,
                upper=upper,
                label=label,
            )
        )
    return forecast_points


def aggregate_metrics(metrics_results: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Aggregate accuracy metrics from individual models.

    Args:
        metrics_results: Dictionary of model metrics

    Returns:
        Combined metrics dictionary
    """
    combined_metrics: dict[str, float] = {}
    if not metrics_results:
        return combined_metrics

    rmse_values = [
        float(m.get("rmse", 0))
        for m in metrics_results.values()
        if isinstance(m.get("rmse"), (int, float)) and m.get("rmse", 0) > 0
    ]
    mae_values = [
        float(m.get("mae", 0))
        for m in metrics_results.values()
        if isinstance(m.get("mae"), (int, float)) and m.get("mae", 0) > 0
    ]
    mape_values = [
        float(m.get("mape", 0))
        for m in metrics_results.values()
        if isinstance(m.get("mape"), (int, float)) and m.get("mape", 0) > 0
    ]

    if rmse_values:
        combined_metrics["rmse"] = float(np.mean(rmse_values))
    if mae_values:
        combined_metrics["mae"] = float(np.mean(mae_values))
    if mape_values:
        combined_metrics["mape"] = float(np.mean(mape_values))

    return combined_metrics


def calculate_ensemble_forecast(
    successful_models: list[str],
    predictions: dict[str, list[float]],
    weights: dict[str, float],
) -> list[float]:
    """Calculate weighted ensemble forecast from successful models.

    Args:
        successful_models: List of successful model names
        predictions: Dictionary of model predictions
        weights: Model weights

    Returns:
        List of weighted ensemble values
    """
    from raglite.forecasting.ensemble import _calculate_weighted_average

    if len(successful_models) == 1:
        return predictions[successful_models[0]]
    else:
        return _calculate_weighted_average(predictions, weights, successful_models)


def calculate_stratified_ensemble_forecast(
    predictions: dict[str, list[float]],
    group_weights: dict | None = None,
) -> list[float]:
    """Two-stage stratified voting ensemble.

    Story: Ensemble Model Grouping (Phase 7)

    Implements stratified voting to prevent any single model from dominating:
    - Stage 1: Average predictions within each model group
    - Stage 2: Combine group averages using group weights

    This approach ensures methodological diversity:
    - Even if 3 gradient boosting models agree, they only get 25% weight total
    - Prevents overweighting of similar models

    Args:
        predictions: Dictionary of model name -> list of predictions
        group_weights: Optional custom group weights (default from model_groups.py)

    Returns:
        List of stratified ensemble values

    Example:
        If predictions has XGBoost, LightGBM, CatBoost (all ML_GB group):
        - Stage 1: Average them -> single ML_GB prediction
        - Stage 2: Weight ML_GB at 25%, other groups at their weights
    """
    from raglite.forecasting.model_groups import (
        GROUP_WEIGHTS,
        MODEL_TO_GROUP,
        ModelGroup,
    )

    if not predictions:
        return []

    # Use default weights if not provided
    weights = group_weights or GROUP_WEIGHTS

    # Stage 1: Within-group averaging
    group_forecasts: dict[ModelGroup, list[float]] = {}
    group_model_counts: dict[ModelGroup, int] = {}

    for group in ModelGroup:
        # Find models in this group that have predictions
        group_models = [
            model for model, g in MODEL_TO_GROUP.items() if g == group and model in predictions
        ]

        if not group_models:
            continue

        # Get predictions for these models
        group_preds = [predictions[model] for model in group_models]

        # Average across models in this group (element-wise)
        n_periods = len(group_preds[0])
        avg_forecast = []
        for i in range(n_periods):
            period_values = [pred[i] for pred in group_preds if i < len(pred)]
            if period_values:
                avg_forecast.append(sum(period_values) / len(period_values))

        if avg_forecast:
            group_forecasts[group] = avg_forecast
            group_model_counts[group] = len(group_models)

    if not group_forecasts:
        return []

    # Stage 2: Cross-group weighted average
    total_weight = sum(weights.get(g, 0.0) for g in group_forecasts.keys())
    if total_weight == 0:
        # Equal weight if no weights defined
        total_weight = len(group_forecasts)
        weights = dict.fromkeys(group_forecasts.keys(), 1.0)

    # Determine forecast length
    n_periods = max(len(f) for f in group_forecasts.values())
    ensemble = [0.0] * n_periods

    for group, forecast in group_forecasts.items():
        group_weight = weights.get(group, 0.0) / total_weight
        for i in range(min(len(forecast), n_periods)):
            ensemble[i] += forecast[i] * group_weight

    logger.info(
        "Stratified ensemble calculated",
        extra={
            "groups_used": [g.value for g in group_forecasts.keys()],
            "models_per_group": {g.value: c for g, c in group_model_counts.items()},
            "total_weight": total_weight,
        },
    )

    return ensemble


def build_ensemble_result(
    metric: str,
    historical_data: TimeSeriesData,
    forecast_points: list[ForecastPoint],
    successful_models: list[str],
    predictions: dict[str, list[float]],
    weights: dict[str, float],
    combined_metrics: dict[str, float],
    selected: list[str],
    periods_ahead: int,
) -> ForecastResult:
    """Build final ForecastResult object for ensemble.

    Args:
        metric: Metric name
        historical_data: Historical time-series data
        forecast_points: Forecast points with CI
        successful_models: List of successful model names
        predictions: Individual model predictions
        weights: Model weights
        combined_metrics: Aggregated accuracy metrics
        selected: Selected regressor names
        periods_ahead: Number of periods forecasted

    Returns:
        Complete ForecastResult object
    """
    basis_text = f"Ensemble of {len(successful_models)} models"
    if selected:
        basis_text += f" with {len(selected)} regressors"

    return ForecastResult(
        metric_name=metric,
        historical_data=historical_data.points,
        forecast=forecast_points,
        model_type="ensemble",
        ensemble_models=successful_models,
        individual_predictions=predictions,
        ensemble_weights={k: weights.get(k, 0.0) for k in successful_models},
        accuracy_metrics=combined_metrics,
        regressors_used=selected,
        basis=basis_text,
        accuracy_estimate="±15% (NFR10 target)",
        periods_ahead=periods_ahead,
    )
