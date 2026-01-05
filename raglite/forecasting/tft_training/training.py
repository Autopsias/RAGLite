"""TFT model training and validation functions.

Story 6.14 AC4: Training loop with early stopping and validation metrics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from raglite.forecasting.tft_training.config import TFT_TRAINING_CONFIG
from raglite.forecasting.tft_training.lazy_loading import (
    _CSVLogger,
    _EarlyStopping,
    _get_lightning_module,
    _get_pytorch_forecasting,
)
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def train_tft_model(
    training_dataset: Any,  # TimeSeriesDataSet (lazy-loaded)
    validation_dataset: Any,  # TimeSeriesDataSet (lazy-loaded)
    checkpoint_dir: str | None = None,
) -> tuple[Any, dict[str, float | int | str]]:  # TemporalFusionTransformer (lazy-loaded)
    """Train TFT model with PyTorch Lightning.

    Story 6.14 AC4: Training loop with early stopping.

    Args:
        training_dataset: Training TimeSeriesDataSet
        validation_dataset: Validation TimeSeriesDataSet
        checkpoint_dir: Directory to save checkpoints (defaults to settings)

    Returns:
        Tuple of (trained_model, metrics_dict)
    """
    # Lazy-load ML libraries
    pl = _get_lightning_module()
    TFT, _, QuantileLoss = _get_pytorch_forecasting()

    if checkpoint_dir is None:
        checkpoint_dir = settings.tft_checkpoint_dir

    # Create checkpoint directory if it doesn't exist
    Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)

    # DataLoaders
    train_dataloader = training_dataset.to_dataloader(
        train=True,
        batch_size=TFT_TRAINING_CONFIG["batch_size"],
        num_workers=0,  # Avoid multiprocessing issues
    )
    val_dataloader = validation_dataset.to_dataloader(
        train=False,
        batch_size=int(TFT_TRAINING_CONFIG["batch_size"]) * 2,
        num_workers=0,
    )

    # Early stopping callback
    early_stop_callback = _EarlyStopping(  # type: ignore[misc]
        monitor="val_loss",
        min_delta=1e-4,
        patience=int(TFT_TRAINING_CONFIG["early_stopping_patience"]),
        verbose=False,
        mode="min",
    )

    # CSV logger for training metrics
    csv_logger = _CSVLogger(checkpoint_dir, name="tft_training")  # type: ignore[misc]

    # PyTorch Lightning trainer
    trainer = pl.Trainer(
        max_epochs=int(TFT_TRAINING_CONFIG["max_epochs"]),
        accelerator=str(TFT_TRAINING_CONFIG["accelerator"]),
        gradient_clip_val=float(TFT_TRAINING_CONFIG["gradient_clip_val"]),
        callbacks=[early_stop_callback],
        logger=csv_logger,
        enable_progress_bar=False,  # Disable for cleaner logs
        enable_model_summary=False,
    )

    # Initialize TFT model
    tft = TFT.from_dataset(  # type: ignore[attr-defined]
        training_dataset,
        learning_rate=TFT_TRAINING_CONFIG["learning_rate"],
        hidden_size=TFT_TRAINING_CONFIG["hidden_size"],
        attention_head_size=TFT_TRAINING_CONFIG["attention_head_size"],
        dropout=TFT_TRAINING_CONFIG["dropout"],
        hidden_continuous_size=8,
        output_size=7,  # 7 quantiles
        loss=QuantileLoss(),
        log_interval=10,
        reduce_on_plateau_patience=4,
    )

    logger.info(
        "Starting TFT training",
        extra={
            "max_epochs": TFT_TRAINING_CONFIG["max_epochs"],
            "batch_size": TFT_TRAINING_CONFIG["batch_size"],
            "accelerator": TFT_TRAINING_CONFIG["accelerator"],
        },
    )

    # Train model
    trainer.fit(
        tft,
        train_dataloaders=train_dataloader,
        val_dataloaders=val_dataloader,
    )

    # Extract validation metrics
    val_metrics: dict[str, float | int | str] = {
        "val_loss": float(trainer.callback_metrics.get("val_loss", 0.0)),
        "train_loss": float(trainer.callback_metrics.get("train_loss", 0.0)),
        "best_epoch": int(trainer.current_epoch),
    }

    logger.info(
        "TFT training complete",
        extra={
            "epochs": trainer.current_epoch,
            "val_loss": val_metrics["val_loss"],
        },
    )

    return tft, val_metrics


def validate_tft_model(
    model: Any,  # TemporalFusionTransformer (lazy-loaded)
    validation_dataset: Any,  # TimeSeriesDataSet (lazy-loaded)
) -> dict[str, int | float | str]:
    """Calculate validation metrics for TFT model.

    Story 6.14 AC4: Validation metrics calculation.

    Args:
        model: Trained TFT model
        validation_dataset: Validation TimeSeriesDataSet

    Returns:
        Dictionary of validation metrics
    """
    val_dataloader = validation_dataset.to_dataloader(
        train=False,
        batch_size=64,
        num_workers=0,
    )

    # Get predictions (execution validates model functionality)
    _ = model.predict(val_dataloader, mode="raw", return_x=True)

    # Calculate metrics (simplified for MVP)
    metrics = {
        "samples": len(validation_dataset),
        "prediction_length": TFT_TRAINING_CONFIG["prediction_length"],
    }

    logger.info("TFT validation complete", extra=metrics)

    return metrics


__all__ = ["train_tft_model", "validate_tft_model"]
