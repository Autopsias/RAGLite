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

from typing import TYPE_CHECKING, Any, cast

import pandas as pd

if TYPE_CHECKING:
    from pytorch_forecasting import TemporalFusionTransformer

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
            import torch
            from pytorch_forecasting import TemporalFusionTransformer

            try:
                logger.info(f"Loading TFT model from {checkpoint_entry.checkpoint_path}...")
                # Security: Validate checkpoint path before loading
                if not checkpoint_entry.checkpoint_path or not isinstance(
                    checkpoint_entry.checkpoint_path, str
                ):
                    raise ValueError("Invalid checkpoint path")
                if not checkpoint_entry.checkpoint_path.endswith(".ckpt"):
                    raise ValueError("Checkpoint must be .ckpt file")

                # Load checkpoint with weights_only=False for custom PyTorch Forecasting format
                checkpoint = torch.load(  # nosec B614 - Required for PyTorch Forecasting custom checkpoint format
                    checkpoint_entry.checkpoint_path,
                    map_location="cpu",
                    weights_only=False,
                )
                # Create model from hparams and load state dict
                _tft_model = TemporalFusionTransformer(**checkpoint["hparams"])
                _tft_model.load_state_dict(checkpoint["state_dict"])
                _tft_checkpoint_path = checkpoint_entry.checkpoint_path
                logger.info("TFT model loaded successfully")
            except Exception as load_error:
                # AC5: Fallback to previous checkpoint if current fails
                logger.warning(
                    f"Failed to load active checkpoint: {load_error}. Trying previous checkpoints..."
                )

                # Get checkpoint history (excluding the failed active one)
                history = storage.get_model_history("tft", limit=5)
                for prev_checkpoint in history:
                    if prev_checkpoint.checkpoint_path == checkpoint_entry.checkpoint_path:
                        continue  # Skip the one that just failed

                    try:
                        logger.info(
                            f"Attempting fallback checkpoint: {prev_checkpoint.checkpoint_path}"
                        )
                        # Security: Validate checkpoint path before loading
                        if not prev_checkpoint.checkpoint_path or not isinstance(
                            prev_checkpoint.checkpoint_path, str
                        ):
                            raise ValueError("Invalid checkpoint path")
                        if not prev_checkpoint.checkpoint_path.endswith(".ckpt"):
                            raise ValueError("Checkpoint must be .ckpt file")

                        # Load checkpoint with weights_only=False for custom PyTorch Forecasting format
                        checkpoint = torch.load(  # nosec B614 - Required for PyTorch Forecasting custom checkpoint format
                            prev_checkpoint.checkpoint_path,
                            map_location="cpu",
                            weights_only=False,
                        )
                        _tft_model = TemporalFusionTransformer(**checkpoint["hparams"])
                        _tft_model.load_state_dict(checkpoint["state_dict"])
                        _tft_checkpoint_path = prev_checkpoint.checkpoint_path
                        logger.info(
                            f"Successfully loaded fallback checkpoint (version: {prev_checkpoint.model_version})"
                        )
                        break
                    except Exception as fallback_error:
                        logger.warning(
                            f"Fallback checkpoint {prev_checkpoint.checkpoint_path} also failed: {fallback_error}"
                        )
                        continue

                if _tft_model is None:
                    logger.error("All TFT checkpoints failed to load")
                    return None

        except ImportError as e:
            raise ImportError(
                "TFT requires 'pytorch-forecasting' package. Install with: uv sync --all-groups"
            ) from e
        except Exception as e:
            logger.error(f"Failed to load TFT model: {e}")
            return None
    return cast("TemporalFusionTransformer | None", _tft_model)


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
        # TFT requires TimeSeriesDataSet format with time_idx, group_ids, target
        from pytorch_forecasting import TimeSeriesDataSet

        # Create DataFrame in TFT format
        df = pd.DataFrame(
            {
                "time_idx": range(len(y)),
                "metric_name": "target_metric",  # Single group for now
                "value": y.values,
            }
        )

        # Create minimal TimeSeriesDataSet for prediction
        # Use same parameters as training (from TFT_TRAINING_CONFIG)
        max_encoder_length = 12  # From settings.tft_encoder_length
        max_prediction_length = periods_ahead

        # Need sufficient history for encoder
        if len(y) < max_encoder_length:
            logger.warning(f"Insufficient data for TFT (need {max_encoder_length}, have {len(y)})")
            return None

        # Create dataset for inference
        # Use last max_encoder_length points as context
        dataset = TimeSeriesDataSet(
            df,
            time_idx="time_idx",
            target="value",
            group_ids=["metric_name"],
            min_encoder_length=max_encoder_length,
            max_encoder_length=max_encoder_length,
            min_prediction_length=1,
            max_prediction_length=max_prediction_length,
            add_relative_time_idx=True,
            add_target_scales=True,
            add_encoder_length=True,
            time_varying_known_reals=[],
            time_varying_unknown_reals=[],
            static_categoricals=[],
        )

        # Generate predictions
        dataloader = dataset.to_dataloader(train=False, batch_size=1, num_workers=0)

        # Force CPU inference to avoid MPS memory allocation issues
        import torch

        device = torch.device("cpu")
        model = model.to(device)
        model.eval()

        # Get predictions from model (using Trainer for consistent behavior)
        import lightning.pytorch as pl

        trainer = pl.Trainer(accelerator="cpu", logger=False, enable_progress_bar=False)
        predictions = trainer.predict(model, dataloader)

        # Extract point forecast (median quantile, index 3 out of 7 quantiles)
        # TFT outputs quantiles: [0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98]
        # trainer.predict returns a list of batch predictions
        if predictions and len(predictions) > 0:
            batch_pred = predictions[0]  # First batch
            if hasattr(batch_pred, "prediction"):
                # Raw output format
                point_forecast = batch_pred.prediction[0, :, 3].cpu().numpy().tolist()
            elif isinstance(batch_pred, dict) and "prediction" in batch_pred:
                point_forecast = batch_pred["prediction"][0, :, 3].cpu().numpy().tolist()
            else:
                # Tensor output - check if it's actually a tensor-like object
                if hasattr(batch_pred, "shape") and hasattr(batch_pred, "cpu"):
                    # Tensor-like object (e.g., torch.Tensor)
                    try:
                        # MyPy can't infer this is a tensor, so we need to cast it
                        point_forecast = batch_pred[0, :, 3].cpu().numpy().tolist()  # type: ignore[call-overload]
                    except (IndexError, TypeError) as e:
                        logger.warning(f"Failed to extract tensor data: {e}")
                        return None
                elif hasattr(batch_pred, "__getitem__") and isinstance(batch_pred, list):
                    # List output
                    try:
                        point_forecast = (
                            batch_pred[0][3] if isinstance(batch_pred[0], list) else batch_pred[0]
                        )
                    except (IndexError, TypeError) as e:
                        logger.warning(f"Failed to extract list data: {e}")
                        return None
                else:
                    logger.warning("Unexpected batch_pred format for tensor output")
                    return None
        else:
            logger.warning("TFT prediction returned empty results")
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
