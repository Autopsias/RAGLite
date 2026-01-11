"""TFT model loading utilities.

Story 6.14: Model checkpoint loading with graceful degradation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pytorch_forecasting import TemporalFusionTransformer

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _load_checkpoint_from_path(checkpoint_path: str) -> TemporalFusionTransformer | None:
    """Load TFT model from a single checkpoint path.

    Args:
        checkpoint_path: Path to .ckpt checkpoint file

    Returns:
        Loaded TFT model or None if loading fails
    """
    import torch
    from pytorch_forecasting import TemporalFusionTransformer

    try:
        logger.info(f"Loading TFT model from {checkpoint_path}...")

        # Security: Validate checkpoint path before loading
        if not checkpoint_path or not isinstance(checkpoint_path, str):
            raise ValueError("Invalid checkpoint path")
        if not checkpoint_path.endswith(".ckpt"):
            raise ValueError("Checkpoint must be .ckpt file")

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
        model.train(False)  # Set to evaluation mode

        logger.info("TFT model loaded successfully")
        return model

    except Exception as e:
        logger.warning(f"Failed to load checkpoint from {checkpoint_path}: {e}")
        return None


def _try_fallback_checkpoints(
    storage: Any, history: Any, active_path: str
) -> TemporalFusionTransformer | None:
    """Try loading from previous checkpoint versions.

    Args:
        storage: ExternalDataStorage instance
        history: List of previous checkpoint entries
        active_path: Path that already failed (skip this one)

    Returns:
        Loaded TFT model or None if all fail
    """
    import torch
    from pytorch_forecasting import TemporalFusionTransformer

    for prev_checkpoint in history:
        if prev_checkpoint.checkpoint_path == active_path:
            continue  # Skip the one that just failed

        try:
            logger.info(f"Attempting fallback checkpoint: {prev_checkpoint.checkpoint_path}")

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

            model = TemporalFusionTransformer(**checkpoint["hparams"])
            model.load_state_dict(checkpoint["state_dict"])
            logger.info(
                f"Successfully loaded fallback checkpoint "
                f"(version: {prev_checkpoint.model_version})"
            )
            return model

        except Exception as fallback_error:
            logger.warning(
                f"Fallback checkpoint {prev_checkpoint.checkpoint_path} also "
                f"failed: {fallback_error}"
            )
            continue

    logger.error("All TFT checkpoints failed to load")
    return None
