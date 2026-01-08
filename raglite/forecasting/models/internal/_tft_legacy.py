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

from raglite.forecasting.models.internal._forecasting import (
    _generate_tft_predictions,
    _prepare_tft_dataset,
)
from raglite.forecasting.models.internal._model_loader import (
    _load_checkpoint_from_path,
    _try_fallback_checkpoints,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Story 6.14: Lazy-load TFT model from checkpoint on first use
# TFT model loading takes <30s on first use, cache singleton
_tft_model: TemporalFusionTransformer | None = None
_tft_checkpoint_path: str | None = None


def _get_tft_model() -> TemporalFusionTransformer | None:
    """Lazy-load TFT model from checkpoint on first use.

    Story 6.14 AC1, AC7: Singleton pattern for model caching.
    Returns None if no trained checkpoint available (graceful degradation).

    Returns:
        TFT model instance (cached after first load), or None if unavailable

    Raises:
        ImportError: If pytorch-forecasting package not installed
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
            try:
                _tft_model = _load_checkpoint_from_path(checkpoint_entry.checkpoint_path)
                if _tft_model is not None:
                    _tft_checkpoint_path = checkpoint_entry.checkpoint_path
                    return _tft_model
            except Exception as load_error:
                # AC5: Fallback to previous checkpoint if current fails
                logger.warning(
                    f"Failed to load active checkpoint: {load_error}. Trying previous checkpoints..."
                )

                # Get checkpoint history (excluding the failed active one)
                history = storage.get_model_history("tft", limit=5)
                _tft_model = _try_fallback_checkpoints(
                    storage, history, checkpoint_entry.checkpoint_path
                )

                if _tft_model is not None:
                    # Update checkpoint path to the fallback that worked
                    for prev_checkpoint in history:
                        if prev_checkpoint.checkpoint_path != checkpoint_entry.checkpoint_path:
                            _tft_checkpoint_path = prev_checkpoint.checkpoint_path
                            break
                    return _tft_model

                logger.error("All TFT checkpoints failed to load")
                return None

        except ImportError as e:
            raise ImportError(
                "TFT requires 'pytorch-forecasting' package. Install with: uv sync --all-groups"
            ) from e
        except Exception as e:
            logger.error(f"Failed to load TFT model: {e}")
            return None
    return _tft_model


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
        # Returns None if no trained checkpoint available (graceful degradation)
        model = _get_tft_model()

        if model is None:
            logger.warning("No TFT checkpoint available - skipping TFT forecast")
            return None

        # Prepare data for TFT inference
        dataset = _prepare_tft_dataset(y, periods_ahead)
        if dataset is None:
            return None

        # Generate predictions
        point_forecast = _generate_tft_predictions(model, dataset)
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
