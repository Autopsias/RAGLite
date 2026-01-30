#!/usr/bin/env python3
"""Quick model selection test with date alignment fix."""

import asyncio
import logging
import os
import sys
import warnings

os.environ["APP_ENV"] = "production"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "raglite"
os.environ["POSTGRES_USER"] = "raglite"
os.environ["POSTGRES_PASSWORD"] = "raglite"

sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

warnings.filterwarnings("ignore")
logging.getLogger("lightgbm").setLevel(logging.ERROR)
logging.getLogger("catboost").setLevel(logging.ERROR)


async def run_quick_test():
    """Run quick model selection test on key variables."""
    from raglite.forecasting.model_selection import select_best_model
    from raglite.forecasting.model_selection_job import (
        fetch_historical_data,
    )
    from raglite.forecasting.regressor_config import get_default_regressors
    from raglite.forecasting.regressor_fetch import fetch_regressors_with_date_range

    # Test variables that should benefit from the fix
    test_vars = [
        "ttf_gas_price",  # Had 0% regressor overlap before
        "ebitda",  # Had poor diesel alignment
        "electricity_cost",  # Best performer
    ]

    print("=" * 70)
    print("QUICK MODEL SELECTION TEST WITH DATE ALIGNMENT FIX")
    print("=" * 70)

    for var in test_vars:
        print(f"\n{'=' * 70}")
        print(f"TESTING: {var}")
        print(f"{'=' * 70}")

        # Fetch data
        data = await fetch_historical_data(var, min_points=12)
        if data is None:
            print(f"  ERROR: Could not fetch {var} data")
            continue

        print(f"Data: {len(data)} points, {data.index.min().date()} to {data.index.max().date()}")

        # Fetch regressors
        regressor_names = get_default_regressors(var)
        if regressor_names:
            print(f"Regressors: {regressor_names}")
            regressors = await fetch_regressors_with_date_range(
                metric=var,
                historical_data_dates=list(data.index),
                periods_ahead=3,
                regressor_names=regressor_names,
            )
            print(f"Fetched: {list(regressors.keys())}")
        else:
            print("No regressors configured")
            regressors = {}

        # Run model selection
        print("\nRunning model selection...")
        result = await select_best_model(
            var,
            historical_data=data,
            external_regressors=regressors if regressors else None,
            force_refresh=True,
        )

        print("\nRESULT:")
        print(f"  Best Model: {result.best_model}")
        print(f"  MASE: {result.best_mase:.4f}")
        print(f"  MAPE: {result.best_mape:.2%}")
        print(f"  Uses Regressors: {result.best_with_regressors}")
        if result.best_regressor_set:
            print(f"  Regressor Set: {result.best_regressor_set}")

        # Show if regressor versions performed better
        if result.candidate_results:
            reg_results = {
                k: v
                for k, v in result.candidate_results.items()
                if "_True" in k and "error" not in v
            }
            if reg_results:
                best_reg = min(reg_results.items(), key=lambda x: x[1].get("mase", float("inf")))
                print(
                    f"\n  Best with regressors: {best_reg[0]} (MASE: {best_reg[1].get('mase', 'N/A'):.4f})"
                )

    print(f"\n\n{'=' * 70}")
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_quick_test())
