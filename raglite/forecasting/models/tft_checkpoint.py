"""TFT checkpoint loading and management utilities.

Story 7.5: Extracted from tft_model.py for modularization.
This module handles checkpoint validation, loading, and fallback logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from pytorch_forecasting import TemporalFusionTransformer

logger = get_logger(__name__)


def validate_checkpoint_path(checkpoint_path: str | None) -> None:
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


def load_checkpoint_from_file(checkpoint_path: str) -> dict[str, Any]:
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


def create_tft_model_from_checkpoint(
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


def try_load_active_checkpoint(checkpoint_path: str) -> TemporalFusionTransformer | None:
    """Attempt to load active checkpoint with error handling.

    Args:
        checkpoint_path: Path to active checkpoint

    Returns:
        Loaded TFT model or None if loading failed
    """
    try:
        logger.info(f"Loading TFT model from {checkpoint_path}...")
        validate_checkpoint_path(checkpoint_path)
        checkpoint = load_checkpoint_from_file(checkpoint_path)
        model = create_tft_model_from_checkpoint(checkpoint, checkpoint_path)
        logger.info("TFT model loaded successfully")
        return model
    except Exception as e:
        logger.warning(f"Failed to load active checkpoint: {e}")
        return None


def try_fallback_checkpoints(
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
            validate_checkpoint_path(prev_checkpoint.checkpoint_path)
            checkpoint = load_checkpoint_from_file(prev_checkpoint.checkpoint_path)
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
