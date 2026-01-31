"""TFT dataset preparation functions.

Story 6.14 AC4: Create training and validation datasets.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from raglite.forecasting.tft_training.config import TFT_TRAINING_CONFIG
from raglite.forecasting.tft_training.lazy_loading import _get_pytorch_forecasting
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def prepare_tft_dataset(
    df: pd.DataFrame,
    target_column: str = "value",
    group_column: str = "metric_name",
    time_column: str = "time_idx",
    static_categoricals: list[str] | None = None,
    time_varying_known_reals: list[str] | None = None,
    time_varying_unknown_reals: list[str] | None = None,
) -> tuple[Any, Any]:  # TimeSeriesDataSet (lazy-loaded)
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
    # Lazy-load pytorch_forecasting classes
    _, TimeSeriesDataSet, _ = _get_pytorch_forecasting()

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
        categorical_encoders={},  # Prevent auto-categorical detection of float columns
    )

    # Validation dataset (last 12 months)
    validation = TimeSeriesDataSet.from_dataset(  # type: ignore[attr-defined]
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


__all__ = ["prepare_tft_dataset"]
