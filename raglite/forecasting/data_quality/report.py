"""Report generation for data quality audits.

Generates JSON and Markdown formatted reports.
"""

from __future__ import annotations

import json
from pathlib import Path

from raglite.forecasting.data_quality.check_result import CheckStatus
from raglite.forecasting.data_quality.orchestrator import AuditResult, VariableAuditResult


def audit_to_dict(audit: AuditResult) -> dict:
    """Convert AuditResult to dictionary for JSON serialization.

    Args:
        audit: Audit result to convert

    Returns:
        Dictionary suitable for JSON export
    """
    return {
        "timestamp": audit.timestamp,
        "runtime_seconds": round(audit.runtime_seconds, 2),
        "summary": {
            "variables_audited": audit.variables_audited,
            "total_checks": audit.total_checks,
            "passed": audit.total_passed,
            "warned": audit.total_warned,
            "failed": audit.total_failed,
            "skipped": audit.total_skipped,
            "pass_rate": round(audit.pass_rate * 100, 1),
            "variables_passed": audit.variables_passed,
            "variables_warned": audit.variables_warned,
            "variables_failed": audit.variables_failed,
        },
        "results": [_variable_result_to_dict(r) for r in audit.results],
    }


def _variable_result_to_dict(result: VariableAuditResult) -> dict:
    """Convert VariableAuditResult to dictionary."""
    return {
        "variable": result.variable,
        "status": result.status.value,
        "passed": result.passed,
        "warned": result.warned,
        "failed": result.failed,
        "skipped": result.skipped,
        "checks": [c.to_dict() for c in result.checks],
    }


def export_json(audit: AuditResult, output_path: str | Path) -> Path:
    """Export audit results to JSON file.

    Args:
        audit: Audit result to export
        output_path: Output file path

    Returns:
        Path to written file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(audit_to_dict(audit), f, indent=2, default=str)

    return output_path


def format_markdown(audit: AuditResult) -> str:
    """Format audit results as Markdown.

    Args:
        audit: Audit result to format

    Returns:
        Markdown formatted string
    """
    lines = []

    # Header
    lines.append("# Data Quality Audit Results")
    lines.append("")
    lines.append(f"**Timestamp:** {audit.timestamp}")
    lines.append(f"**Runtime:** {audit.runtime_seconds:.1f}s")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Variables audited: {audit.variables_audited}")
    lines.append(f"- Total checks: {audit.total_checks}")
    lines.append(f"- Pass rate: {audit.pass_rate:.1%}")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| PASS | {audit.total_passed} |")
    lines.append(f"| WARN | {audit.total_warned} |")
    lines.append(f"| FAIL | {audit.total_failed} |")
    lines.append(f"| SKIP | {audit.total_skipped} |")
    lines.append("")

    # Variable Summary Table
    lines.append("## Variable Summary")
    lines.append("")
    lines.append("| Variable | Status | Pass | Warn | Fail |")
    lines.append("|----------|--------|------|------|------|")

    for result in sorted(
        audit.results, key=lambda r: (0 if r.status == CheckStatus.FAIL else 1, r.variable)
    ):
        status_icon = _status_icon(result.status)
        lines.append(
            f"| {result.variable} | {status_icon} {result.status.value} | "
            f"{result.passed} | {result.warned} | {result.failed} |"
        )
    lines.append("")

    # Detailed Results (only failures and warnings)
    failed_results = [r for r in audit.results if r.status in (CheckStatus.FAIL, CheckStatus.WARN)]
    if failed_results:
        lines.append("## Issues Requiring Attention")
        lines.append("")

        for result in failed_results:
            lines.append(f"### {result.variable}")
            lines.append("")

            for check in result.checks:
                if check.status in (CheckStatus.FAIL, CheckStatus.WARN):
                    icon = _status_icon(check.status)
                    lines.append(f"- {icon} **{check.check_name}**: {check.message}")

                    if check.sample_rows:
                        lines.append("  - Sample data:")
                        for sample in check.sample_rows[:3]:
                            lines.append(f"    - `{sample}`")

            lines.append("")

    # All passed message
    if not failed_results:
        lines.append("## All Checks Passed!")
        lines.append("")
        lines.append("No issues requiring attention.")
        lines.append("")

    return "\n".join(lines)


def _status_icon(status: CheckStatus) -> str:
    """Get icon for status."""
    return {
        CheckStatus.PASS: "✓",
        CheckStatus.WARN: "!",
        CheckStatus.FAIL: "✗",
        CheckStatus.SKIP: "-",
    }.get(status, "?")


def print_console_report(audit: AuditResult, verbose: bool = False) -> None:
    """Print audit results to console.

    Args:
        audit: Audit result to print
        verbose: Show all checks, not just failures
    """
    print("=" * 70)
    print("DATA QUALITY AUDIT RESULTS")
    print("=" * 70)
    print()
    print(f"Timestamp: {audit.timestamp}")
    print(f"Runtime: {audit.runtime_seconds:.1f}s")
    print(f"Variables audited: {audit.variables_audited}")
    print(f"Total checks: {audit.total_checks}")
    print(f"Pass rate: {audit.pass_rate:.1%}")
    print()
    print("-" * 70)
    print(f"{'Variable':<25} {'Pass':>6} {'Warn':>6} {'Fail':>6} {'Status':<8}")
    print("-" * 70)

    for result in sorted(
        audit.results, key=lambda r: (0 if r.status == CheckStatus.FAIL else 1, r.variable)
    ):
        status_str = result.status.value
        print(
            f"{result.variable:<25} {result.passed:>6} {result.warned:>6} "
            f"{result.failed:>6} {status_str:<8}"
        )

        # Show failed/warned checks inline
        for check in result.checks:
            if check.status == CheckStatus.FAIL:
                print(f"  [X] {check.check_name}: {check.message}")
            elif check.status == CheckStatus.WARN:
                print(f"  [!] {check.check_name}: {check.message}")
            elif verbose and check.status == CheckStatus.PASS:
                print(f"  [✓] {check.check_name}: {check.message}")

    print("=" * 70)

    # Summary
    print()
    print("Summary:")
    print(
        f"  Variables: {audit.variables_passed} passed, {audit.variables_warned} warned, {audit.variables_failed} failed"
    )
    print(
        f"  Checks: {audit.total_passed} passed, {audit.total_warned} warned, {audit.total_failed} failed, {audit.total_skipped} skipped"
    )
    print()
