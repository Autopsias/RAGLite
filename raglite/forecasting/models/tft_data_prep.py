"""TFT data preparation and inference utilities.

Story 7.5: Extracted from tft_model.py for modularization.
This module handles DataFrame preparation, dataset creation, and inference execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet

logger = get_logger(__name__)


def prepare_tft_dataframe(y: pd.Series) -> pd.DataFrame:
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


def create_tft_dataset(
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


def extract_point_forecast(output: Any) -> list[float] | None:
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


def run_tft_inference(model: TemporalFusionTransformer, dataloader: Any) -> list[float] | None:
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
            point_forecast = extract_point_forecast(output)
            if point_forecast is None:
                logger.warning("TFT prediction returned empty results")
                return None

            break  # Only need first batch

    return point_forecast
