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
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet

from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Story 6.14: Lazy-load TFT model from checkpoint on first use
# TFT model loading takes <30s on first use, cache singleton
_tft_model: TemporalFusionTransformer | None = None
_tft_checkpoint_path: str | None = None


def _validate_checkpoint_path(checkpoint_path: str | None) -> None:
    """Validate checkpoint path security constraints.

    Args:
        checkpoint_path: Path to checkpoint file

    Raises:
        ValueError: If checkpoint path is invalid
    """
    if not checkpoint_path or not isinstance(checkpoint_path, str):
        raise ValueError("Invalid checkpoint path")
    if not checkpoint_path.endswith(".ckpt"):
        raise ValueError("Checkpoint must be .ckpt file")


def _load_checkpoint_from_file(checkpoint_path: str) -> dict[str, Any]:
    """Load PyTorch checkpoint file with validation.

    Args:
        checkpoint_path: Path to .ckpt file

    Returns:
        Checkpoint dictionary with state_dict and hparams
    """
    import torch

    # Load checkpoint with weights_only=False for custom PyTorch Forecasting format
    checkpoint = torch.load(  # nosec B614 - Required for PyTorch Forecasting custom checkpoint format
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )
    return checkpoint  # type: ignore[no-any-return]


def _create_tft_model_from_checkpoint(
    checkpoint: dict[str, Any], checkpoint_path: str
) -> TemporalFusionTransformer:
    """Create TFT model instance from checkpoint dictionary.

    Args:
        checkpoint: Loaded checkpoint dictionary
        checkpoint_path: Original checkpoint path (for logging)

    Returns:
        Initialized TFT model in evaluation mode
    """
    from pytorch_forecasting import TemporalFusionTransformer

    # Try Lightning-style loading first, fall back to manual if needed
    hparams = checkpoint.get("hyper_parameters", checkpoint.get("hparams", {}))
    if not hparams:
        raise ValueError("Checkpoint missing hyper_parameters/hparams")

    # Create model from hparams and load state dict
    model = TemporalFusionTransformer(**hparams)
    model.load_state_dict(checkpoint["state_dict"])
    model.train(False)  # Set to evaluation mode (equivalent to .eval())
    return model


def _try_load_active_checkpoint(checkpoint_path: str) -> TemporalFusionTransformer | None:
    """Attempt to load active checkpoint with error handling.

    Args:
        checkpoint_path: Path to active checkpoint

    Returns:
        Loaded TFT model or None if loading failed
    """
    try:
        logger.info(f"Loading TFT model from {checkpoint_path}...")
        _validate_checkpoint_path(checkpoint_path)
        checkpoint = _load_checkpoint_from_file(checkpoint_path)
        model = _create_tft_model_from_checkpoint(checkpoint, checkpoint_path)
        logger.info("TFT model loaded successfully")
        return model
    except Exception as e:
        logger.warning(f"Failed to load active checkpoint: {e}")
        return None


def _try_fallback_checkpoints(
    storage: Any, failed_checkpoint_path: str
) -> TemporalFusionTransformer | None:
    """Attempt to load fallback checkpoints after active fails.

    Args:
        storage: ExternalDataStorage instance
        failed_checkpoint_path: Path that already failed

    Returns:
        Loaded TFT model or None if all failed
    """

    from pytorch_forecasting import TemporalFusionTransformer

    logger.warning("Trying previous checkpoints...")

    # Get checkpoint history (excluding the failed active one)
    history = storage.get_model_history("tft", limit=5)
    for prev_checkpoint in history:
        if prev_checkpoint.checkpoint_path == failed_checkpoint_path:
            continue  # Skip the one that just failed

        try:
            logger.info(f"Attempting fallback checkpoint: {prev_checkpoint.checkpoint_path}")
            _validate_checkpoint_path(prev_checkpoint.checkpoint_path)
            checkpoint = _load_checkpoint_from_file(prev_checkpoint.checkpoint_path)
            model = TemporalFusionTransformer(**checkpoint["hparams"])
            model.load_state_dict(checkpoint["state_dict"])
            logger.info(
                f"Successfully loaded fallback checkpoint (version: {prev_checkpoint.model_version})"
            )
            return model
        except Exception as e:
            logger.warning(
                f"Fallback checkpoint {prev_checkpoint.checkpoint_path} also failed: {e}"
            )
            continue

    logger.error("All TFT checkpoints failed to load")
    return None


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
            model = _try_load_active_checkpoint(checkpoint_entry.checkpoint_path)

            # AC5: Fallback to previous checkpoint if current fails
            if model is None:
                model = _try_fallback_checkpoints(storage, checkpoint_entry.checkpoint_path)

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


