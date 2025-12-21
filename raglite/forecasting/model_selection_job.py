"""
Batch model selection job for slash command execution.

This module provides functions for running model selection in batch mode,
used by the /model-selection slash command and model-selection-executor subagent.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from raglite.external_data.storage import cache_model_selection
from raglite.forecasting.model_selection import (
    CANDIDATE_MODELS,
    ModelSelectionResult,
    select_best_model,
)

logger = logging.getLogger(__name__)

# All 20 forecasting variables
ALL_VARIABLES = [
    "revenue",
    "turnover",
    "ebitda",
    "variable_cost",
    "electricity_cost",
    "thermal_cost",
    "sales_volume",
    "capacity_utilization",
    "avg_selling_price",
    "ttf_gas",
    "api2_coal",
    "diesel",
    "eurostat_electricity",
    "gdp_growth",
    "inflation",
    "euribor_3m",
    "construction_output",
    "building_permits",
    "construction_confidence",
    "co2_eua_price",
]


async def run_batch_model_selection(
    variables: list[str] | None = None,
    workers: int = 4,
    force_refresh: bool = False,
    output_dir: str = "reports",
) -> dict[str, ModelSelectionResult]:
    """Run model selection for multiple variables in parallel.

    Args:
        variables: List of variable names (default: ALL_VARIABLES)
        workers: Number of parallel workers (default: 4)
        force_refresh: Ignore existing cache (default: False)
        output_dir: Directory for report output (default: "reports")

    Returns:
        Dictionary of variable_name -> ModelSelectionResult
    """
    import time

    start_time = time.time()
    variables = variables or ALL_VARIABLES
    results: dict[str, ModelSelectionResult] = {}
    errors: list[str] = []

    # Create semaphore for parallel limiting
    semaphore = asyncio.Semaphore(workers)

    async def process_variable(
        var_name: str, index: int
    ) -> tuple[str, ModelSelectionResult | None]:
        async with semaphore:
            print(
                f"[{index}/{len(variables)}] {var_name}: Testing {len(CANDIDATE_MODELS)} models..."
            )
            try:
                # TODO: Fetch historical_data for variable_name from storage
                # For now this is a placeholder - Story 7b-6 will implement data fetching
                import pandas as pd

                historical_data = pd.Series()  # Placeholder

                result = await select_best_model(
                    var_name, historical_data=historical_data, force_refresh=force_refresh
                )
                print(
                    f"  -> Best: {result.best_model} | MAPE: {result.best_mape:.2%} | MASE: {result.best_mase:.2f}"
                )

                # Cache result
                await cache_model_selection(result)
                return var_name, result
            except Exception as e:
                logger.error(f"Error processing {var_name}: {e}")
                errors.append(f"{var_name}: {e}")
                return var_name, None

    # Run in parallel
    tasks = [process_variable(var, i + 1) for i, var in enumerate(variables)]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results
    for item in completed:
        if isinstance(item, Exception):
            logger.error(f"Task error: {item}")
            errors.append(str(item))
        elif item is not None:
            var_name, result = item  # type: ignore[misc]
            if result is not None:
                results[var_name] = result

    # Calculate runtime
    runtime_minutes = (time.time() - start_time) / 60

    # Generate reports
    await _generate_reports(results, output_dir, runtime_minutes)

    # Print summary
    _print_summary(results, errors, variables)

    return results


async def run_single_variable_selection(
    variable: str,
    force_refresh: bool = False,
    dry_run: bool = False,
) -> ModelSelectionResult | None:
    """Run model selection for a single variable.

    Args:
        variable: Variable name
        force_refresh: Ignore existing cache
        dry_run: Preview without caching

    Returns:
        ModelSelectionResult or None if error
    """
    print(f"Running model selection for: {variable}")
    print(f"Testing {len(CANDIDATE_MODELS)} models...")

    try:
        # TODO: Fetch historical_data for variable from storage
        # For now this is a placeholder - Story 7b-6 will implement data fetching
        import pandas as pd

        historical_data = pd.Series()  # Placeholder

        result = await select_best_model(
            variable, historical_data=historical_data, force_refresh=force_refresh
        )

        print(f"\n{variable.upper()} Model Selection Results:")
        print(f"Best Model: {result.best_model}")
        print(f"MAPE: {result.best_mape:.2%} | MASE: {result.best_mase:.2f}")
        if result.best_with_regressors:
            print(f"Regressors: {', '.join(result.best_regressor_set)}")
        else:
            print("Regressors: None")

        # Print comparison table (M2 fix)
        if result.candidate_results:
            print("\nModel Comparison:")
            print("| Model    | MAPE   | MASE | Status |")
            print("|----------|--------|------|--------|")

            # Sort by MAPE
            sorted_results = sorted(
                result.candidate_results.items(), key=lambda x: x[1].get("mape", float("inf"))
            )

            for model_key, metrics in sorted_results[:10]:  # Top 10
                model_name = model_key.rsplit("_", 1)[0]  # Remove _True/_False suffix
                mape = metrics.get("mape", float("inf"))
                mase = metrics.get("mase", float("inf"))
                is_best = model_name == result.best_model
                status = "BEST" if is_best else ""

                if mape != float("inf"):
                    print(f"| {model_name:8} | {mape:6.2%} | {mase:4.2f} | {status:6} |")

        # Cache unless dry run
        if not dry_run:
            await cache_model_selection(result)
            print("\nResult cached to PostgreSQL.")
        else:
            print("\n[DRY RUN] Result not cached.")

        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        return None


async def _generate_reports(
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
    md_content = _generate_markdown_report(results, timestamp)
    with open(md_path, "w") as f:
        f.write(md_content)

    print("\nReports generated:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")


def _generate_markdown_report(results: dict[str, ModelSelectionResult], timestamp: str) -> str:
    """Generate markdown report content."""
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


def _print_summary(
    results: dict[str, ModelSelectionResult],
    errors: list[str],
    variables: list[str],
) -> None:
    """Print execution summary."""
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
