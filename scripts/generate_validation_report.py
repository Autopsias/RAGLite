#!/usr/bin/env python3
"""Generate validation report for Epic 4 forecasting and insights.

Story 4.10 AC5: Generates markdown report with test results, metrics,
and improvement recommendations.

Usage:
    python scripts/generate_validation_report.py
    python scripts/generate_validation_report.py --output docs/reports/validation-report.md
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.validation.test_epic4_e2e_validation import (  # noqa: E402
    Epic4ValidationOrchestrator,
    Epic4ValidationResult,
    create_comprehensive_test_data,
)
from tests.validation.test_forecast_accuracy import ForecastValidationResult  # noqa: E402
from tests.validation.test_insight_quality import InsightValidationResult  # noqa: E402
from tests.validation.test_recommendation_alignment import (  # noqa: E402
    RecommendationValidationResult,
)


class ValidationReportGenerator:
    """Generates markdown validation report from Epic4ValidationResult.

    Story 4.10 Task 5.1-5.4: Report generation with executive summary
    and improvement recommendations.
    """

    def __init__(self, output_dir: Path | None = None):
        """Initialize report generator.

        Args:
            output_dir: Output directory for reports (default: docs/sprint-artifacts)
        """
        self.output_dir = output_dir or PROJECT_ROOT / "docs" / "sprint-artifacts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        result: Epic4ValidationResult,
        output_path: Path | None = None,
    ) -> str:
        """Generate markdown report from validation result.

        Args:
            result: Complete validation result
            output_path: Optional specific output path

        Returns:
            Generated report content as string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        report_name = f"validation-report-4-10-{timestamp}.md"
        final_path = output_path or self.output_dir / report_name

        # Generate report sections
        content = self._generate_header(result, timestamp)
        content += self._generate_executive_summary(result)
        content += self._generate_forecast_section(result.forecast_results)
        content += self._generate_insight_section(result.insight_result)
        content += self._generate_recommendation_section(result.recommendation_result)
        content += self._generate_improvement_section(result.improvement_recommendations)
        content += self._generate_methodology_section()
        content += self._generate_footer(timestamp)

        # Write report
        final_path.write_text(content)
        print(f"Report generated: {final_path}")

        return content

    def _generate_header(self, result: Epic4ValidationResult, timestamp: str) -> str:
        """Generate report header with status badges."""
        overall_status = "PASS" if result.overall_passed else "FAIL"
        status_emoji = "check" if result.overall_passed else "x"

        return f"""# Epic 4 Validation Report

**Story:** 4.10 - Forecasting & Insights Test Suite
**Generated:** {timestamp}
**Status:** :{status_emoji}: **{overall_status}**

---

"""

    def _generate_executive_summary(self, result: Epic4ValidationResult) -> str:
        """Generate executive summary section."""
        forecast_status = "PASS" if result.forecast_passed else "FAIL"
        insight_status = "PASS" if result.insight_passed else "FAIL"
        rec_status = "PASS" if result.recommendation_passed else "FAIL"

        # Calculate totals
        total_scenarios = (
            result.insight_result.total_scenarios + result.recommendation_result.total_scenarios
        )
        passed_scenarios = (
            result.insight_result.passed_scenarios + result.recommendation_result.aligned_scenarios
        )

        return f"""## Executive Summary

| Criteria | Target | Actual | Status |
|----------|--------|--------|--------|
| Forecast Accuracy (MAPE) | ≤15% | {result.average_mape:.1f}% | **{forecast_status}** |
| Insight Relevance | ≥75% | {result.insight_result.relevance_rate:.1f}% | **{insight_status}** |
| Recommendation Alignment | ≥80% | {result.recommendation_result.alignment_rate:.1f}% | **{rec_status}** |

**Total Metrics Validated:** {len(result.forecast_results)}
**Total Scenarios Tested:** {total_scenarios}
**Scenarios Passed:** {passed_scenarios}/{total_scenarios}

---

"""

    def _generate_forecast_section(self, forecast_results: list[ForecastValidationResult]) -> str:
        """Generate forecast accuracy section."""
        content = """## 1. Forecast Accuracy (NFR10)

**Target:** MAPE ≤15% for key indicators (revenue, expenses, cash flow)

### Results by Metric

| Metric | MAPE | Train Points | Test Points | Status |
|--------|------|--------------|-------------|--------|
"""
        for r in forecast_results:
            status = "PASS" if r.passed else "FAIL"
            content += f"| {r.metric_name} | {r.mape:.1f}% | {r.data_points_train} | {r.data_points_test} | {status} |\n"

        avg_mape = (
            sum(r.mape for r in forecast_results) / len(forecast_results) if forecast_results else 0
        )
        content += f"\n**Average MAPE:** {avg_mape:.1f}%\n\n"

        # Add per-period analysis for failed forecasts
        failed = [r for r in forecast_results if not r.passed]
        if failed:
            content += "### Failed Forecast Details\n\n"
            for r in failed:
                content += f"**{r.metric_name}:**\n"
                content += f"- MAPE: {r.mape:.1f}% (threshold: 15%)\n"
                if r.per_period_errors:
                    max_error = max(r.per_period_errors)
                    min_error = min(r.per_period_errors)
                    content += f"- Error range: {min_error:.1f}% - {max_error:.1f}%\n"
                content += "\n"

        content += "---\n\n"
        return content

    def _generate_insight_section(self, insight_result: InsightValidationResult) -> str:
        """Generate insight quality section."""
        content = f"""## 2. Insight Quality (PRD Criterion)

**Target:** ≥75% insights rated useful/actionable

### Results Summary

- **Total Scenarios:** {insight_result.total_scenarios}
- **Passed Scenarios:** {insight_result.passed_scenarios}
- **Relevance Rate:** {insight_result.relevance_rate:.1f}%
- **Status:** {"PASS" if insight_result.passed else "FAIL"}

### Category Breakdown

| Category | Count |
|----------|-------|
"""
        for category, count in sorted(insight_result.category_breakdown.items()):
            content += f"| {category} | {count} |\n"

        # Add failed scenario details
        failed_scenarios = [s for s in insight_result.scenario_results if not s.get("passed")]
        if failed_scenarios:
            content += "\n### Failed Scenarios\n\n"
            for s in failed_scenarios[:5]:  # Show top 5 failures
                content += f"- **{s['scenario_id']}:** {s.get('reason', 'Unknown')}\n"
            if len(failed_scenarios) > 5:
                content += f"- *...and {len(failed_scenarios) - 5} more*\n"

        content += "\n---\n\n"
        return content

    def _generate_recommendation_section(self, rec_result: RecommendationValidationResult) -> str:
        """Generate recommendation alignment section."""
        content = f"""## 3. Recommendation Alignment (PRD Criterion)

**Target:** ≥80% alignment with expert analysis

### Results Summary

- **Total Scenarios:** {rec_result.total_scenarios}
- **Aligned Scenarios:** {rec_result.aligned_scenarios}
- **Alignment Rate:** {rec_result.alignment_rate:.1f}%
- **Status:** {"PASS" if rec_result.passed else "FAIL"}

### Category Breakdown

| Category | Count |
|----------|-------|
"""
        for category, count in sorted(rec_result.category_breakdown.items()):
            content += f"| {category} | {count} |\n"

        # Add misaligned scenario details
        misaligned = [s for s in rec_result.scenario_results if not s.get("aligned")]
        if misaligned:
            content += "\n### Misaligned Scenarios\n\n"
            for s in misaligned[:5]:  # Show top 5
                expected = s.get("expected_category", "N/A")
                actual = s.get("generated_category", "N/A")
                content += f"- **{s['scenario_id']}:** Expected {expected}, got {actual}\n"
            if len(misaligned) > 5:
                content += f"- *...and {len(misaligned) - 5} more*\n"

        content += "\n---\n\n"
        return content

    def _generate_improvement_section(self, recommendations: list[str]) -> str:
        """Generate improvement recommendations section."""
        content = """## 4. Improvement Recommendations

Based on validation results, the following improvements are recommended:

"""
        for i, rec in enumerate(recommendations, 1):
            content += f"{i}. {rec}\n\n"

        content += "---\n\n"
        return content

    def _generate_methodology_section(self) -> str:
        """Generate methodology section for transparency."""
        return """## 5. Validation Methodology

### Forecast Accuracy (AC1, AC2)

- **Method:** Backtesting with 80% train / 20% test holdout
- **Metric:** Mean Absolute Percentage Error (MAPE)
- **Threshold:** ≤15% per NFR10
- **Data Requirements:** Minimum 8 data points (2 years quarterly)

### Insight Quality (AC3)

- **Method:** Expert-labeled scenario validation
- **Scoring:** Category match + Priority range + Supporting data presence
- **Threshold:** ≥75% scenarios pass all checks
- **Scenarios:** 10 expert-labeled test cases

### Recommendation Alignment (AC4)

- **Method:** Expert-labeled ground truth comparison
- **Scoring:** Category match + Impact score range (±2 tolerance) + Actionable steps
- **Threshold:** ≥80% alignment rate
- **Scenarios:** 8 expert-labeled test cases

---

"""

    def _generate_footer(self, timestamp: str) -> str:
        """Generate report footer."""
        return f"""## Appendix

- **Report Generated:** {timestamp}
- **Tool Version:** Story 4.10 Validation Framework
- **Contact:** RAGLite Development Team

---

*This report was automatically generated by the Epic 4 validation pipeline.*
"""


