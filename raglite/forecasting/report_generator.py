"""Validation report generator for forecasting validation.

Story 6.26: Multi-Metric Validation Enhancement

Generates comprehensive, actionable validation reports that:
1. Explain what each validation metric means
2. Provide per-variable assessment with clear pass/fail/warning status
3. Identify specific areas needing improvement
4. Confirm what's working well

Output formats:
- Markdown: Full narrative report for human reading
- JSON: MCP-compatible structured data
- Console: Abbreviated summary for CLI
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raglite.forecasting.validation_schema import (
        FailureDiagnosis,
        UnifiedValidationResult,
        VariableValidationResult,
    )

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Assessment Thresholds
# =============================================================================

# MAPE thresholds for assessment status
MAPE_THRESHOLDS = {
    "excellent": 5.0,  # <5%: Excellent - suitable for financial reporting
    "good": 10.0,  # 5-10%: Good - acceptable for planning
    "moderate": 20.0,  # 10-20%: Moderate - use with caution
    "poor": 30.0,  # 20-30%: Poor - investigate root cause
    # >30%: Critical
}

# MASE thresholds for assessment status
MASE_THRESHOLDS = {
    "excellent": 0.5,  # <0.5: Excellent - model provides significant value
    "good": 0.8,  # 0.5-0.8: Good - model outperforms naïve substantially
    "marginal": 1.0,  # 0.8-1.0: Marginal - model barely beats naïve
    # >1.0: Poor - naïve forecast would be better
}


def get_mape_assessment(mape: float | None) -> str:
    """Get assessment status based on MAPE value."""
    if mape is None:
        return "unknown"
    if mape < MAPE_THRESHOLDS["excellent"]:
        return "excellent"
    if mape < MAPE_THRESHOLDS["good"]:
        return "good"
    if mape < MAPE_THRESHOLDS["moderate"]:
        return "moderate"
    if mape < MAPE_THRESHOLDS["poor"]:
        return "poor"
    return "critical"


def get_mase_assessment(mase: float | None) -> str:
    """Get assessment status based on MASE value."""
    if mase is None:
        return "unknown"
    if mase < MASE_THRESHOLDS["excellent"]:
        return "excellent"
    if mase < MASE_THRESHOLDS["good"]:
        return "good"
    if mase < MASE_THRESHOLDS["marginal"]:
        return "marginal"
    return "poor"


def get_status_emoji(passed: bool, mape: float | None = None) -> str:
    """Get status emoji based on pass/fail and MAPE value."""
    if not passed:
        return "❌"
    if mape is not None and mape < 5.0:
        return "✅"
    return "✅" if passed else "⚠️"


# =============================================================================
# Metric Explanation Content
# =============================================================================

METRIC_EXPLANATIONS = """## Understanding the Metrics

### MAPE (Mean Absolute Percentage Error)
**What it measures:** Average percentage deviation from actual values
**Target:** Variable-specific (see table below)
**Interpretation:**
- <5%: Excellent - suitable for financial reporting
- 5-10%: Good - acceptable for planning
- 10-20%: Moderate - use with caution
- >20%: Poor - investigate root cause

