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

import pandas as pd

from raglite.external_data.storage import cache_model_selection
from raglite.forecasting.model_selection import (
    CANDIDATE_MODELS,
    ModelSelectionResult,
    select_best_model,
)
from raglite.forecasting.regressor_config import get_default_regressors
from raglite.forecasting.regressor_fetch import fetch_regressors_with_date_range
from raglite.forecasting.timeseries import (
    extract_external_regressor_timeseries,
    extract_external_timeseries,
    extract_timeseries_from_sql,
)

logger = logging.getLogger(__name__)

# Variable configuration for data fetching
# Maps variable names to extraction method and DB aliases
VARIABLE_CONFIG: dict[str, dict] = {
    # Internal SECIL metrics (from financial_tables)
    "revenue": {
        "type": "internal",
        "aliases": ["Turnover+VAT", "Turnover", "turnover", "revenue"],
        "aggregation": "max",
    },
    "ebitda": {
        "type": "internal",
        "aliases": ["EBITDA", "ebitda", "Cement Unit Ebitda"],
        "aggregation": "sum",
    },
    "sales_volume": {
        "type": "internal",
        "aliases": ["Sales Volumes", "sales volumes", "Volume IM - kton"],
        "aggregation": "sum",
    },
    "thermal_cost": {
        "type": "internal",
        "aliases": ["Thermal Energy", "thermal energy", "fuel_cost"],
        "aggregation": "sum",
    },
    "variable_cost": {
        "type": "internal",
        "aliases": ["Variable Cost", "variable cost"],
        "aggregation": "sum",
    },
    "capacity_utilization": {
        "type": "internal",
        "aliases": ["Capacity Utilization", "capacity_utilization", "Ratio"],
        "aggregation": "max",
    },
    "avg_selling_price": {
        "type": "internal",
        "aliases": ["Sales Price IM", "avg_selling_price", "Average Selling Price"],
        "aggregation": "max",
    },
    # External database metrics (from external_data_points)
    "ttf_gas_price": {
        "type": "external_db",
        "metric_name": "ttf_gas_price",
        # HIGH UNCERTAINTY: 2022 energy crisis caused +211% mean shift, 99% CV
        "uncertainty": "high",
        "uncertainty_reason": "2022 energy crisis regime change",
    },
    "petcoke_price": {
        "type": "external_db",
        "metric_name": "petcoke_price",
    },
    "co2_eua_price": {
        "type": "external_db",
        "metric_name": "co2_eua_price",
    },
    # External API metrics (from regressor fetch)
    "electricity_cost": {
        "type": "external_api",
        "metric_name": "ren_electricity",
        # BEST PERFORMER: MASE 0.44 (56% better than naive)
        "quality": "excellent",
        "quality_note": "Best performing variable with MASE 0.44",
    },
    "diesel": {
        "type": "external_api",
        "metric_name": "diesel",
    },
    "api2_coal": {
        "type": "external_api",
        "metric_name": "api2_coal",
        # HIGH UNCERTAINTY: Correlated with energy crisis, 54% CV
        "uncertainty": "high",
        "uncertainty_reason": "2022 energy crisis and geopolitical disruptions",
    },
    # NOTE: eurostat_electricity removed - only 9 semi-annual data points (need 12+)
    # Use electricity_cost (ren_electricity) for Portuguese electricity prices instead
    "gdp_growth": {
        "type": "external_api",
        "metric_name": "gdp_growth",
    },
    "inflation": {
        "type": "external_api",
        "metric_name": "inflation",
    },
    "euribor_3m": {
        "type": "external_api",
        "metric_name": "euribor_3m",
        # HIGH UNCERTAINTY: ECB policy regime change from -0.5% to +4%
        "uncertainty": "high",
        "uncertainty_reason": "ECB rate policy regime change 2022-2023",
    },
    "construction_output": {
        "type": "external_api",
        "metric_name": "construction_output",
    },
    "building_permits": {
        "type": "external_api",
        "metric_name": "building_permits",
        # BEST PERFORMER: MASE 0.79 (21% better than naive)
        "quality": "excellent",
        "quality_note": "Second best performing variable with MASE 0.79",
    },
    "construction_confidence": {
        "type": "external_api",
        "metric_name": "construction_confidence",
    },
    "industrial_production": {
        "type": "external_api",
        "metric_name": "industrial_production",
    },
}

# All variables for batch processing
ALL_VARIABLES = list(VARIABLE_CONFIG.keys())

# Epic 7 Enhancement: Energy crisis regime detection
# Based on Exa research: Structural breaks in energy markets require regime-aware modeling
ENERGY_CRISIS_START = pd.Timestamp("2022-02-01")  # Russia-Ukraine conflict
ENERGY_CRISIS_PEAK = pd.Timestamp("2022-08-31")  # Peak TTF prices
ENERGY_CRISIS_END = pd.Timestamp("2023-06-30")  # Prices stabilized

# Variables that are affected by energy crisis regime
ENERGY_AFFECTED_VARIABLES = [
    "ttf_gas_price",
    "api2_coal",
    "co2_eua_price",
    "electricity_cost",
    "thermal_cost",
    "diesel",
    "euribor_3m",  # ECB rate changes in response to inflation
]


