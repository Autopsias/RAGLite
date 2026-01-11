"""Report section generators for validation reports.

Story 6.26: Multi-Metric Validation Enhancement
Individual section generators for executive summary, variable assessment, and cross-variable analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from raglite.forecasting.validation_schema import UnifiedValidationResult

from raglite.forecasting.report_helpers_assessment import (
    get_mape_assessment,
    get_status_emoji,
)


def generate_executive_summary(
    result: UnifiedValidationResult,
    request_id: str | None = None,
    include_recommendations: bool = True,
) -> str:
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


def _generate_mape_row(var: Any, assessment: str) -> str:
    """Generate MAPE table row for a variable."""
    if var.actual_mape is None:
        return "| MAPE | N/A | - | ⚠️ N/A | No data available |"

    mase_only_pass = getattr(var, "mase_only_pass", False)
    primary_metric = getattr(var, "primary_metric_used", "mape")

    if mase_only_pass:
        mase_val = var.metrics.mase if var.metrics else None
        mape_interp = (
            f"MASE {mase_val:.2f} passed (MAPE waived)" if mase_val else "MASE passed (MAPE waived)"
        )
        return f"| MAPE | {var.actual_mape:.2f}% | <{var.target_mape}% | ✅ MASE-ONLY | {mape_interp} |"
    elif var.passed:
        return f"| MAPE | {var.actual_mape:.2f}% | <{var.target_mape}% | ✅ PASS ({primary_metric.upper()}) | {assessment.title()} for FP&A reporting |"
    else:
        return f"| MAPE | {var.actual_mape:.2f}% | <{var.target_mape}% | ❌ FAIL | {assessment.title()} - needs investigation |"


def _generate_metrics_rows(metrics: Any) -> list[str]:
    """Generate table rows for multi-metric data."""
    rows = []
    if metrics.mase is not None:
        status = "✅ PASS" if metrics.mase < 1.0 else "❌ FAIL"
        interp = f"{'Beats' if metrics.mase < 1.0 else 'Worse than'} naïve by {abs(1 - metrics.mase) * 100:.0f}%"
        rows.append(f"| MASE | {metrics.mase:.2f} | <1.0 | {status} | {interp} |")
    if metrics.smape is not None:
        rows.append(f"| SMAPE | {metrics.smape:.2f}% | - | INFO | Symmetric error |")
    if metrics.rmse is not None:
        rows.append(f"| RMSE | {metrics.rmse:.2f} | - | INFO | Error in original units |")
    if metrics.mae is not None:
        rows.append(f"| MAE | {metrics.mae:.2f} | - | INFO | Average absolute error |")
    if metrics.bias is not None:
        direction = "over" if metrics.bias > 0 else "under"
        status = (
            "⚠️ WARN"
            if metrics.rmse is not None and abs(metrics.bias) > metrics.rmse * 0.5
            else "INFO"
        )
        rows.append(
            f"| Bias | {metrics.bias:+.2f} | ~0 | {status} | Tends to {direction}-predict |"
        )
    if metrics.fqs is not None:
        rating = (
            "Excellent"
            if metrics.fqs >= 80
            else "Good"
            if metrics.fqs >= 65
            else "Moderate"
            if metrics.fqs >= 50
            else "Poor"
        )
        rows.append(f"| FQS | {metrics.fqs:.1f}/100 | ≥65 | INFO | {rating} quality |")
    return rows


def generate_variable_assessment(result: UnifiedValidationResult) -> str:
    """Generate per-variable assessment section."""
    lines = ["## Detailed Variable Analysis", ""]

    for var in result.variable_results:
        status_emoji = get_status_emoji(var.passed, var.actual_mape)
        assessment = get_mape_assessment(var.actual_mape)

        lines.append(f"### {status_emoji} {var.display_name}")
        lines.append("| Metric | Value | Target | Status | Interpretation |")
        lines.append("|--------|-------|--------|--------|----------------|")
        lines.append(_generate_mape_row(var, assessment))

        if var.metrics:
            lines.extend(_generate_metrics_rows(var.metrics))

        lines.append("")
        lines.append(
            f"**Assessment:** {var.assessment_text or f'{assessment.title()} performance.'}"
        )

        if var.recommendations:
            lines.append("")
            lines.append("**Recommendations:**")
            for i, rec in enumerate(var.recommendations, 1):
                lines.append(f"{i}. {rec}")

        lines.extend(["", "---", ""])

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
