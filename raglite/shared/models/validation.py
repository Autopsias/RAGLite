"""Validation models.

Defines models for forecasting validation.
"""

from pydantic import BaseModel, Field


# Story 6.22: MCP Validation Tool Integration models
class VariableValidationDetail(BaseModel):
    """Per-variable validation detail for MCP responses.

    Story 6.22 AC1: MCP-compatible validation detail for individual variables.

    Attributes:
        variable_name: Technical variable name (e.g., 'variable_cost')
        display_name: Human-readable name (e.g., 'Variable Cost')
        target_mape: Target MAPE threshold for this variable
        actual_mape: Actual MAPE achieved (None if not tested)
        passed: Whether the variable passes its MAPE target
        ensemble_weights: Model weights in ensemble (e.g., {'prophet': 0.4, 'linear': 0.3})
        best_model: Best performing model for this variable
    """

    variable_name: str = Field(..., description="Technical variable name")
    display_name: str = Field(..., description="Human-readable name")
    target_mape: float = Field(..., description="Target MAPE threshold")
    actual_mape: float | None = Field(None, description="Actual MAPE achieved")
    passed: bool = Field(..., description="Whether variable passes target")
    ensemble_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Model weights in ensemble",
    )
    best_model: str = Field(default="", description="Best performing model")

    # Multi-metric fields (Forecasting Quality Enhancement)
    actual_mase: float | None = Field(None, description="MASE value (<1.0 = better than naïve)")
    actual_smape: float | None = Field(None, description="Symmetric MAPE (0-200%)")
    actual_bias: float | None = Field(
        None, description="Bias (+ = over-predict, - = under-predict)"
    )
    fqs: float | None = Field(None, description="Forecast Quality Score (0-100)")
    primary_metric_used: str = Field(default="mape", description="Primary metric for pass/fail")
    mase_only_pass: bool = Field(default=False, description="True if MASE-only pass applied")


class ModelPerformanceDetail(BaseModel):
    """Per-model performance detail for MCP responses.

    Story 6.22 AC1: MCP-compatible model performance breakdown.

    Attributes:
        model_name: Model name (e.g., 'prophet', 'linear', 'xgboost')
        avg_mape: Average MAPE across all variables using this model
        variables_used: Number of variables using this model
    """

    model_name: str = Field(..., description="Model name")
    avg_mape: float = Field(..., description="Average MAPE across variables")
    variables_used: int = Field(..., description="Variables using this model")


class ValidationResponse(BaseModel):
    """Response model for forecasting validation via MCP.

    Story 6.22 AC1: Complete validation result for MCP tool.

    Attributes:
        timestamp: Validation timestamp (ISO format)
        runtime_seconds: Validation runtime in seconds
        mape_method: MAPE calculation method used ('holdout', 'walkforward', or 'cv')
        variables_tested: Number of variables validated
        variables_passed: Number of variables passing MAPE target
        pass_rate: Pass rate (0.0-1.0)
        average_mape: Average MAPE across all variables
        quality_gate_passed: Whether Epic 6 quality gate passed (10/12 variables + Variable Cost <8%)
        variable_cost_mape: Variable Cost MAPE if tested
        variable_results: Per-variable validation results
        model_performance: Per-model breakdown if requested
    """

    timestamp: str = Field(..., description="Validation timestamp (ISO format)")
    runtime_seconds: float = Field(..., description="Validation runtime in seconds")
    mape_method: str = Field(..., description="MAPE calculation method used")

    # Summary
    variables_tested: int = Field(..., description="Number of variables validated")
    variables_passed: int = Field(..., description="Number of variables passing MAPE target")
    pass_rate: float = Field(..., description="Pass rate (0.0-1.0)")
    average_mape: float = Field(..., description="Average MAPE across all variables")

    # Quality gate
    quality_gate_passed: bool = Field(..., description="Whether Epic 6 quality gate passed")
    variable_cost_mape: float | None = Field(None, description="Variable Cost MAPE if tested")

    # Multi-metric summary (Forecasting Quality Enhancement)
    average_mase: float | None = Field(None, description="Average MASE (<1.0 = better than naïve)")
    average_fqs: float | None = Field(None, description="Average Forecast Quality Score (0-100)")
    controllable_mase: float | None = Field(None, description="MASE excluding exempt variables")
    controllable_fqs: float | None = Field(None, description="FQS excluding exempt variables")

    # Details
    variable_results: list[VariableValidationDetail] = Field(
        ..., description="Per-variable validation results"
    )
    model_performance: dict[str, ModelPerformanceDetail] | None = Field(
        None, description="Per-model breakdown if requested"
    )