def add_regime_features(data: pd.DataFrame | pd.Series) -> pd.DataFrame:
    """Add regime indicator features for energy crisis period.

    Epic 7 Enhancement: Structural break handling based on Exa deep research.
    Energy markets experienced distinct regimes:
    - Pre-crisis: Stable prices (before Feb 2022)
    - Crisis: High volatility, extreme prices (Feb 2022 - Aug 2022)
    - Post-crisis: New normal with elevated but stable prices (after Jun 2023)

    Args:
        data: DataFrame or Series with DatetimeIndex

    Returns:
        DataFrame with added regime indicator columns
    """
    if isinstance(data, pd.Series):
        df = data.to_frame()
    else:
        df = data.copy()

    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        logger.warning("Data index is not DatetimeIndex, skipping regime features")
        return df

    # Add regime indicator columns
    df["regime_pre_crisis"] = (df.index < ENERGY_CRISIS_START).astype(int)
    df["regime_crisis"] = (
        (df.index >= ENERGY_CRISIS_START) & (df.index <= ENERGY_CRISIS_PEAK)
    ).astype(int)
    df["regime_post_peak"] = (
        (df.index > ENERGY_CRISIS_PEAK) & (df.index <= ENERGY_CRISIS_END)
    ).astype(int)
    df["regime_new_normal"] = (df.index > ENERGY_CRISIS_END).astype(int)

    return df


def is_energy_affected_variable(var_name: str) -> bool:
    """Check if a variable is affected by energy crisis regime changes.

    Args:
        var_name: Variable name to check

    Returns:
        True if the variable is in the energy-affected list
    """
    return var_name.lower() in [v.lower() for v in ENERGY_AFFECTED_VARIABLES]


async def fetch_historical_data(var_name: str, min_points: int = 12) -> pd.Series | None:
    """Fetch historical time series data for a variable.

    Args:
        var_name: Variable name from VARIABLE_CONFIG
        min_points: Minimum data points required

    Returns:
        pandas Series with DatetimeIndex, or None if insufficient data
    """
    config = VARIABLE_CONFIG.get(var_name)
    if not config:
        logger.warning(f"Unknown variable: {var_name}")
        return None

    try:
        var_type = config["type"]

        if var_type == "internal":
            # Extract from SECIL financial_tables
            for alias in config["aliases"]:
                try:
                    ts_data = await extract_timeseries_from_sql(
                        metric=alias,
                        min_points=min_points,
                        aggregation=config.get("aggregation", "sum"),
                    )
                    if ts_data and len(ts_data.points) >= min_points:
                        # Convert to pandas Series
                        dates = [p.date for p in ts_data.points]
                        values = [p.value for p in ts_data.points]
                        series = pd.Series(values, index=pd.DatetimeIndex(dates))
                        series.name = var_name
                        return series.sort_index()
                except Exception as e:
                    logger.debug(f"Alias {alias} failed: {e}")
                    continue
            logger.warning(f"No data found for internal variable {var_name}")
            return None

        elif var_type == "external_db":
            # Extract from external_data_points table
            ext_ts_data = await extract_external_timeseries(
                metric=config["metric_name"],
                min_points=min_points,
            )
            if ext_ts_data and len(ext_ts_data.points) >= min_points:
                dates = [p.date for p in ext_ts_data.points]
                values = [p.value for p in ext_ts_data.points]
                series = pd.Series(values, index=pd.DatetimeIndex(dates))
                series.name = var_name
                return series.sort_index()
            return None

        elif var_type == "external_api":
            # Extract via regressor fetch (API-backed)
            api_ts_data = await extract_external_regressor_timeseries(
                metric=config["metric_name"],
                min_points=min_points,
            )
            if api_ts_data and len(api_ts_data.points) >= min_points:
                dates = [p.date for p in api_ts_data.points]
                values = [p.value for p in api_ts_data.points]
                series = pd.Series(values, index=pd.DatetimeIndex(dates))
                series.name = var_name
                return series.sort_index()
            return None

        else:
            logger.warning(f"Unknown variable type: {var_type}")
            return None

    except Exception as e:
        logger.error(f"Error fetching data for {var_name}: {e}")
        return None


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
    if variables is None:
        variables = ALL_VARIABLES
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
                # Fetch historical data for variable
                historical_data = await fetch_historical_data(var_name, min_points=12)

                if historical_data is None or len(historical_data) < 12:
                    msg = f"Insufficient data for {var_name} (need 12+ points)"
                    logger.warning(msg)
                    errors.append(msg)
                    return var_name, None

                print(f"  -> Loaded {len(historical_data)} data points")

                # Fetch regressors for this variable
                regressor_names = get_default_regressors(var_name)
                external_regressors: dict[str, pd.Series] = {}
                if regressor_names:
                    try:
                        external_regressors = await fetch_regressors_with_date_range(
                            metric=var_name,
                            historical_data_dates=list(historical_data.index),
                            periods_ahead=3,  # Default forecast horizon
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
