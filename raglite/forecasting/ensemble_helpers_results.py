"""Result building and aggregation for ensemble forecasting.

Extracted from ensemble_helpers.py (Story 8 refactoring).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData


def build_forecast_points(
    ensemble_values: list[float],
    prophet_result: ForecastResult | None,
    df: pd.DataFrame,
    periods_ahead: int,
) -> list[ForecastPoint]:
    """Build forecast points from ensemble values.

    Args:
        ensemble_values: Weighted ensemble predictions
        prophet_result: Prophet result (if available) for CI
        df: Historical DataFrame
        periods_ahead: Number of periods

    Returns:
        List of ForecastPoint objects
    """
    if prophet_result:
        return [
            ForecastPoint(
                date=p.date,
                value=ensemble_values[i] if i < len(ensemble_values) else p.value,
                lower=p.lower,
                upper=p.upper,
                label=p.label,
            )
            for i, p in enumerate(prophet_result.forecast)
        ]

    # Build from scratch (no Prophet available)
    last_date = df["ds"].max()
    forecast_points = []
    for i in range(periods_ahead):
        next_date = last_date + pd.DateOffset(months=3 * (i + 1))
        quarter = (next_date.month - 1) // 3 + 1
        label = f"Q{quarter} {next_date.year}"
        value = ensemble_values[i] if i < len(ensemble_values) else 0.0
        forecast_points.append(
            ForecastPoint(
                date=next_date.to_pydatetime(),
                value=value,
                lower=value * 0.8,
                upper=value * 1.2,
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
