"""TFT forecasting utilities.

Story 6.14: Forecast generation from pre-trained TFT model.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _prepare_tft_dataset(y: pd.Series, periods_ahead: int) -> Any | None:
    """Prepare TimeSeriesDataSet for TFT inference.

    Args:
        y: Target time-series values
        periods_ahead: Number of periods to forecast

    Returns:
        TimeSeriesDataSet instance or None if insufficient data
    """
    from pytorch_forecasting import TimeSeriesDataSet

    # Create DataFrame in TFT format
    df = pd.DataFrame(
        {
            "time_idx": range(len(y)),
            "metric_name": "target_metric",  # Single group for now
            "value": y.values,
        }
    )

    # Create minimal TimeSeriesDataSet for prediction
    # Use same parameters as training (from TFT_TRAINING_CONFIG)
    max_encoder_length = 12  # From settings.tft_encoder_length
    max_prediction_length = periods_ahead

    # Need sufficient history for encoder + prediction
    # TimeSeriesDataSet requires encoder_length + prediction_length + 1 points minimum
    min_required = max_encoder_length + max_prediction_length + 1
    if len(y) < min_required:
        logger.warning(f"Insufficient data for TFT (need {min_required}, have {len(y)})")
        return None

    # Create dataset for inference
    # Use last max_encoder_length points as context
    return TimeSeriesDataSet(
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


def _generate_tft_predictions(model: Any, dataset: Any) -> list[float] | None:
    """Generate predictions from TFT model.

    Args:
        model: Loaded TFT model
        dataset: TimeSeriesDataSet for inference

    Returns:
        Point forecast values or None if prediction fails
    """
    import torch

    # Generate predictions
    dataloader = dataset.to_dataloader(train=False, batch_size=1, num_workers=0)

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

            # Extract point forecast (median quantile, index 3 out of 7 quantiles)
            # TFT outputs quantiles: [0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98]
            if hasattr(output, "prediction"):
                pred = output.prediction
            elif isinstance(output, dict) and "prediction" in output:
                pred = output["prediction"]
            else:
                pred = output

            # Extract median (index 3) from quantiles
            point_forecast = pred[0, :, 3].cpu().numpy().tolist()
            break  # Only need first batch

    if point_forecast is None:
        logger.warning("TFT prediction returned empty results")
        return None

    # Ensure we return list[float], not Any
    assert isinstance(point_forecast, list), f"Expected list, got {type(point_forecast)}"
    assert all(isinstance(x, (int, float)) for x in point_forecast), "Expected numeric values"
    return point_forecast
