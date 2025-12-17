"""Validation schema dataclasses for forecasting validation.

Story 6.21: Unified Validation Script
Story 6.26: Multi-Metric Validation Enhancement

Contains MCP-compatible data structures for validation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class MultiMetricValues:
    """All validation metrics for a single variable.

    These metrics provide different perspectives on forecast accuracy:
    - MAPE: Percentage error (stakeholder-friendly)
    - MASE: Scale-free comparison vs naïve baseline
    - SMAPE: Symmetric MAPE, handles zeros better
    - RMSE: Penalizes large errors (risk-sensitive)
    - MAE: Simple absolute error
    - Bias: Systematic over/under-prediction
    """

    mape: float | None = None
    mase: float | None = None
    smape: float | None = None
    rmse: float | None = None
    mae: float | None = None
    bias: float | None = None


@dataclass
class ModelPerformanceStats:
    """Performance statistics for a forecasting model."""

    model_name: str
    avg_mape: float
    variables_used: int
    avg_runtime_seconds: float


@dataclass
class QualityGateResult:
    """Quality gate validation result.

    Story 6.26: Extended with MASE criterion.

    A validation run PASSES when ALL criteria are met:
    1. actual_passed >= minimum_required (existing MAPE criterion)
    2. variable_cost_mape < variable_cost_target (existing cost criterion)
    3. average_mase < 1.0 (NEW: forecasts beat naïve baseline)
    """

    passed: bool
    minimum_required: int  # Minimum variables that must pass (10 of 20)
    actual_passed: int
    variable_cost_mape: float | None  # None if variable_cost not tested
    variable_cost_target: float  # <8%

    # Story 6.26: Multi-metric extension
    average_mase: float | None = None  # Target: < 1.0 (better than naïve)
    mase_passed: bool = True  # True if average_mase < 1.0 or None
    mase_target: float = 1.0  # Default target: beat naïve baseline

    # Story 6.29 P2: Data quality exemption - track controllable MASE separately
    controllable_mase: float | None = None  # MASE excluding exempt variables
    exempt_variables: list[str] = field(default_factory=list)  # Variables excluded
    controllable_mase_passed: bool = True  # True if controllable_mase < 1.0


@dataclass
class VariableValidationResult:
    """Validation result for a single variable.

    Story 6.26: Extended with multi-metric values and assessment.
    Story 6.27: Extended with multi-metric pass/fail fields.
    """

    variable_name: str
    display_name: str
    target_mape: float
    actual_mape: float | None  # None if not tested
    passed: bool

    # MAPE by method
    holdout_mape: float | None = None
    walkforward_mape: float | None = None
    cv_mape: float | None = None

    # Story 6.26: Multi-metric values
    metrics: MultiMetricValues = field(default_factory=MultiMetricValues)

    # Story 6.26: Assessment and recommendations
    assessment_status: str = "unknown"  # "excellent", "good", "moderate", "poor", "critical"
    assessment_text: str = ""
    recommendations: list[str] = field(default_factory=list)

    # Model contributions (for ensemble forecasts)
    ensemble_weights: dict[str, float] = field(default_factory=dict)
    best_model: str = ""
    best_model_mape: float = 0.0

    # Story 6.27: Multi-metric pass/fail fields
    primary_metric_used: str = "mape"  # Which metric determined pass/fail
    mase_only_pass: bool = False  # Did MASE-only pass apply?
    bias_alert: bool = False  # True if |bias| > 20% of mean
    bias_alert_message: str = ""  # Description of bias alert


@dataclass
class UnifiedValidationResult:
    """Complete validation result (MCP-compatible schema).

    Story 6.26: Extended with multi-metric summary.
    """

    timestamp: str
    runtime_seconds: float
    mape_method: str

    # Summary metrics
    variables_tested: int
    variables_passed: int
    pass_rate: float  # 0.0-1.0
    average_mape: float

    # Story 6.26: Multi-metric summary
    average_mase: float | None = None  # Average MASE across all variables
    average_smape: float | None = None  # Average SMAPE
    average_rmse: float | None = None  # Average RMSE
    average_mae: float | None = None  # Average MAE
    average_bias: float | None = None  # Average bias

    # Per-variable details
    variable_results: list[VariableValidationResult] = field(default_factory=list)

    # Model breakdown (for ensemble)
    model_performance: dict[str, ModelPerformanceStats] = field(default_factory=dict)

    # Quality gate status
    quality_gate: QualityGateResult | None = None


@dataclass
class FailureDiagnosis:
    """Diagnosis for a failing variable with actionable guidance.

    Story 6.27: Used to generate actionable reports for failed variables.
    """

    issue: str  # Brief description of the failure
    root_cause: str  # Identified or suspected root cause
    requires_data_fix: bool  # True if reingestion/data change needed
    fix_action: str  # Specific action to take (or "N/A")
    expected_improvement: str  # Expected outcome after fix (or "N/A")
    analysis: str = ""  # Detailed analysis (for threshold review cases)
    recommendation: str = ""  # Specific recommendation


@dataclass
class VariableConfig:
    """Configuration for a forecast variable.

    Story 6.27: Extended with multi-metric pass/fail configuration.
    """

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

    # Story 6.27: Multi-metric pass/fail configuration
    primary_metric: str = "mape"  # "mape", "smape", or "mase"
    allow_mase_only_pass: bool = False  # MASE < target_mase passes even if MAPE high
    target_smape: float | None = None  # When primary_metric="smape"
    target_mase: float = 1.0  # Default: beat naive baseline

    # Story 6.29 P2: Data quality exemption - exclude from aggregate MASE calculation
    # Use for metrics with known structural data issues (gaps, regime changes)
    data_quality_exempt: bool = False
    data_quality_reason: str | None = None  # Document why exempt