### MASE (Mean Absolute Scaled Error)
**What it measures:** Forecast accuracy relative to a naïve baseline (previous period's value)
**Target:** <1.0 (beating the naïve forecast)
**Interpretation:**
- <0.5: Excellent - model provides significant value over naïve baseline
- 0.5-0.8: Good - model outperforms naïve substantially
- 0.8-1.0: Marginal - model barely beats naïve
- >1.0: Poor - naïve forecast would be better

### SMAPE (Symmetric MAPE)
**What it measures:** Percentage error bounded 0-200%, treats over/under equally
**When to use:** Volatile metrics where MAPE skews results
**Interpretation:** Similar to MAPE but more stable for commodities

### RMSE (Root Mean Square Error)
**What it measures:** Average error in original units, penalizes large errors
**When to use:** When large errors are especially costly (risk management)
**Interpretation:** Lower is better; compare only within same variable

### MAE (Mean Absolute Error)
**What it measures:** Simple average of absolute errors in original units
**When to use:** When you want interpretable error in data units
**Interpretation:** Lower is better; more robust to outliers than RMSE

### Bias (Mean Error)
**What it measures:** Systematic over-prediction (positive) or under-prediction (negative)
**Target:** Close to 0
**Interpretation:**
- Positive: Model tends to over-predict (conservative)
- Negative: Model tends to under-predict (optimistic)
- Near 0: Model is well-calibrated

### FQS (Forecast Quality Score)
**What it measures:** Composite quality metric combining MAPE and MASE (0-100 scale)
**Target:** ≥65 (Good), ≥80 (Excellent)
**Formula:** FQS = 100 × [0.35 × A_MAPE + 0.65 × A_MASE]
**Interpretation:**
- ≥80: Excellent - high confidence in forecast quality
- 65-79: Good - acceptable for planning decisions
- 50-64: Moderate - use with caution
- <50: Poor - forecast needs investigation
**Note:** MASE-weighted (65%) per Hyndman (2006) recommendation for cross-series comparability
"""


# =============================================================================
# Report Generation Functions
# =============================================================================


def generate_executive_summary(result: UnifiedValidationResult) -> str:
    """Generate executive summary section."""
    # Determine overall status
    if result.quality_gate and result.quality_gate.passed:
        overall_status = "✅ PASS"
    elif result.pass_rate >= 0.8:
        overall_status = "⚠️ WARNING"
    else:
        overall_status = "❌ FAIL"

    # Count variables by MAPE category
    excellent_count = sum(
        1 for v in result.variable_results if v.actual_mape is not None and v.actual_mape < 5
    )
    good_count = sum(
        1 for v in result.variable_results if v.actual_mape is not None and 5 <= v.actual_mape < 15
    )
    needs_improvement_count = sum(
        1 for v in result.variable_results if v.actual_mape is not None and 15 <= v.actual_mape < 30
    )
    critical_count = sum(
        1 for v in result.variable_results if v.actual_mape is not None and v.actual_mape >= 30
    )

    # Build summary
    lines = [
        "# RAGLite Forecasting Validation Report",
        f"Generated: {result.timestamp}",
        f"Runtime: {result.runtime_seconds:.1f} seconds",
        "",
        f"## Overall Assessment: {overall_status}",
        "",
        "### Quality Gate Results",
        "| Criterion | Target | Actual | Status |",
        "|-----------|--------|--------|--------|",
    ]

    # Quality gate details
    if result.quality_gate:
        qg = result.quality_gate
        mape_status = "✅ PASS" if qg.actual_passed >= qg.minimum_required else "❌ FAIL"
        lines.append(
            f"| Variables Passing MAPE | ≥{qg.minimum_required}/{result.variables_tested} | "
            f"{qg.actual_passed}/{result.variables_tested} | {mape_status} |"
        )

        if qg.variable_cost_mape is not None:
            vc_status = "✅ PASS" if qg.variable_cost_mape < qg.variable_cost_target else "❌ FAIL"
            lines.append(
                f"| Variable Cost MAPE | <{qg.variable_cost_target}% | "
                f"{qg.variable_cost_mape:.2f}% | {vc_status} |"
            )

        if qg.average_mase is not None:
            mase_status = "✅ PASS" if qg.mase_passed else "❌ FAIL"
            lines.append(
                f"| Average MASE | <{qg.mase_target} | {qg.average_mase:.2f} | {mase_status} |"
            )

    lines.extend(
        [
            "",
            "### Quick Summary",
            f"- **Excellent (MAPE <5%):** {excellent_count} variables",
            f"- **Good (MAPE 5-15%):** {good_count} variables",
            f"- **Needs Improvement (MAPE 15-30%):** {needs_improvement_count} variables",
            f"- **Critical (MAPE >30%):** {critical_count} variables",
            "",
            f"**Average MAPE:** {result.average_mape:.2f}%",
        ]
    )

    if result.average_mase is not None:
        mase_interpretation = (
            "better than naïve" if result.average_mase < 1.0 else "worse than naïve"
        )
        lines.append(f"**Average MASE:** {result.average_mase:.2f} ({mase_interpretation})")

    if result.average_fqs is not None:
        fqs_rating = (
            "Excellent"
            if result.average_fqs >= 80
            else "Good"
            if result.average_fqs >= 65
            else "Moderate"
            if result.average_fqs >= 50
            else "Poor"
        )
        lines.append(f"**Average FQS:** {result.average_fqs:.1f}/100 ({fqs_rating})")

    return "\n".join(lines)


def generate_variable_assessment(result: UnifiedValidationResult) -> str:
    """Generate per-variable assessment section."""
    lines = [
        "## Detailed Variable Analysis",
        "",
    ]

    for var in result.variable_results:
        # Status emoji
        status_emoji = get_status_emoji(var.passed, var.actual_mape)
        assessment = get_mape_assessment(var.actual_mape)

        lines.append(f"### {status_emoji} {var.display_name}")
        lines.append("| Metric | Value | Target | Status | Interpretation |")
        lines.append("|--------|-------|--------|--------|----------------|")

        # MAPE row - Story 6.27: Show primary metric indicator
        if var.actual_mape is not None:
            # Determine status based on pass/fail and which metric was used
            mase_only_pass = getattr(var, "mase_only_pass", False)
            primary_metric = getattr(var, "primary_metric_used", "mape")

            if mase_only_pass:
                mape_status = "✅ MASE-ONLY"
                mase_val = var.metrics.mase if var.metrics else None
                mape_interp = (
                    f"MASE {mase_val:.2f} passed (MAPE waived)"
                    if mase_val
                    else "MASE passed (MAPE waived)"
                )
            elif var.passed:
                mape_status = f"✅ PASS ({primary_metric.upper()})"
                mape_interp = f"{assessment.title()} for FP&A reporting"
            else:
                mape_status = "❌ FAIL"
                mape_interp = f"{assessment.title()} - needs investigation"

            lines.append(
                f"| MAPE | {var.actual_mape:.2f}% | <{var.target_mape}% | "
                f"{mape_status} | {mape_interp} |"
            )
        else:
            lines.append("| MAPE | N/A | - | ⚠️ N/A | No data available |")

        # Multi-metric rows (if available)
        if var.metrics:
            m = var.metrics

            if m.mase is not None:
                mase_status = "✅ PASS" if m.mase < 1.0 else "❌ FAIL"
                mase_interp = (
                    f"{'Beats' if m.mase < 1.0 else 'Worse than'} naïve by "
                    f"{abs(1 - m.mase) * 100:.0f}%"
                )
                lines.append(f"| MASE | {m.mase:.2f} | <1.0 | {mase_status} | {mase_interp} |")

            if m.smape is not None:
                lines.append(f"| SMAPE | {m.smape:.2f}% | - | INFO | Symmetric error |")

            if m.rmse is not None:
                lines.append(f"| RMSE | {m.rmse:.2f} | - | INFO | Error in original units |")

            if m.mae is not None:
                lines.append(f"| MAE | {m.mae:.2f} | - | INFO | Average absolute error |")

            if m.bias is not None:
                bias_direction = "over" if m.bias > 0 else "under"
                bias_status = (
                    "⚠️ WARN" if m.rmse is not None and abs(m.bias) > m.rmse * 0.5 else "INFO"
                )
                lines.append(
                    f"| Bias | {m.bias:+.2f} | ~0 | {bias_status} | "
                    f"Tends to {bias_direction}-predict |"
                )

            if m.fqs is not None:
                fqs_rating = (
                    "Excellent"
                    if m.fqs >= 80
                    else "Good"
                    if m.fqs >= 65
                    else "Moderate"
                    if m.fqs >= 50
                    else "Poor"
                )
                lines.append(f"| FQS | {m.fqs:.1f}/100 | ≥65 | INFO | {fqs_rating} quality |")

        # Assessment and recommendations
        lines.append("")
        if var.assessment_text:
            lines.append(f"**Assessment:** {var.assessment_text}")
        else:
            lines.append(f"**Assessment:** {assessment.title()} performance.")

        if var.recommendations:
            lines.append("")
            lines.append("**Recommendations:**")
            for i, rec in enumerate(var.recommendations, 1):
                lines.append(f"{i}. {rec}")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def generate_improvement_priorities(result: UnifiedValidationResult) -> str:
    """Generate improvement priorities section."""
    # Categorize variables
    critical_vars = []
    warning_vars = []
    good_vars = []

    for var in result.variable_results:
        if var.actual_mape is None:
            continue

        # Check MASE for critical (worse than naïve)
        if var.metrics and var.metrics.mase is not None and var.metrics.mase > 1.0:
            critical_vars.append(var)
        elif not var.passed:
            warning_vars.append(var)
        elif var.actual_mape > var.target_mape * 0.9:  # Within 10% of threshold
            warning_vars.append(var)
        else:
            good_vars.append(var)

    lines = [
        "## Action Items",
        "",
    ]

    # Critical section
    if critical_vars:
        lines.append("### 🔴 Critical - Requires Immediate Attention")
        lines.append("| Variable | Issue | MASE | Recommendation |")
        lines.append("|----------|-------|------|----------------|")
        for var in critical_vars:
            mase_val = var.metrics.mase if var.metrics and var.metrics.mase else "N/A"
            rec = var.recommendations[0] if var.recommendations else "Evaluate model configuration"
            lines.append(f"| {var.display_name} | MASE >1.0 | {mase_val:.2f} | {rec} |")
        lines.append("")

    # Warning section
    if warning_vars:
        lines.append("### 🟡 Warning - Monitor & Improve")
        lines.append("| Variable | Issue | Current | Target | Gap |")
        lines.append("|----------|-------|---------|--------|-----|")
        for var in warning_vars:
            if var.actual_mape is not None:
                gap = var.actual_mape - var.target_mape
                gap_str = f"{gap:+.2f}%" if gap > 0 else f"{gap:.2f}%"
                issue = "Exceeds target" if gap > 0 else "Near threshold"
                lines.append(
                    f"| {var.display_name} | {issue} | {var.actual_mape:.2f}% | "
                    f"{var.target_mape}% | {gap_str} |"
                )
        lines.append("")

    # Good section
    if good_vars:
        lines.append("### 🟢 Good Performance - No Action Required")
        good_names = [var.display_name for var in good_vars]
        lines.append(", ".join(good_names))
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# Story 6.27: Failure Diagnosis and Actionable Guidance
# =============================================================================


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


def generate_cross_variable_analysis(result: UnifiedValidationResult) -> str:
    """Generate cross-variable comparison section."""
    # Get variables with MASE values
    vars_with_mase = [
        (var.display_name, var.metrics.mase)
        for var in result.variable_results
        if var.metrics and var.metrics.mase is not None
    ]

    if not vars_with_mase:
        return ""

    # Sort by MASE (lower is better)
    vars_with_mase.sort(key=lambda x: x[1])

    lines = [
        "## Cross-Variable Performance",
        "",
        "### MASE Ranking (Lower is Better)",
        "| Rank | Variable | MASE | vs Naïve |",
        "|------|----------|------|----------|",
    ]

    for i, (name, mase) in enumerate(vars_with_mase, 1):
        if mase < 1.0:
            comparison = f"{(1 - mase) * 100:.0f}% better"
        else:
            comparison = f"{(mase - 1) * 100:.0f}% worse"
        lines.append(f"| {i} | {name} | {mase:.2f} | {comparison} |")

    lines.append("")

    # Best and worst performers
    best_vars = vars_with_mase[:3]
    worst_vars = [v for v in vars_with_mase if v[1] > 1.0]

    if best_vars:
        lines.append("### Variables Where Model Adds Most Value")
        for i, (name, mase) in enumerate(best_vars, 1):
            improvement = (1 - mase) * 100
            lines.append(
                f"{i}. **{name}** - MASE {mase:.2f} ({improvement:.0f}% better than naïve)"
            )
        lines.append("")

    if worst_vars:
        lines.append("### Variables Where Model Needs Work")
        for i, (name, mase) in enumerate(worst_vars, 1):
            degradation = (mase - 1) * 100
            lines.append(f"{i}. **{name}** - MASE {mase:.2f} ({degradation:.0f}% worse than naïve)")
        lines.append("")

    # FQS Ranking Section
    vars_with_fqs = [
        (var.display_name, var.metrics.fqs)
        for var in result.variable_results
        if var.metrics and var.metrics.fqs is not None
    ]

    if vars_with_fqs:
        # Sort by FQS (higher is better)
        vars_with_fqs.sort(key=lambda x: x[1], reverse=True)

        lines.append("### FQS Ranking (Higher is Better)")
        lines.append("| Rank | Variable | FQS | Rating |")
        lines.append("|------|----------|-----|--------|")

        for i, (name, fqs) in enumerate(vars_with_fqs, 1):
            rating = (
                "Excellent"
                if fqs >= 80
                else "Good"
                if fqs >= 65
                else "Moderate"
                if fqs >= 50
                else "Poor"
            )
            lines.append(f"| {i} | {name} | {fqs:.1f} | {rating} |")

        lines.append("")

    return "\n".join(lines)


def generate_markdown_report(result: UnifiedValidationResult) -> str:
    """Generate full markdown report with all sections.

    Args:
        result: UnifiedValidationResult from validation run

    Returns:
        Complete markdown report as string
    """
    sections = [
        generate_executive_summary(result),
        "",
        METRIC_EXPLANATIONS,
        "",
        generate_variable_assessment(result),
        generate_improvement_priorities(result),
        generate_actionable_guidance(result),  # Story 6.27: Add actionable guidance
        generate_cross_variable_analysis(result),
    ]

    return "\n".join(sections)


def generate_console_summary(result: UnifiedValidationResult) -> str:
    """Generate abbreviated console summary.

    Args:
        result: UnifiedValidationResult from validation run

    Returns:
        Console-friendly summary string
    """
    lines = [
        "",
        "=" * 70,
        "FORECASTING VALIDATION SUMMARY",
        "=" * 70,
        "",
    ]

    # Overall status
    if result.quality_gate and result.quality_gate.passed:
        lines.append("QUALITY GATE: ✅ PASSED")
    else:
        lines.append("QUALITY GATE: ❌ FAILED")

    lines.append("")
    lines.append(
        f"Variables: {result.variables_passed}/{result.variables_tested} passed "
        f"({result.pass_rate:.1%})"
    )
    lines.append(f"Average MAPE: {result.average_mape:.2f}%")

    if result.average_mase is not None:
        status = "✅" if result.average_mase < 1.0 else "❌"
        lines.append(f"Average MASE: {result.average_mase:.2f} {status}")

    lines.append("")
    lines.append("-" * 70)
    lines.append(f"{'Variable':<25} {'MAPE':<12} {'MASE':<10} {'Status':<10}")
    lines.append("-" * 70)

    for var in result.variable_results:
        mape_str = f"{var.actual_mape:.2f}%" if var.actual_mape else "N/A"
        mase_str = f"{var.metrics.mase:.2f}" if var.metrics and var.metrics.mase else "N/A"
        status = "PASS" if var.passed else "FAIL"
        lines.append(f"{var.display_name:<25} {mape_str:<12} {mase_str:<10} {status:<10}")

    lines.append("=" * 70)
    lines.append("")

    return "\n".join(lines)


def generate_validation_report(
    result: UnifiedValidationResult,
    output_dir: Path = Path("reports"),
    formats: list[str] | None = None,
) -> dict[str, Path]:
    """Generate comprehensive validation report with actionable guidance.

    Args:
        result: UnifiedValidationResult from run_unified_validation()
        output_dir: Directory for report files
        formats: Output formats to generate (default: ["markdown", "json", "console"])

    Returns:
        Dict mapping format name to output file path
    """
    if formats is None:
        formats = ["markdown", "json", "console"]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    outputs: dict[str, Path] = {}

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    if "markdown" in formats:
        md_content = generate_markdown_report(result)
        md_path = output_dir / f"validation-report-{timestamp}.md"
        md_path.write_text(md_content)
        outputs["markdown"] = md_path
        logger.info(f"Markdown report saved to {md_path}")

    if "json" in formats:
        json_path = output_dir / f"validation-report-{timestamp}.json"
        data = asdict(result)
        data["_schema_version"] = "2.0"
        data["_source"] = "raglite-unified-validation"
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        outputs["json"] = json_path
        logger.info(f"JSON report saved to {json_path}")

    if "console" in formats:
        console_output = generate_console_summary(result)
        print(console_output)
        # No file path for console output

    return outputs


def print_report_summary(result: UnifiedValidationResult) -> None:
    """Print report summary to console."""
    print(generate_console_summary(result))
