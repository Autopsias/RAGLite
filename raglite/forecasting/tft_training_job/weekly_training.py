"""Weekly TFT training workflow.

Story 6.14 AC3: Weekly TFT training job (Sunday 2am UTC, before backtest at 3am).
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from raglite.external_data.storage import ExternalDataStorage
from raglite.forecasting.tft_training import (
    prepare_tft_dataset,
    save_tft_checkpoint,
    train_tft_model,
)
from raglite.shared.config import settings
from raglite.shared.database import get_session
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Minimum data points required for TFT training
MIN_DATA_POINTS = 24  # 2 years of monthly data minimum


async def run_weekly_tft_training() -> None:
    """Weekly TFT training job (Sunday 2am UTC).

    Story 6.14 AC3: Trigger 1 - Weekly scheduled training.
    Runs BEFORE backtest job (2am vs 3am) to ensure fresh models.

    Workflow:
    1. Fetch all metrics with sufficient historical data (>=24 months)
    2. Prepare TimeSeriesDataSet combining all metrics
    3. Train TFT model
    4. Save checkpoint to model_registry
    5. Log training metrics
    """
    logger.info("TFT training job triggered (weekly schedule)")

    try:
        session = get_session()
        storage = ExternalDataStorage(session)

        # Get all available sources
        from raglite.external_data.orm_models import ExternalDataSourceORM

        sources = (
            session.query(ExternalDataSourceORM)
            .filter(ExternalDataSourceORM.deleted_at.is_(None))
            .all()
        )

        if not sources:
            logger.warning("No external data sources found - skipping TFT training")
            return

        # Collect all time series data with sufficient history
        all_data = []
        end_date = date.today()
        buffer_days = settings.regressor_buffer_years * 365
        start_date = end_date - timedelta(days=buffer_days)

        for source in sources:
            try:
                source_metrics = storage.get_metrics_for_source(source.source_name)
                for metric in source_metrics:
                    data_points = storage.query_data_range(
                        source_name=source.source_name,
                        start_date=start_date,
                        end_date=end_date,
                        metric_name=metric,
                    )

                    if len(data_points) >= MIN_DATA_POINTS:
                        # Convert to DataFrame format
                        # CRITICAL: Convert Decimal to float for TFT compatibility
                        for idx, point in enumerate(data_points):
                            all_data.append(
                                {
                                    "metric_name": f"{source.source_name}_{metric}",
                                    "date": point.date,
                                    "value": float(point.value),  # Convert Decimal to float
                                    "time_idx": idx,
                                }
                            )
                        logger.info(
                            f"Included metric for training: {source.source_name}_{metric} ({len(data_points)} points)"
                        )
                    else:
                        logger.debug(
                            f"Skipped metric (insufficient data): {source.source_name}_{metric} ({len(data_points)} < {MIN_DATA_POINTS})"
                        )

            except Exception as e:
                logger.warning(f"Failed to fetch data for source {source.source_name}: {e}")
                continue

        if not all_data:
            logger.warning("No metrics with sufficient historical data - skipping TFT training")
            return

        # Convert to DataFrame
        df = pd.DataFrame(all_data)

        # Prepare datasets
        logger.info(f"Preparing TFT datasets with {len(df)} total data points")
        training_dataset, validation_dataset = prepare_tft_dataset(
            df=df,
            target_column="value",
            group_column="metric_name",
            time_column="time_idx",
        )

        # Train model
        logger.info("Starting TFT model training")
        tft_model, metrics = train_tft_model(
            training_dataset=training_dataset,
            validation_dataset=validation_dataset,
        )

        # Save checkpoint
        checkpoint_path = save_tft_checkpoint(
            model=tft_model,
            metrics=metrics,
        )

        logger.info(
            "TFT training completed successfully",
            extra={
                "checkpoint_path": checkpoint_path,
                "metrics": metrics,
                "training_samples": len(training_dataset),
                "validation_samples": len(validation_dataset),
            },
        )

    except Exception as e:
        logger.error(
            f"TFT training job failed: {e}",
            exc_info=True,
        )
