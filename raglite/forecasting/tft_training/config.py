"""TFT training configuration constants.

Story 6.14 AC4: TFT training configuration constants.
"""

from raglite.shared.config import settings

# Story 6.14 AC4: TFT training configuration constants
TFT_TRAINING_CONFIG: dict[str, int | float | str] = {
    "encoder_length": settings.tft_encoder_length,  # 12 periods lookback
    "prediction_length": settings.tft_prediction_length,  # 3 periods forecast
    "max_epochs": settings.tft_max_epochs,  # 50
    "early_stopping_patience": settings.tft_early_stopping_patience,  # 5
    "gradient_clip_val": 0.1,
    "accelerator": "cpu",  # Force CPU to avoid MPS issues with small batches
    "batch_size": 32,  # Reduced batch size for small datasets
    "learning_rate": 0.03,
    "hidden_size": 16,  # Reduced for faster training on small datasets
    "attention_head_size": 4,
    "dropout": 0.1,
}

__all__ = ["TFT_TRAINING_CONFIG"]
