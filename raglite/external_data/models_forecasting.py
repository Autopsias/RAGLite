"""Forecasting-related models.

Story 6.12: Model Weight for Adaptive Ensemble
Story 6.14: Model Registry & Retrain Result

Models for forecasting infrastructure:
- ModelWeight: Adaptive ensemble weights
- ModelRegistry: Trained model checkpoints
- RetrainResult: Model retraining operation results
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

# =============================================================================
# Story 6.12: Model Weight for Adaptive Ensemble
# =============================================================================


class ModelWeight(BaseModel):
    """Model weight for adaptive ensemble forecasting.

    Story 6.12 AC2: Pydantic model for API interactions with model weights.

    Attributes:
        metric_name: Target metric (e.g., "cement_demand")
        model_name: Model identifier (e.g., "prophet", "xgboost", "catboost")
        weight: Normalized weight (0.0-1.0, sum to 1.0 per metric)
        backtest_rmse: RMSE from rolling backtest validation
        backtest_mape: MAPE from rolling backtest validation
        has_regressors: Whether external regressors were available
        data_points: Number of data points used in backtest
        calculated_at: When weight was last calculated
    """

    metric_name: str = Field(description="Target metric name")
    model_name: str = Field(description="Model identifier")
    weight: float = Field(ge=0.0, le=1.0, description="Normalized weight")
    backtest_rmse: float | None = Field(default=None, description="Backtest RMSE")
    backtest_mape: float | None = Field(default=None, description="Backtest MAPE (%)")
    has_regressors: bool = Field(default=True, description="External regressors available")
    data_points: int | None = Field(default=None, description="Data points in backtest")
    calculated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When weight was calculated",
    )


# =============================================================================
# Story 6.14: Model Registry & Retrain Result
# =============================================================================


class ModelRegistry(BaseModel):
    """Model registry entry for trained model checkpoints.

    Story 6.14 AC2: Pydantic model for model registry API interactions.

    Attributes:
        id: Registry entry ID
        model_type: Model type (e.g., "tft", "lstm")
        model_version: Version string (e.g., "v1.0", "2024-12-10")
        checkpoint_path: Path to saved checkpoint file
        metrics_json: Training/validation metrics
        trained_at: When model was trained
        is_active: Whether this is the active checkpoint for this model type
    """

    id: int | None = Field(default=None, description="Registry entry ID")
    model_type: str = Field(description="Model type identifier")
    model_version: str = Field(description="Model version string")
    checkpoint_path: str = Field(description="Path to checkpoint file")
    metrics_json: dict[str, float | str | int] | None = Field(
        default=None, description="Training metrics"
    )
    trained_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When model was trained",
    )
    is_active: bool = Field(default=False, description="Active checkpoint flag")


class RetrainResult(BaseModel):
    """Result of model retraining operation.

    Story 6.14 AC6: MCP tool return type for retrain_forecasting_models.

    Attributes:
        status: Training status ("success", "partial", "failed")
        models_trained: List of model types that were trained
        checkpoint_path: Path to saved checkpoint (if single model)
        metrics: Training/validation metrics summary
        duration_seconds: Training duration
        errors: List of errors encountered (if any)
    """

    status: str = Field(description="Training status")
    models_trained: list[str] = Field(default_factory=list, description="Models trained")
    checkpoint_path: str | None = Field(default=None, description="Checkpoint path")
    metrics: dict[str, float | str] | None = Field(default=None, description="Training metrics")
    duration_seconds: float = Field(description="Training duration")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
