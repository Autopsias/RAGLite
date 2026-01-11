"""TFT forecasting model - facade for backward compatibility."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytorch_forecasting import TemporalFusionTransformer

from raglite.forecasting.models.tft._legacy import (
    _get_tft_model,
    _tft_checkpoint_path,
    _tft_model,
    fit_and_forecast_tft,
)

__all__ = [
    "_get_tft_model",
    "_tft_checkpoint_path",
    "_tft_model",
    "fit_and_forecast_tft",
]
