"""Chronos-2 zero-shot forecasting model.

Story 6.13: Chronos-2 integration for cold-start scenarios.
Story 7.5 Task 7: Extracted from hybrid.py to separate module.

This module provides Chronos-2 foundation model forecasting capabilities:
- Zero-shot forecasting (no training required)
- Cold-start scenarios with as few as 3 data points
- Pre-trained on diverse time-series datasets
- 250x faster than original Chronos (using Chronos-Bolt)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from chronos import BaseChronosPipeline

from raglite.forecasting.models.base import InsufficientDataError
from raglite.shared.logging import get_logger
from raglite.shared.models import ForecastPoint, ForecastResult, TimeSeriesData

logger = get_logger(__name__)

# Story 6.13: Lazy-load Chronos-2 pipeline to avoid import-time penalty
# Chronos-2 model loading takes 10-30s on first use, cache singleton
_chronos_pipeline: BaseChronosPipeline | None = None


def _get_chronos_pipeline() -> BaseChronosPipeline:
    """Lazy-load Chronos-2 pipeline on first use.

    Story 6.13 AC1, AC5: Singleton pattern for model caching.
    Uses amazon/chronos-bolt-small (250x faster than original Chronos).

    Returns:
        Chronos-2 pipeline instance (cached after first load)

    Raises:
        ImportError: If chronos-forecasting package not installed
    """
    global _chronos_pipeline
    if _chronos_pipeline is None:
        try:
            from chronos import BaseChronosPipeline

            logger.info("Loading Chronos-2 model (first use, 10-30s)...")
            _chronos_pipeline = BaseChronosPipeline.from_pretrained(
                "amazon/chronos-bolt-small",
                device_map="cpu",  # GPU optional via future config
            )
            logger.info("Chronos-2 model loaded successfully")
        except ImportError as e:
            raise ImportError(
                "Chronos-2 requires 'chronos-forecasting' package. "
                "Install with: uv sync --all-groups"
            ) from e
    return cast("BaseChronosPipeline", _chronos_pipeline)


async def generate_chronos_cold_start_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int = 4,
) -> ForecastResult:
    """Generate zero-shot forecast using Chronos-2 for cold-start scenarios.

    Story 6.13 AC2: Cold-start path when historical_data < MIN_DATA_POINTS.
    Uses Chronos-2 foundation model which requires NO training and works
    with as few as 3 data points.

    Args:
        metric: Metric name
        historical_data: Time-series data (3-5 points typically)
        periods_ahead: Number of periods to forecast

    Returns:
        ForecastResult with Chronos-2 zero-shot predictions and confidence intervals

    Raises:
        InsufficientDataError: If <3 data points (absolute minimum for Chronos-2)
    """
    import torch

    # Input validation: Check for empty data
    if historical_data is None or len(historical_data.points) == 0:
        raise InsufficientDataError("minimum 3 data points. Got 0.")

    if len(historical_data.points) < 3:
        raise InsufficientDataError(f"minimum 3 data points. Got {len(historical_data.points)}.")

    # Input validation: Check for NaN values
    values = [float(p.value) for p in historical_data.points]
    if all(np.isnan(v) for v in values):
        raise InsufficientDataError(
            f"Chronos-2 received all-NaN values. Got {len(values)} NaN values."
        )

    logger.info(
        "Cold-start path: using Chronos-2 zero-shot",
        extra={
            "metric": metric,
            "data_points": len(historical_data.points),
            "periods_ahead": periods_ahead,
        },
    )

    # Load Chronos-2 pipeline (cached singleton)
    pipeline = _get_chronos_pipeline()

    # Prepare input tensor from historical data
    inputs = torch.tensor(values, dtype=torch.float32).unsqueeze(0)  # Shape: (1, T)

    # Generate forecast with prediction intervals
    # Chronos-Bolt uses simplified API: predict(inputs, prediction_length)
    forecast = pipeline.predict(
        inputs=inputs,
        prediction_length=periods_ahead,
    )

    # Extract quantiles from forecast tensor
    # forecast shape: (1, num_samples, prediction_length)
    forecast_samples = forecast.squeeze(0).numpy()  # Shape: (num_samples, prediction_length)

    # Calculate quantiles: 10% (lower), 50% (median), 90% (upper)
    lower_bound = np.percentile(forecast_samples, 10, axis=0).tolist()  # 10th percentile
    median_forecast = np.percentile(forecast_samples, 50, axis=0).tolist()  # Median
    upper_bound = np.percentile(forecast_samples, 90, axis=0).tolist()  # 90th percentile

    # Generate future dates
    last_date = historical_data.points[-1].date
    forecast_dates = pd.date_range(start=last_date, periods=periods_ahead + 1, freq="MS")[1:]

    # Build forecast points with confidence intervals
    forecast_points = [
        ForecastPoint(
            date=forecast_dates[i].to_pydatetime(),
            value=float(median_forecast[i]),
            lower=float(lower_bound[i]),
            upper=float(upper_bound[i]),
            label=f"{forecast_dates[i].strftime('%b-%y')}",
        )
        for i in range(periods_ahead)
    ]

    return ForecastResult(
        metric_name=metric,
        forecast=forecast_points,
        model_type="chronos-2-zero-shot",
        confidence_reasoning=(
            f"Zero-shot forecast using Chronos-2 foundation model. "
            f"Cold-start scenario with only {len(historical_data.points)} data points. "
            f"Chronos-2 is pre-trained on diverse time-series datasets and requires no training. "
            f"Wider confidence intervals reflect limited historical context."
        ),
        basis=f"Chronos-2 zero-shot model (cold-start with {len(historical_data.points)} data points)",
        periods_ahead=periods_ahead,
        ensemble_weights={"chronos": 1.0},  # 100% Chronos-2 for cold-start
    )


def _validate_chronos_input(
    y: pd.Series,
    external_regressors: pd.DataFrame | None,
    periods_ahead: int,
) -> bool:
    """Validate Chronos-2 input data.

    Args:
        y: Target time-series values
        external_regressors: Optional external covariates
        periods_ahead: Number of periods to forecast

    Returns:
        True if input is valid, False otherwise
    """
    if y is None or len(y) == 0:
        logger.warning("Chronos-2 received empty input array", extra={"data_points": 0})
        return False

    if y.isna().all():
        logger.warning(
            "Chronos-2 received all-NaN input",
            extra={"data_points": len(y), "nan_count": y.isna().sum()},
        )
        return False

    logger.info(
        "Starting Chronos-2 inference",
        extra={
            "data_points": len(y),
            "periods_ahead": periods_ahead,
            "has_regressors": external_regressors is not None,
        },
    )
    return True


def _execute_chronos_inference(
    y: pd.Series,
    periods_ahead: int,
) -> np.ndarray:
    """Execute Chronos-2 inference and return median forecast.

    Args:
        y: Target time-series values
        periods_ahead: Number of periods to forecast

    Returns:
        Median forecast values as numpy array
    """
    import time

    import torch

    from raglite.shared.config import settings

    start_time = time.time()

    # Load Chronos-2 pipeline (cached singleton)
    pipeline = _get_chronos_pipeline()

    # Prepare input tensor
    inputs = torch.tensor(y.values, dtype=torch.float32).unsqueeze(0)  # Shape: (1, T)

    # Generate forecast (zero-shot, no training)
    # Chronos-Bolt uses simplified API: predict(inputs, prediction_length)
    # NOTE: Chronos-2 DOES support covariates in v2.0+, but we use simple
    # time-series only for ensemble consistency. Future story can add covariates.
    forecast = pipeline.predict(
        inputs=inputs,
        prediction_length=periods_ahead,
    )

    # Extract median forecast (50th percentile)
    forecast_samples = forecast.squeeze(0).numpy()  # Shape: (num_samples, prediction_length)
    median_forecast: np.ndarray = np.percentile(forecast_samples, 50, axis=0)

    # Calculate elapsed time
    elapsed = time.time() - start_time

    # Log completion with timing (AC6: timeout monitoring)
    logger.info(
        "Chronos-2 inference completed",
        extra={
            "elapsed_seconds": round(elapsed, 3),
            "periods_ahead": periods_ahead,
            "timeout_threshold": settings.chronos_inference_timeout,
        },
    )

    # Warn if inference exceeded timeout threshold (AC6)
    if elapsed > settings.chronos_inference_timeout:
        logger.warning(
            "Chronos-2 inference exceeded timeout threshold",
            extra={
                "elapsed_seconds": round(elapsed, 3),
                "timeout_threshold": settings.chronos_inference_timeout,
                "overage_seconds": round(elapsed - settings.chronos_inference_timeout, 3),
            },
        )

    return median_forecast


def fit_and_forecast_chronos(
    y: pd.Series,
    periods_ahead: int,
    external_regressors: pd.DataFrame | None = None,
) -> dict[str, Any] | None:
    """Generate Chronos-2 forecast (for ThreadPoolExecutor).

    Story 6.13 AC3, AC4: Zero-shot forecasting with optional covariates.
    Chronos-2 requires NO training - it's a pre-trained foundation model.

    Args:
        y: Target time-series values
        periods_ahead: Number of periods to forecast
        external_regressors: Optional external covariates (NOT USED in initial implementation)

    Returns:
        Dict with 'values' list and 'metrics' dict, or None if inference fails
    """
    # Input validation
    if not _validate_chronos_input(y, external_regressors, periods_ahead):
        return None

    try:
        # Execute inference
        median_forecast = _execute_chronos_inference(y, periods_ahead)

        # Return format matching other models
        return {
            "values": median_forecast.tolist(),
            "metrics": {},  # Zero-shot model has no training metrics
        }

    except Exception as e:
        logger.error(
            "Chronos-2 inference failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "data_points": len(y),
                "periods_ahead": periods_ahead,
            },
        )
        return None  # Graceful fallback - None indicates model failure