async def run_validation_and_generate_report(
    output_path: Path | None = None,
    use_mock_llm: bool = True,
) -> Epic4ValidationResult:
    """Run validation and generate report.

    Args:
        output_path: Optional specific output path for report
        use_mock_llm: Whether to mock LLM calls (default True for testing)

    Returns:
        Epic4ValidationResult from validation run
    """
    print("Starting Epic 4 validation...")

    # Create orchestrator with default thresholds
    orchestrator = Epic4ValidationOrchestrator(
        forecast_threshold=15.0,
        insight_threshold=75.0,
        recommendation_threshold=80.0,
    )

    # Create comprehensive test data
    test_data = create_comprehensive_test_data(months=24)
    print(f"Created test data: {list(test_data.keys())}")

    # Run validation (with optional LLM mocking)
    if use_mock_llm:
        with patch("raglite.shared.clients.get_mistral_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.choices = [
                AsyncMock(
                    message=AsyncMock(
                        content=(
                            "SUMMARY: Financial analysis complete\n"
                            "RATIONALE: Based on historical data patterns\n"
                            "ACTION: Review findings and take action"
                        )
                    )
                )
            ]
            mock_client.return_value.chat.complete.return_value = mock_response

            result = await orchestrator.run_full_validation(forecast_data=test_data)
    else:
        result = await orchestrator.run_full_validation(forecast_data=test_data)

    print(f"Validation complete. Overall: {'PASS' if result.overall_passed else 'FAIL'}")

    # Generate report
    generator = ValidationReportGenerator()
    generator.generate_report(result, output_path)

    return result


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="Generate Epic 4 validation report")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output path for report (default: docs/sprint-artifacts/validation-report-4-10-{date}.md)",
    )
    parser.add_argument(
        "--no-mock",
        action="store_true",
        help="Disable LLM mocking (use real API calls)",
    )
    args = parser.parse_args()

    result = asyncio.run(
        run_validation_and_generate_report(
            output_path=args.output,
            use_mock_llm=not args.no_mock,
        )
    )

    # Exit with appropriate code
    sys.exit(0 if result.overall_passed else 1)


if __name__ == "__main__":
    main()
