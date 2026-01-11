"""Test helpers for TFT training.

Simplified training execution for testing purposes.
"""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


async def execute_tft_training(training_data: dict[str, Any]) -> dict[str, Any]:
    """Execute TFT training with provided data.

    This is a simplified version for testing purposes.
    In production, this would use the full TFT training pipeline.

    Args:
        training_data: Dictionary containing training data

    Returns:
        Dict with training results
    """
    # Simulate training time
    await asyncio.sleep(0.1)  # Short sleep for testing

    # Mock training results
    return {
        "checkpoint_path": str(
            Path(tempfile.gettempdir())
            / f"tft_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ckpt"
        ),
        "model_version": "v1.0",
        "metrics": {
            "train_loss": 0.1,
            "val_loss": 0.12,
            "epochs": 10,
        },
    }
