"""TFT (Temporal Fusion Transformer) training workflow.

This module provides offline training functionality for TFT models,
including dataset preparation, training loop, validation, and checkpoint management.

LAZY LOADING: All heavy ML imports (PyTorch, Lightning, pytorch_forecasting) are
deferred until first use to speed up MCP server startup (~5-15s saved).

Story 6.14: TFT Integration with Training Workflow
"""

# Facade: Re-export all public APIs from new modular structure
from raglite.forecasting.tft_training.checkpoint import save_tft_checkpoint
from raglite.forecasting.tft_training.config import TFT_TRAINING_CONFIG
from raglite.forecasting.tft_training.data_collection import collect_training_data
from raglite.forecasting.tft_training.dataset import prepare_tft_dataset
from raglite.forecasting.tft_training.execution import execute_tft_training
from raglite.forecasting.tft_training.training import train_tft_model, validate_tft_model

__all__ = [
    "TFT_TRAINING_CONFIG",
    "prepare_tft_dataset",
    "train_tft_model",
    "validate_tft_model",
    "save_tft_checkpoint",
    "collect_training_data",
    "execute_tft_training",
]
