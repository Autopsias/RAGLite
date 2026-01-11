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
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet

from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Story 6.14: Lazy-load TFT model from checkpoint on first use
# TFT model loading takes <30s on first use, cache singleton
_tft_model: TemporalFusionTransformer | None = None
_tft_checkpoint_path: str | None = None


def _validate_checkpoint_path(checkpoint_path: str) -> None:
    """Validate checkpoint path security.

    Args:
        checkpoint_path: Path to checkpoint file

    Raises:
        ValueError: If path is invalid
    """
    if not checkpoint_path or not isinstance(checkpoint_path, str):
        raise ValueError("Invalid checkpoint path")
    if not checkpoint_path.endswith(".ckpt"):
        raise ValueError("Checkpoint must be .ckpt file")


def _load_tft_from_checkpoint(checkpoint_path: str) -> TemporalFusionTransformer:
    """Load TFT model from checkpoint file.

    Args:
        checkpoint_path: Path to checkpoint file

    Returns:
        Loaded TFT model

    Raises:
        ValueError: If checkpoint is invalid
    """
    import torch
    from pytorch_forecasting import TemporalFusionTransformer

    _validate_checkpoint_path(checkpoint_path)

    # Load checkpoint with weights_only=False for custom PyTorch Forecasting format
    checkpoint = torch.load(  # nosec B614 - Required for PyTorch Forecasting custom checkpoint format
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )
    # Try Lightning-style loading first, fall back to manual if needed
    hparams = checkpoint.get("hyper_parameters", checkpoint.get("hparams", {}))
    if not hparams:
        raise ValueError("Checkpoint missing hyper_parameters/hparams")

    # Create model from hparams and load state dict
    model = TemporalFusionTransformer(**hparams)
    model.load_state_dict(checkpoint["state_dict"])
    model.train(False)  # Set to evaluation mode (equivalent to .eval())
    return model


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
                logger.info(f"Loading TFT model from {checkpoint_entry.checkpoint_path}...")
                _tft_model = _load_tft_from_checkpoint(checkpoint_entry.checkpoint_path)
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
                        _tft_model = _load_tft_from_checkpoint(prev_checkpoint.checkpoint_path)
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


def _prepare_tft_dataset(y: pd.Series, periods_ahead: int) -> TimeSeriesDataSet | None:
    """Prepare TimeSeriesDataSet for TFT inference.

    Args:
        y: Target time-series values
        periods_ahead: Number of periods to forecast

    Returns:
        TimeSeriesDataSet ready for inference, or None if insufficient data
    """
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

    # Need sufficient history for encoder + prediction
    # TimeSeriesDataSet requires encoder_length + prediction_length + 1 points minimum
    min_required = max_encoder_length + max_prediction_length + 1
    if len(y) < min_required:
        logger.warning(f"Insufficient data for TFT (need {min_required}, have {len(y)})")
        return None

    # Create dataset for inference
    # Use last max_encoder_length points as context
    return TimeSeriesDataSet(
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


def _run_tft_inference(
    model: TemporalFusionTransformer, dataset: TimeSeriesDataSet
) -> list[float] | None:
    """Run TFT model inference on prepared dataset.

    Args:
        model: Loaded TFT model
        dataset: TimeSeriesDataSet for inference

    Returns:
        List of forecasted values, or None if inference fails
    """
    import torch

    # Type alias for inference result
    point_forecast: list[float] | None = None

    # Generate predictions
    dataloader = dataset.to_dataloader(train=False, batch_size=1, num_workers=0)

    # Force CPU inference to avoid MPS memory allocation issues
    device = torch.device("cpu")
    model = model.to(device)
    model.train(False)  # Set to inference mode

    # Use direct model inference instead of Trainer.predict()
    # This avoids Lightning callback issues
    point_forecast = None
    with torch.no_grad():
        for batch in dataloader:
            x, _ = batch  # x is input dict, y is target

            # Get prediction from model
            output = model(x)

            # Extract point forecast (median quantile, index 3 out of 7 quantiles)
            # TFT outputs quantiles: [0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98]
            if hasattr(output, "prediction"):
                pred = output.prediction
            elif isinstance(output, dict) and "prediction" in output:
                pred = output["prediction"]
            else:
                pred = output

            # Extract median (index 3) from quantiles
            point_forecast = pred[0, :, 3].cpu().numpy().tolist()
            break  # Only need first batch

    if point_forecast is None:
        logger.warning("TFT prediction returned empty results")
        return None

    return point_forecast


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

        # Run inference
        point_forecast = _run_tft_inference(model, dataset)
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
