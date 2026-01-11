"""
Batch model selection job for slash command execution.

This module provides functions for running model selection in batch mode,
used by the /model-selection slash command and model-selection-executor subagent.
"""

import asyncio
import logging

import pandas as pd

from raglite.external_data.storage import cache_model_selection
from raglite.forecasting.model_selection import (
    CANDIDATE_MODELS,
    ModelSelectionResult,
    select_best_model,
)
from raglite.forecasting.model_selection_job_config import ALL_VARIABLES, VARIABLE_CONFIG
from raglite.forecasting.model_selection_job_fetch import fetch_historical_data
from raglite.forecasting.model_selection_job_regime import (
    add_regime_features,
    is_energy_affected_variable,
)
from raglite.forecasting.model_selection_job_reports import (
    generate_markdown_report,
    generate_reports,
    print_summary,
)
from raglite.forecasting.regressor_config import get_default_regressors
from raglite.forecasting.regressor_fetch import fetch_regressors_with_date_range

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    "ALL_VARIABLES",
    "VARIABLE_CONFIG",
    "add_regime_features",
    "is_energy_affected_variable",
    "fetch_historical_data",
    "run_batch_model_selection",
    "run_single_variable_selection",
    "generate_reports",
    "generate_markdown_report",
    "print_summary",
]

# Re-export private function names for test compatibility
_generate_reports = generate_reports
_print_summary = print_summary
_generate_markdown_report = generate_markdown_report


async def _process_single_variable(
    var_name: str,
    index: int,
    total: int,
    force_refresh: bool,
    errors: list[str],
    semaphore: asyncio.Semaphore,
) -> tuple[str, ModelSelectionResult | None]:
    """Process a single variable for model selection."""
    async with semaphore:
        print(f"[{index}/{total}] {var_name}: Testing {len(CANDIDATE_MODELS)} models...")
        try:
            historical_data = await fetch_historical_data(var_name, min_points=12)

            if historical_data is None or len(historical_data) < 12:
                msg = f"Insufficient data for {var_name} (need 12+ points)"
                logger.warning(msg)
                errors.append(msg)
                return var_name, None

            print(f"  -> Loaded {len(historical_data)} data points")

            # Fetch regressors
            regressor_names = get_default_regressors(var_name)
            external_regressors: dict[str, pd.Series] = {}
            if regressor_names:
                try:
                    external_regressors = await fetch_regressors_with_date_range(
                        metric=var_name,
                        historical_data_dates=list(historical_data.index),
                        periods_ahead=3,
                        regressor_names=regressor_names,
                    )
                    if external_regressors:
                        print(f"  -> Fetched {len(external_regressors)} regressors")
                except Exception as e:
                    logger.warning(f"Failed to fetch regressors for {var_name}: {e}")

            result = await select_best_model(
                var_name,
                historical_data=historical_data,
                external_regressors=external_regressors if external_regressors else None,
                force_refresh=force_refresh,
            )
            print(
                f"  -> Best: {result.best_model} | MAPE: {result.best_mape:.2%} | MASE: {result.best_mase:.2f}"
            )

            cache_model_selection(result)
            return var_name, result
        except Exception as e:
            logger.error(f"Error processing {var_name}: {e}")
            errors.append(f"{var_name}: {e}")
            return var_name, None


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
    variables = variables if variables is not None else ALL_VARIABLES

    # Early return for empty list
    if not variables:
        return {}

    results: dict[str, ModelSelectionResult] = {}
    errors: list[str] = []
    semaphore = asyncio.Semaphore(workers)

    tasks = [
        _process_single_variable(var, i + 1, len(variables), force_refresh, errors, semaphore)
        for i, var in enumerate(variables)
    ]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for item in completed:
        if isinstance(item, BaseException):
            logger.error(f"Task error: {item}")
            errors.append(str(item))
        elif item is not None:
            var_name, result = item
            if result is not None:
                results[var_name] = result

    runtime_minutes = (time.time() - start_time) / 60
    await generate_reports(results, output_dir, runtime_minutes)
    print_summary(results, errors, variables)

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
        # Fetch historical data for variable
        historical_data = await fetch_historical_data(variable, min_points=12)

        if historical_data is None or len(historical_data) < 12:
            print(f"Error: Insufficient data for {variable} (need 12+ points)")
            return None

        print(f"Loaded {len(historical_data)} data points")

        # Fetch regressors for this variable
        regressor_names = get_default_regressors(variable)
        external_regressors: dict[str, pd.Series] = {}
        if regressor_names:
            try:
                external_regressors = await fetch_regressors_with_date_range(
                    metric=variable,
                    historical_data_dates=list(historical_data.index),
                    periods_ahead=3,  # Default forecast horizon
                    regressor_names=regressor_names,
                )
                if external_regressors:
                    print(
                        f"Fetched {len(external_regressors)} regressors: {list(external_regressors.keys())}"
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch regressors for {variable}: {e}")

        result = await select_best_model(
            variable,
            historical_data=historical_data,
            external_regressors=external_regressors if external_regressors else None,
            force_refresh=force_refresh,
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
            cache_model_selection(result)
            print("\nResult cached to PostgreSQL.")
        else:
            print("\n[DRY RUN] Result not cached.")

        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        return None
