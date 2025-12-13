"""Validation schema dataclasses for forecasting validation.

Story 6.21: Unified Validation Script

Contains MCP-compatible data structures for validation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelPerformanceStats:
    """Performance statistics for a forecasting model."""

    model_name: str
    avg_mape: float
    variables_used: int
    avg_runtime_seconds: float


@dataclass
class QualityGateResult:
    """Quality gate validation result."""

    passed: bool
    minimum_required: int  # Minimum variables that must pass (10 of 12)
    actual_passed: int
    variable_cost_mape: float | None  # None if variable_cost not tested
    variable_cost_target: float  # <8%


@dataclass
class VariableValidationResult:
    """Validation result for a single variable."""

    variable_name: str
    display_name: str
    target_mape: float
    actual_mape: float | None  # None if not tested
    passed: bool

    # MAPE by method
    holdout_mape: float | None = None
    walkforward_mape: float | None = None
    cv_mape: float | None = None

    # Model contributions (for ensemble forecasts)
    ensemble_weights: dict[str, float] = field(default_factory=dict)
    best_model: str = ""
    best_model_mape: float = 0.0


@dataclass
class UnifiedValidationResult:
    """Complete validation result (MCP-compatible schema)."""

    timestamp: str
    runtime_seconds: float
    mape_method: str

    # Summary metrics
    variables_tested: int
    variables_passed: int
    pass_rate: float  # 0.0-1.0
    average_mape: float

    # Per-variable details
    variable_results: list[VariableValidationResult]

    # Model breakdown (for ensemble)
    model_performance: dict[str, ModelPerformanceStats]

    # Quality gate status
    quality_gate: QualityGateResult


@dataclass
class VariableConfig:
    """Configuration for a forecast variable."""

    name: str
    display_name: str
    unit: str
    regressors: list[str]
    target_mape: float
    db_metric_aliases: list[str]
    is_external_only: bool = False
    entity: str | None = (
        None  # Story 6.23: Entity filter for multi-entity metrics (e.g., "portugal")
    )
