"""TFT (Temporal Fusion Transformer) training workflow.

Story 6.14: TFT Integration with Training Workflow

This module provides offline training functionality for TFT models,
including dataset preparation, training loop, validation, and checkpoint management.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Use lightning (unified package) instead of pytorch_lightning for compatibility
# Import lightning/pytorch_lightning with fallback
try:
    import lightning.pytorch as pl
    from lightning.pytorch.callbacks import EarlyStopping
    from lightning.pytorch.loggers import CSVLogger
except ImportError:  # pragma: no cover
    import pytorch_lightning as pl
    from pytorch_lightning.callbacks import EarlyStopping
    from pytorch_lightning.loggers import CSVLogger

from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet

# Import QuantileLoss from pytorch_forecasting
try:
    from pytorch_forecasting.metrics import QuantileLoss
except ImportError:
    # Fallback for older versions
    from pytorch_forecasting.metrics.quantile import QuantileLoss

from raglite.external_data.storage import ExternalDataStorage
from raglite.shared.config import settings
from raglite.shared.database import get_session
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def collect_training_data(
    metrics: list[str] | None = None,
    min_data_points: int = 24,
) -> pd.DataFrame | None:
    """Collect training data for TFT from external data sources.

    Story 6.14 AC4: Gather time-series data for TFT training.

    Args:
        metrics: List of metrics to collect (default: EBITDA, revenue, etc.)
        min_data_points: Minimum required data points per metric

    Returns:
        DataFrame with columns: time_idx, metric_name, value, plus regressors
        Returns None if insufficient data
    """
    from raglite.external_data.clients.ecb import ECBClient
    from raglite.external_data.clients.eu_oil_bulletin import EUOilBulletinClient
    from raglite.forecasting.timeseries_extract import extract_timeseries_from_sql

    if metrics is None:
        metrics = ["ebitda", "revenue", "sales_volume"]

    all_data = []

    for metric in metrics:
        try:
            # Extract time-series using SQL extraction (primary method)
            ts_data = await extract_timeseries_from_sql(metric=metric, min_points=6)

            if ts_data and len(ts_data.points) >= min_data_points:
                # Convert to DataFrame rows
                for i, point in enumerate(ts_data.points):
                    all_data.append(
                        {
                            "time_idx": i,
                            "metric_name": metric,
                            "value": point.value,
                            "date": point.date,
                        }
                    )
                logger.info(
                    f"Collected {len(ts_data.points)} points for {metric}",
                    extra={"metric": metric, "points": len(ts_data.points)},
                )
            else:
                logger.warning(
                    f"Insufficient data for {metric}: "
                    f"{len(ts_data.points) if ts_data else 0} points (need {min_data_points})"
                )
        except Exception as e:
            logger.warning(f"Failed to collect data for {metric}: {e}")
            continue

    if not all_data:
        logger.warning("No training data collected - need at least one metric with 24+ points")
        return None

    df = pd.DataFrame(all_data)

    # Add external regressors if available
    try:
        ecb = ECBClient()
        from datetime import date

        euribor_data = await ecb.fetch_euribor(
            start_date=date(2020, 1, 1), end_date=date(2025, 12, 31), tenor="3M"
        )
        if euribor_data:
            euribor_series = pd.Series({d.date: float(d.rate_pct) for d in euribor_data})
            df["euribor_3m"] = df["date"].map(
                lambda x: euribor_series.get(x, euribor_series.iloc[-1])
            )
    except Exception as e:
        logger.warning(f"Failed to add EURIBOR regressor: {e}")
        df["euribor_3m"] = 0.0

    try:
        oil = EUOilBulletinClient()
        diesel_data = await oil.fetch_diesel_prices(
            start_date=date(2020, 1, 1), end_date=date(2025, 12, 31), country="Portugal"
        )
        if diesel_data:
            diesel_series = pd.Series({d.date: float(d.price_eur_litre) for d in diesel_data})
            df["diesel"] = df["date"].map(lambda x: diesel_series.get(x, diesel_series.iloc[-1]))
    except Exception as e:
        logger.warning(f"Failed to add diesel regressor: {e}")
        df["diesel"] = 0.0

    logger.info(
        "Training data collection complete",
        extra={"total_rows": len(df), "metrics": df["metric_name"].nunique()},
    )

    return df


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


def prepare_tft_dataset(
    df: pd.DataFrame,
    target_column: str = "value",
    group_column: str = "metric_name",
    time_column: str = "time_idx",
    static_categoricals: list[str] | None = None,
    time_varying_known_reals: list[str] | None = None,
    time_varying_unknown_reals: list[str] | None = None,
) -> tuple[TimeSeriesDataSet, TimeSeriesDataSet]:
    """Prepare TimeSeriesDataSet for TFT training.

    Story 6.14 AC4: Create training and validation datasets.

    Args:
        df: DataFrame with time series data
        target_column: Target variable column name
        group_column: Group identifier column (e.g., metric_name)
        time_column: Time index column (integer)
        static_categoricals: Fixed categorical features
        time_varying_known_reals: Known future values (date features)
        time_varying_unknown_reals: External regressors (euribor, diesel, etc.)

    Returns:
        Tuple of (training_dataset, validation_dataset)
    """
    if static_categoricals is None:
        static_categoricals = []
    if time_varying_known_reals is None:
        time_varying_known_reals = []
    if time_varying_unknown_reals is None:
        time_varying_unknown_reals = []

    # Story 6.14 AC4: Validation set is last 12 months (holdout)
    max_encoder_length = int(TFT_TRAINING_CONFIG["encoder_length"])
    max_prediction_length = int(TFT_TRAINING_CONFIG["prediction_length"])

    # Determine validation split point (last 12 time steps)
    max_time_idx = df[time_column].max()
    validation_cutoff = max_time_idx - 12

    # Training dataset (all data except last 12 points)
    training = TimeSeriesDataSet(
        df[df[time_column] <= validation_cutoff],
        time_idx=time_column,
        target=target_column,
        group_ids=[group_column],
        min_encoder_length=max_encoder_length // 2,
        max_encoder_length=max_encoder_length,
        min_prediction_length=1,
        max_prediction_length=max_prediction_length,
        static_categoricals=static_categoricals,
        time_varying_known_reals=time_varying_known_reals,
        time_varying_unknown_reals=time_varying_unknown_reals,
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )

    # Validation dataset (last 12 months)
    validation = TimeSeriesDataSet.from_dataset(
        training,
        df,
        predict=True,
        stop_randomization=True,
    )

    logger.info(
        "Prepared TFT datasets",
        extra={
            "training_samples": len(training),
            "validation_samples": len(validation),
            "encoder_length": max_encoder_length,
            "prediction_length": max_prediction_length,
        },
    )

    return training, validation


def train_tft_model(
    training_dataset: TimeSeriesDataSet,
    validation_dataset: TimeSeriesDataSet,
    checkpoint_dir: str | None = None,
) -> tuple[TemporalFusionTransformer, dict[str, float | int | str]]:
    """Train TFT model with PyTorch Lightning.

    Story 6.14 AC4: Training loop with early stopping.

    Args:
        training_dataset: Training TimeSeriesDataSet
        validation_dataset: Validation TimeSeriesDataSet
        checkpoint_dir: Directory to save checkpoints (defaults to settings)

    Returns:
        Tuple of (trained_model, metrics_dict)
    """
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
    early_stop_callback = EarlyStopping(
        monitor="val_loss",
        min_delta=1e-4,
        patience=int(TFT_TRAINING_CONFIG["early_stopping_patience"]),
        verbose=False,
        mode="min",
    )

    # CSV logger for training metrics
    csv_logger = CSVLogger(checkpoint_dir, name="tft_training")

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
    tft = TemporalFusionTransformer.from_dataset(
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
    model: TemporalFusionTransformer,
    validation_dataset: TimeSeriesDataSet,
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


def save_tft_checkpoint(
    model: TemporalFusionTransformer,
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

    # Save checkpoint using torch.save (TFT models don't have a .save() method)
    checkpoint_path = checkpoint_dir / f"tft_{model_version}.ckpt"
    # Security: Saving trusted model checkpoint - data is generated internally, not user input
    torch.save(  # nosec B614 - PyTorch save operation with internally generated data only
        {
            "state_dict": model.state_dict(),
            "hparams": model.hparams,
            "metrics": metrics,
        },
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


async def execute_tft_training(training_data: dict[str, Any]) -> dict[str, Any]:
    """Execute TFT training with provided data.

    This is a simplified version for testing purposes.
    In production, this would use the full TFT training pipeline.

    Args:
        training_data: Dictionary containing training data

    Returns:
        Dict with training results
    """
    import asyncio

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
