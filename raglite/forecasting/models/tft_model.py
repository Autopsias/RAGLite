"""Temporal Fusion Transformer (TFT) forecasting model.

Story 6.14: TFT integration for deep learning-based forecasting.
Story 7.5 Task 8: Extracted from hybrid.py to separate module.

This module provides TFT model forecasting capabilities:
- Offline-trained model inference (checkpoint-based)
- Graceful degradation if no checkpoint available
- Fallback to previous checkpoints on load failure
- Attention-based architecture for interpretable forecasts
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from pytorch_forecasting import TemporalFusionTransformer

from raglite.forecasting.models.tft_checkpoint import (
    try_fallback_checkpoints,
    try_load_active_checkpoint,
)
from raglite.forecasting.models.tft_data_prep import (
    create_tft_dataset,
    prepare_tft_dataframe,
    run_tft_inference,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Story 6.14: Lazy-load TFT model from checkpoint on first use
# TFT model loading takes <30s on first use, cache singleton
_tft_model: TemporalFusionTransformer | None = None
_tft_checkpoint_path: str | None = None


def _get_tft_model_sync() -> TemporalFusionTransformer | None:
    """Synchronous TFT model loading (internal use only).

    This is the synchronous implementation that does the actual DB access.
    Use _get_tft_model_with_timeout() for async contexts to avoid blocking.

    Returns:
        TFT model instance or None if unavailable
    """
    global _tft_model, _tft_checkpoint_path
    if _tft_model is None:
        try:
            # Check model_registry for active checkpoint
            from raglite.external_data.storage import ExternalDataStorage
            from raglite.shared.database import get_session

            session = get_session()
            storage = ExternalDataStorage(session)
            checkpoint_entry = storage.get_active_model("tft")

            if checkpoint_entry is None:
                logger.warning("No TFT checkpoint available - skipping TFT in ensemble")
                return None

            # Try to load active checkpoint
            model = try_load_active_checkpoint(checkpoint_entry.checkpoint_path)

            # AC5: Fallback to previous checkpoint if current fails
            if model is None:
                model = try_fallback_checkpoints(storage, checkpoint_entry.checkpoint_path)

            if model is None:
                return None

            _tft_model = model
            _tft_checkpoint_path = checkpoint_entry.checkpoint_path

        except ImportError as e:
            raise ImportError(
                "TFT requires 'pytorch-forecasting' package. Install with: uv sync --all-groups"
            ) from e
        except Exception as e:
            logger.error(f"Failed to load TFT model: {e}")
            return None
    return _tft_model


def _get_tft_model() -> TemporalFusionTransformer | None:
    """Lazy-load TFT model from checkpoint on first use.

    Story 6.14 AC1, AC7: Singleton pattern for model caching.
    Returns None if no trained checkpoint available (graceful degradation).

    NOTE: This function performs synchronous DB access. For async contexts,
    use _get_tft_model_with_timeout() to avoid blocking the event loop.

    Returns:
        TFT model instance (cached after first load), or None if unavailable

    Raises:
        ImportError: If pytorch-forecasting package not installed
    """
    return _get_tft_model_sync()


async def _get_tft_model_with_timeout(timeout: float = 10.0) -> TemporalFusionTransformer | None:
    """Async TFT model loading with timeout protection.

    Wraps the synchronous model loading in an executor to avoid blocking
    the async event loop. Includes timeout to prevent indefinite hangs
    if PostgreSQL is slow or unresponsive.

    Args:
        timeout: Maximum seconds to wait for model loading (default 10s)

    Returns:
        TFT model instance or None if unavailable or timeout
    """
    import asyncio

    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _get_tft_model_sync),
            timeout=timeout,
        )
    except TimeoutError:
        logger.warning(
            "TFT model loading timed out - skipping TFT",
            extra={"timeout_seconds": timeout},
        )
        return None
    except Exception as e:
        logger.error(f"Async TFT model loading failed: {e}")
        return None


def fit_and_forecast_tft(
    y: pd.Series,
    periods_ahead: int,
    external_regressors: pd.DataFrame | None = None,
) -> dict[str, Any] | None:
    """Generate TFT forecast from pre-trained checkpoint (for ThreadPoolExecutor).

    Story 6.14 AC5, AC7: Offline-trained model inference with graceful degradation.
    TFT requires OFFLINE TRAINING - checkpoint must exist in model_registry.

    Args:
        y: Target time-series values
        periods_ahead: Number of periods to forecast
        external_regressors: Optional external covariates (for TFT v2)

    Returns:
        Dict with 'values' list and 'metrics' dict, or None if no checkpoint available
    """
    import time

    logger.info(
        "Starting TFT inference",
        extra={
            "data_points": len(y),
            "periods_ahead": periods_ahead,
            "has_regressors": external_regressors is not None,
        },
    )

    try:
        start_time = time.time()

        # Load TFT model from checkpoint (cached singleton)
        model = _get_tft_model()
        if model is None:
            logger.warning("No TFT checkpoint available - skipping TFT forecast")
            return None

        # Prepare data for TFT inference
        df = prepare_tft_dataframe(y)

        # Create TimeSeriesDataSet for prediction
        # Use same parameters as training (from TFT_TRAINING_CONFIG)
        max_encoder_length = 12  # From settings.tft_encoder_length
        max_prediction_length = periods_ahead

        dataset = create_tft_dataset(df, max_encoder_length, max_prediction_length)
        if dataset is None:
            return None

        # Generate predictions
        dataloader = dataset.to_dataloader(train=False, batch_size=1, num_workers=0)
        point_forecast = run_tft_inference(model, dataloader)
        if point_forecast is None:
            return None

        elapsed = time.time() - start_time

        logger.info(
            "TFT inference complete",
            extra={
                "forecast_length": len(point_forecast),
                "inference_time_ms": elapsed * 1000,
            },
        )

        return {
            "values": point_forecast,
            "metrics": {
                "inference_time_ms": elapsed * 1000,
            },
        }

    except Exception as e:
        logger.error(
            "TFT inference failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "data_points": len(y),
                "periods_ahead": periods_ahead,
            },
        )
        return None  # Graceful fallback - None indicates model failure


def fit_and_forecast_tft_with_model(
    model: TemporalFusionTransformer,
    y: pd.Series,
    periods_ahead: int,
    external_regressors: pd.DataFrame | None = None,
) -> dict[str, Any] | None:
    """Generate TFT forecast using a pre-loaded model (for async contexts).

    This variant accepts a pre-loaded model to avoid synchronous DB access
    during inference. The model should be loaded using _get_tft_model_with_timeout()
    in async contexts.

    Args:
        model: Pre-loaded TFT model instance
        y: Target time-series values
        periods_ahead: Number of periods to forecast
        external_regressors: Optional external covariates (for TFT v2)

    Returns:
        Dict with 'values' list and 'metrics' dict, or None if inference failed
    """
    import time

    logger.info(
        "Starting TFT inference (pre-loaded model)",
        extra={
            "data_points": len(y),
            "periods_ahead": periods_ahead,
            "has_regressors": external_regressors is not None,
        },
    )

    try:
        start_time = time.time()

        # Prepare data for TFT inference
        df = prepare_tft_dataframe(y)

        # Create TimeSeriesDataSet for prediction
        max_encoder_length = 12  # From settings.tft_encoder_length
        max_prediction_length = periods_ahead

        dataset = create_tft_dataset(df, max_encoder_length, max_prediction_length)
        if dataset is None:
            return None

        # Generate predictions
        dataloader = dataset.to_dataloader(train=False, batch_size=1, num_workers=0)
        point_forecast = run_tft_inference(model, dataloader)
        if point_forecast is None:
            return None

        elapsed = time.time() - start_time

        logger.info(
            "TFT inference complete (pre-loaded model)",
            extra={
                "forecast_length": len(point_forecast),
                "inference_time_ms": elapsed * 1000,
            },
        )

        return {
            "values": point_forecast,
            "metrics": {
                "inference_time_ms": elapsed * 1000,
            },
        }

    except Exception as e:
        logger.error(
            "TFT inference failed (pre-loaded model)",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "data_points": len(y),
                "periods_ahead": periods_ahead,
            },
        )
        return None
