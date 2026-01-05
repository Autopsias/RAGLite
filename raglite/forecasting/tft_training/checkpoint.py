"""TFT model checkpoint management functions.

Story 6.14 AC4: Save checkpoint and register in PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from raglite.external_data.storage import ExternalDataStorage
from raglite.shared.config import settings
from raglite.shared.database import get_session
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def save_tft_checkpoint(
    model: Any,  # TemporalFusionTransformer (lazy-loaded)
    metrics: dict[str, float | int | str],
    model_version: str | None = None,
) -> str:
    """Save TFT checkpoint and update model registry.

    Story 6.14 AC4: Save checkpoint and register in PostgreSQL.

    Args:
        model: Trained TFT model
        metrics: Training/validation metrics
        model_version: Version string (defaults to timestamp)

    Returns:
        Path to saved checkpoint
    """
    if model_version is None:
        model_version = datetime.now().strftime("%Y-%m-%d-%H%M%S")

    import torch

    # Create checkpoint directory
    checkpoint_dir = Path(settings.tft_checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Save checkpoint using Lightning's built-in method for proper TFT compatibility
    checkpoint_path = checkpoint_dir / f"tft_{model_version}.ckpt"
    # Use Lightning's save_hyperparameters for full compatibility with load_from_checkpoint
    trainer_checkpoint = {
        "state_dict": model.state_dict(),
        "hyper_parameters": dict(model.hparams),  # Lightning expects 'hyper_parameters'
        "hparams": dict(model.hparams),  # Also include as hparams for compatibility
        "metrics": metrics,
    }
    # Security: Saving trusted model checkpoint - data is generated internally, not user input
    torch.save(  # nosec B614 - PyTorch save operation with internally generated data only
        trainer_checkpoint,
        str(checkpoint_path),
    )

    # Update model registry
    session = get_session()
    storage = ExternalDataStorage(session)
    storage.save_model_checkpoint(
        model_type="tft",
        model_version=model_version,
        checkpoint_path=str(checkpoint_path),
        metrics_json=metrics,
        set_active=True,
    )

    logger.info(
        "Saved TFT checkpoint",
        extra={
            "checkpoint": str(checkpoint_path),
            "version": model_version,
        },
    )

    return str(checkpoint_path)


__all__ = ["save_tft_checkpoint"]
