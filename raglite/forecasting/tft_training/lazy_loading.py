"""Lazy loading utilities for heavy ML libraries.

PyTorch, Lightning, and pytorch_forecasting imports take 5-15 seconds.
These functions defer imports until first use to speed up MCP server startup.
"""

from __future__ import annotations

from typing import Any

# LAZY LOAD: Heavy ML libraries (PyTorch, Lightning, pytorch_forecasting)
# These imports take 5-15 seconds and are only needed for TFT training
_pl_module: Any | None = None
_EarlyStopping: type | None = None
_CSVLogger: type | None = None
_TFT: type | None = None
_TimeSeriesDataSet: type | None = None
_QuantileLoss: type | None = None
_lightning_checked: bool = False


def _get_lightning_module() -> Any:
    """Lazy-load PyTorch Lightning module."""
    global _pl_module, _EarlyStopping, _CSVLogger, _lightning_checked
    if not _lightning_checked:
        _lightning_checked = True
        try:
            import lightning.pytorch as pl
            from lightning.pytorch.callbacks import EarlyStopping
            from lightning.pytorch.loggers import CSVLogger

            _pl_module = pl
            _EarlyStopping = EarlyStopping
            _CSVLogger = CSVLogger
        except ImportError:
            import pytorch_lightning as pl  # type: ignore[no-redef]
            from pytorch_lightning.callbacks import EarlyStopping  # type: ignore[no-redef]
            from pytorch_lightning.loggers import CSVLogger  # type: ignore[no-redef]

            _pl_module = pl
            _EarlyStopping = EarlyStopping
            _CSVLogger = CSVLogger
    return _pl_module


def _get_pytorch_forecasting() -> tuple[type, type, type]:
    """Lazy-load pytorch_forecasting classes."""
    global _TFT, _TimeSeriesDataSet, _QuantileLoss
    if _TFT is None:
        from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet

        try:
            from pytorch_forecasting.metrics import QuantileLoss
        except ImportError:
            from pytorch_forecasting.metrics.quantile import QuantileLoss

        _TFT = TemporalFusionTransformer
        _TimeSeriesDataSet = TimeSeriesDataSet
        _QuantileLoss = QuantileLoss
    return _TFT, _TimeSeriesDataSet, _QuantileLoss  # type: ignore[return-value]


__all__ = ["_get_lightning_module", "_get_pytorch_forecasting", "_EarlyStopping", "_CSVLogger"]
