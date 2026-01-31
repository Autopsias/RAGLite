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
        UnifiedValidationResult,
    )

# Re-export from helper modules (facade pattern)
from raglite.forecasting.report_helpers_assessment import (
    MAPE_THRESHOLDS,
    MASE_THRESHOLDS,
    METRIC_EXPLANATIONS,
    get_mape_assessment,
    get_mase_assessment,
    get_status_emoji,
)
from raglite.forecasting.report_helpers_diagnosis import (
    diagnose_failure,
    generate_actionable_guidance,
)
from raglite.forecasting.report_helpers_sections import (
    generate_console_summary,
    generate_cross_variable_analysis,
    generate_executive_summary,
    generate_improvement_priorities,
    generate_model_distribution,
    generate_variable_assessment,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Re-export constants for backward compatibility
__all__ = [
    "MAPE_THRESHOLDS",
    "MASE_THRESHOLDS",
    "METRIC_EXPLANATIONS",
    "get_mape_assessment",
    "get_mase_assessment",
    "get_status_emoji",
    "generate_executive_summary",
    "generate_variable_assessment",
    "generate_improvement_priorities",
    "diagnose_failure",
    "generate_actionable_guidance",
    "generate_cross_variable_analysis",
    "generate_model_distribution",
    "generate_markdown_report",
    "generate_console_summary",
    "generate_validation_report",
    "print_report_summary",
]


# =============================================================================
# Main Report Generation Functions
# =============================================================================


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
        generate_model_distribution(result),  # Phase 5: Model transparency
        generate_cross_variable_analysis(result),
    ]

    return "\n".join(sections)


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