def _prepare_tft_dataframe(y: pd.Series) -> pd.DataFrame:
    """Prepare DataFrame in TFT format with time_idx and group_ids.

    Args:
        y: Target time-series values

    Returns:
        DataFrame with time_idx, metric_name, and value columns
    """
    df = pd.DataFrame(
        {
            "time_idx": range(len(y)),
            "metric_name": "target_metric",  # Single group for now
            "value": y.values,
        }
    )
    return df


def _create_tft_dataset(
    df: pd.DataFrame, max_encoder_length: int, max_prediction_length: int
) -> TimeSeriesDataSet | None:
    """Create TimeSeriesDataSet for TFT inference.

    Args:
        df: Input DataFrame in TFT format
        max_encoder_length: Encoder sequence length
        max_prediction_length: Prediction sequence length

    Returns:
        TimeSeriesDataSet or None if insufficient data
    """
    from pytorch_forecasting import TimeSeriesDataSet

    # Need sufficient history for encoder + prediction
    # TimeSeriesDataSet requires encoder_length + prediction_length + 1 points minimum
    min_required = max_encoder_length + max_prediction_length + 1
    if len(df) < min_required:
        logger.warning(f"Insufficient data for TFT (need {min_required}, have {len(df)})")
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
    return dataset


def _extract_point_forecast(output: Any) -> list[float] | None:
    """Extract point forecast (median quantile) from TFT model output.

    Args:
        output: Raw TFT model output

    Returns:
        List of forecast values or None if extraction failed
    """
    # Extract point forecast (median quantile, index 3 out of 7 quantiles)
    # TFT outputs quantiles: [0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98]
    if hasattr(output, "prediction"):
        pred = output.prediction
    elif isinstance(output, dict) and "prediction" in output:
        pred = output["prediction"]
    else:
        pred = output

    # Extract median (index 3) from quantiles
    return pred[0, :, 3].cpu().numpy().tolist()  # type: ignore[no-any-return]


def _run_tft_inference(model: TemporalFusionTransformer, dataloader: Any) -> list[float] | None:
    """Run TFT model inference on dataloader.

    Args:
        model: Loaded TFT model
        dataloader: TimeSeriesDataSet dataloader

    Returns:
        List of forecast values or None if inference failed
    """
    import torch

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

            # Extract median forecast
            point_forecast = _extract_point_forecast(output)
            if point_forecast is None:
                logger.warning("TFT prediction returned empty results")
                return None

            break  # Only need first batch

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
        model = _get_tft_model()
        if model is None:
            logger.warning("No TFT checkpoint available - skipping TFT forecast")
            return None

        # Prepare data for TFT inference
        df = _prepare_tft_dataframe(y)

        # Create TimeSeriesDataSet for prediction
        # Use same parameters as training (from TFT_TRAINING_CONFIG)
        max_encoder_length = 12  # From settings.tft_encoder_length
        max_prediction_length = periods_ahead

        dataset = _create_tft_dataset(df, max_encoder_length, max_prediction_length)
        if dataset is None:
            return None

        # Generate predictions
        dataloader = dataset.to_dataloader(train=False, batch_size=1, num_workers=0)
        point_forecast = _run_tft_inference(model, dataloader)
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
        df = _prepare_tft_dataframe(y)

        # Create TimeSeriesDataSet for prediction
        max_encoder_length = 12  # From settings.tft_encoder_length
        max_prediction_length = periods_ahead

        dataset = _create_tft_dataset(df, max_encoder_length, max_prediction_length)
        if dataset is None:
            return None

        # Generate predictions
        dataloader = dataset.to_dataloader(train=False, batch_size=1, num_workers=0)
        point_forecast = _run_tft_inference(model, dataloader)
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
