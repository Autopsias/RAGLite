"""Failure diagnosis and actionable guidance for validation reports.

Story 6.27: Failure Diagnosis and Actionable Guidance
Categorizes failures and provides specific fix recommendations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raglite.forecasting.validation_schema import (
        FailureDiagnosis,
        UnifiedValidationResult,
        VariableValidationResult,
    )


def diagnose_failure(var: VariableValidationResult) -> FailureDiagnosis:
    """Diagnose why a variable failed and recommend action.

    Story 6.27: Provides actionable guidance based on failure patterns.

    Args:
        var: The variable validation result to diagnose

    Returns:
        FailureDiagnosis with issue analysis and recommendations
    """
    # Import at runtime to avoid circular imports
    from raglite.forecasting.validation_schema import FailureDiagnosis

    mape = var.actual_mape or 0
    mase = var.metrics.mase if var.metrics else float("inf")

    # Pattern 1: High MAPE but excellent MASE
    # The model follows trends well but has scale/offset issues
    if mape > var.target_mape and mase is not None and mase < 1.0:
        return FailureDiagnosis(
            issue=f"MAPE {mape:.1f}% exceeds threshold but MASE {mase:.2f} is excellent",
            root_cause="Model beats naive baseline but has scale/offset issues",
            requires_data_fix=False,
            fix_action="N/A",
            expected_improvement="N/A",
            analysis="Forecasts follow correct trend but may have systematic bias",
            recommendation="Consider enabling MASE-only pass for this variable",
        )

    # Pattern 2: Both MAPE and MASE poor - likely data quality issue
    if mape > 50 and mase is not None and mase > 2.0:
        return FailureDiagnosis(
            issue=f"MAPE {mape:.1f}% and MASE {mase:.2f} both poor",
            root_cause="Likely data quality issue (entity mixing, wrong aliases, scale mismatch)",
            requires_data_fix=True,
            fix_action=(
                "1) Check db_metric_aliases for incorrect mappings\n"
                "2) Verify entity filter (GROUP vs individual entities)\n"
                "3) Check for scale mismatches (thousands vs units)"
            ),
            expected_improvement="50-90% reduction in MAPE after data fix",
        )

    # Pattern 3: High MAPE, moderate MASE - may be inherent volatility
    if mape > var.target_mape and mase is not None and 1.0 <= mase <= 1.5:
        suggested_threshold = int(mape * 1.1)
        return FailureDiagnosis(
            issue=f"MAPE {mape:.1f}% exceeds threshold, MASE {mase:.2f} is borderline",
            root_cause="May be inherent series volatility or missing regressors",
            requires_data_fix=False,
            fix_action="N/A",
            expected_improvement="N/A",
            analysis="Model performs close to naive baseline",
            recommendation=(
                f"Consider: 1) Adding predictive regressors, "
                f"2) Adjusting threshold to {suggested_threshold}%"
            ),
        )

    # Pattern 4: SMAPE-primary variable failing on MAPE
    if (
        hasattr(var, "primary_metric_used")
        and var.primary_metric_used == "smape"
        and var.metrics
        and var.metrics.smape is not None
        and var.metrics.smape <= var.target_mape
    ):
        return FailureDiagnosis(
            issue=(
                f"MAPE unreliable due to negative/zero values, "
                f"SMAPE {var.metrics.smape:.1f}% is acceptable"
            ),
            root_cause="Metric stored with negative sign or zero crossings",
            requires_data_fix=False,
            fix_action="N/A",
            expected_improvement="N/A",
            analysis="SMAPE handles negative values correctly",
            recommendation="Use SMAPE as primary metric for this variable",
        )

    # Default: Unknown pattern
    return FailureDiagnosis(
        issue=f"MAPE {mape:.1f}% exceeds threshold {var.target_mape}%",
        root_cause="Unknown - requires manual investigation",
        requires_data_fix=False,
        fix_action="N/A",
        expected_improvement="N/A",
        analysis="Review data quality, regressors, and model configuration",
        recommendation="Run targeted diagnosis on this variable",
    )


def generate_actionable_guidance(result: UnifiedValidationResult) -> str:
    """Generate actionable guidance for each failing variable.

    Story 6.27: Categorizes failures and provides specific fix recommendations.

    Args:
        result: Complete validation result

    Returns:
        Markdown string with actionable guidance sections
    """
    lines = ["\n## Actionable Guidance\n"]

    # Categorize issues
    needs_data_fix: list[tuple[VariableValidationResult, FailureDiagnosis]] = []
    needs_threshold_review: list[tuple[VariableValidationResult, FailureDiagnosis]] = []
    acceptable_as_is: list[VariableValidationResult] = []

    for var in result.variable_results:
        if var.passed:
            acceptable_as_is.append(var)
            continue

        diagnosis = diagnose_failure(var)
        if diagnosis.requires_data_fix:
            needs_data_fix.append((var, diagnosis))
        else:
            needs_threshold_review.append((var, diagnosis))

    # Section 1: Acceptable (Passing)
    if acceptable_as_is:
        lines.append("### ✅ Acceptable (No Action Required)\n")
        lines.append("| Variable | MAPE | MASE | Status |")
        lines.append("|----------|------|------|--------|")
        for var in acceptable_as_is:
            mape_str = f"{var.actual_mape:.1f}%" if var.actual_mape else "N/A"
            mase_str = f"{var.metrics.mase:.2f}" if var.metrics and var.metrics.mase else "N/A"
            # Check for mase_only_pass attribute (Story 6.27)
            status = "MASE-only" if getattr(var, "mase_only_pass", False) else "Primary"
            lines.append(f"| {var.display_name} | {mape_str} | {mase_str} | {status} |")
        lines.append("")

    # Section 2: Needs Data Fix (Requires Reingestion)
    if needs_data_fix:
        lines.append("\n### 🔧 Needs Data Fix (Requires Reingestion)\n")
        for var, diagnosis in needs_data_fix:
            lines.append(f"**{var.display_name}** - {diagnosis.issue}")
            lines.append(f"- **Root Cause:** {diagnosis.root_cause}")
            lines.append(f"- **Fix:** {diagnosis.fix_action}")
            lines.append(f"- **Expected Improvement:** {diagnosis.expected_improvement}")
            lines.append("")

    # Section 3: Threshold Review (No Reingestion)
    if needs_threshold_review:
        lines.append("\n### ⚙️ Consider Threshold Adjustment (No Reingestion)\n")
        for var, diagnosis in needs_threshold_review:
            lines.append(f"**{var.display_name}** - {diagnosis.issue}")
            lines.append(f"- **Analysis:** {diagnosis.analysis}")
            lines.append(f"- **Recommendation:** {diagnosis.recommendation}")
            lines.append("")

    # Section 4: Bias Alerts (Informational)
    vars_with_bias = [v for v in result.variable_results if getattr(v, "bias_alert", False)]
    if vars_with_bias:
        lines.append("\n### ⚠️ Bias Alerts\n")
        lines.append("| Variable | Bias | Alert |")
        lines.append("|----------|------|-------|")
        for var in vars_with_bias:
            bias_val = var.metrics.bias if var.metrics else 0
            bias_msg = getattr(var, "bias_alert_message", "Bias detected")
            lines.append(f"| {var.display_name} | {bias_val:.2f} | {bias_msg} |")
        lines.append("")

    return "\n".join(lines)
