"""
Report generation functions for model selection job.

This module provides functions to generate JSON and Markdown reports,
and print execution summaries.
"""

import json
from datetime import datetime
from pathlib import Path

from raglite.forecasting.model_selection import ModelSelectionResult


async def generate_reports(
    results: dict[str, ModelSelectionResult], output_dir: str, runtime_minutes: float
) -> None:
    """Generate JSON and Markdown reports.

    Args:
        results: Dictionary of results
        output_dir: Output directory path
        runtime_minutes: Total runtime in minutes
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # JSON report
    json_path = output_path / f"model-selection-{timestamp}.json"
    json_data = {
        "timestamp": timestamp,
        "runtime_minutes": runtime_minutes,
        "variables_processed": len(results),
        "results": {
            name: {
                "best_model": r.best_model,
                "best_mape": r.best_mape,
                "best_mase": r.best_mase,
                "use_regressors": r.best_with_regressors,
                "regressor_set": r.best_regressor_set,
            }
            for name, r in results.items()
        },
    }
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)

    # Markdown report
    md_path = output_path / f"model-selection-{timestamp}.md"
    md_content = generate_markdown_report(results, timestamp)
    with open(md_path, "w") as f:
        f.write(md_content)

    print("\nReports generated:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")


def generate_markdown_report(results: dict[str, ModelSelectionResult], timestamp: str) -> str:
    """Generate markdown report content.

    Args:
        results: Dictionary of results
        timestamp: Report timestamp

    Returns:
        Markdown report content as string
    """
    lines = [
        f"# Model Selection Report - {timestamp}",
        "",
        "## Summary",
        "",
        f"- Variables processed: {len(results)}",
        f"- Generated at: {timestamp}",
        "",
        "## Results",
        "",
        "| Variable | Best Model | MAPE | MASE | Regressors |",
        "|----------|------------|------|------|------------|",
    ]

    for name, result in sorted(results.items(), key=lambda x: x[1].best_mape):
        regs = ", ".join(result.best_regressor_set) if result.best_with_regressors else "None"
        lines.append(
            f"| {name} | {result.best_model} | {result.best_mape:.2%} | {result.best_mase:.2f} | {regs} |"
        )

    lines.extend(
        [
            "",
            "## Best Performers",
            "",
        ]
    )

    # Top 5 by MAPE
    sorted_results = sorted(results.items(), key=lambda x: x[1].best_mape)
    for name, result in sorted_results[:5]:
        lines.append(f"- **{name}**: {result.best_mape:.2%} ({result.best_model})")

    return "\n".join(lines)


def print_summary(
    results: dict[str, ModelSelectionResult],
    errors: list[str],
    variables: list[str],
) -> None:
    """Print execution summary.

    Args:
        results: Dictionary of results
        errors: List of error messages
        variables: List of variable names processed
    """
    print("\n" + "=" * 60)
    print("MODEL SELECTION COMPLETE")
    print("=" * 60)
    print(f"Variables processed: {len(results)}/{len(variables)}")
    if errors:
        print(f"Errors: {len(errors)}")
        for err in errors:
            print(f"  - {err}")

    if results:
        # M1 fix: Show top 3 best performers
        sorted_results = sorted(results.items(), key=lambda x: x[1].best_mape)
        print("\nBest performers:")
        for i, (var_name, result) in enumerate(sorted_results[:3], 1):
            print(f"  {i}. {var_name}: {result.best_mape:.2%} ({result.best_model})")

        worst = max(results.items(), key=lambda x: x[1].best_mape)
        print(f"\nNeeds attention: {worst[0]} ({worst[1].best_mape:.2%})")
