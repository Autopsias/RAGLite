#!/usr/bin/env python3
"""Test ebitda model selection with full candidate results."""

import asyncio
import logging
import os
import sys
import warnings

# Set production environment BEFORE any raglite imports
os.environ["APP_ENV"] = "production"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "raglite"
os.environ["POSTGRES_USER"] = "raglite"
os.environ["POSTGRES_PASSWORD"] = "raglite"

# Add project root to path
sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Suppress warnings
warnings.filterwarnings("ignore")
logging.getLogger("lightgbm").setLevel(logging.ERROR)
logging.getLogger("catboost").setLevel(logging.ERROR)


async def test_ebitda_models():
    """Show all candidate results for ebitda."""
    from raglite.forecasting.model_selection_job import fetch_historical_data

    from raglite.forecasting.model_selection import select_best_model
    from raglite.forecasting.regressor_config import get_default_regressors
    from raglite.forecasting.regressor_fetch import fetch_regressors_with_date_range

    print("Fetching ebitda historical data...")
    data = await fetch_historical_data("ebitda", min_points=12)

    if data is None:
        print("ERROR: Could not fetch ebitda data")
        return

    print(f"Data points: {len(data)}")
    print(f"Date range: {data.index.min()} to {data.index.max()}")
    print(f"Values: min={data.min():.2f}, max={data.max():.2f}, mean={data.mean():.2f}")

    # Check for near-zero values (problematic for MAPE)
    near_zero = (abs(data) < 1.0).sum()
    negative = (data < 0).sum()
    print(f"Near-zero values (|x| < 1): {near_zero}")
    print(f"Negative values: {negative}")

    # Fetch regressors
    regressor_names = get_default_regressors("ebitda")
    print(f"\nConfigured regressors for ebitda: {regressor_names}")

    regressors = await fetch_regressors_with_date_range(
        metric="ebitda",
        historical_data_dates=list(data.index),
        periods_ahead=3,
        regressor_names=regressor_names,
    )
    print(f"Fetched regressors: {list(regressors.keys())}")

    # Show regressor coverage
    for reg_name, reg_series in regressors.items():
        overlap = len(set(data.index) & set(reg_series.index))
        print(f"  {reg_name}: {len(reg_series)} points, {overlap} overlap with target")

    print("\nRunning model selection (this may take a few minutes)...")
    result = await select_best_model(
        "ebitda",
        historical_data=data,
        external_regressors=regressors,
        force_refresh=True,
    )

    print(f"\n{'=' * 70}")
    print("EBITDA MODEL SELECTION RESULTS")
    print(f"{'=' * 70}")
    print(f"Best Model: {result.best_model}")
    print(f"Best MAPE: {result.best_mape:.2%}")
    print(f"Best MASE: {result.best_mase:.2f}")
    print(f"Uses Regressors: {result.best_with_regressors}")
    if result.best_regressor_set:
        print(f"Regressors: {result.best_regressor_set}")

    print(f"\n{'=' * 70}")
    print("ALL CANDIDATE RESULTS (sorted by MASE)")
    print(f"{'=' * 70}")
    print(f"{'Model':<25} {'MAPE':>10} {'MASE':>8} {'Regressors':>12}")
    print("-" * 60)

    # Sort by MASE (primary metric for evaluation)
    sorted_results = sorted(
        result.candidate_results.items(), key=lambda x: x[1].get("mase", float("inf"))
    )

    for config_key, metrics in sorted_results:
        mape = metrics.get("mape", float("inf"))
        mase = metrics.get("mase", float("inf"))
        has_regs = metrics.get("with_regressors", False)

        if mape != float("inf"):
            print(f"{config_key:<25} {mape:>10.2%} {mase:>8.2f} {'Yes' if has_regs else 'No':>12}")
        else:
            error = str(metrics.get("error", "Unknown error"))[:30]
            print(f"{config_key:<25} {'ERROR':>10} {'--':>8} {error}")


if __name__ == "__main__":
    asyncio.run(test_ebitda_models())
