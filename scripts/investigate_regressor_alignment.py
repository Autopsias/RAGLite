#!/usr/bin/env python3
"""Investigate regressor data alignment issues."""

import asyncio
import os
import sys

# Set production environment BEFORE any raglite imports
os.environ["APP_ENV"] = "production"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "raglite"
os.environ["POSTGRES_USER"] = "raglite"
os.environ["POSTGRES_PASSWORD"] = "raglite"

sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import warnings

warnings.filterwarnings("ignore")


async def investigate_alignment():
    """Investigate data alignment between targets and regressors."""
    from raglite.forecasting.model_selection_job import fetch_historical_data
    from raglite.forecasting.regressor_config import get_default_regressors
    from raglite.forecasting.regressor_fetch import fetch_regressors_with_date_range

    # Variables to investigate
    variables = ["ebitda", "ttf_gas_price", "euribor_3m", "api2_coal"]

    for var in variables:
        print(f"\n{'=' * 70}")
        print(f"INVESTIGATING: {var}")
        print(f"{'=' * 70}")

        # Fetch target data
        data = await fetch_historical_data(var, min_points=12)
        if data is None:
            print(f"  ERROR: Could not fetch {var} data")
            continue

        print("Target data:")
        print(f"  Points: {len(data)}")
        print(f"  Date range: {data.index.min()} to {data.index.max()}")
        print(f"  Values: min={data.min():.4f}, max={data.max():.4f}")

        # Check for problematic values
        near_zero = (abs(data) < 1.0).sum()
        negative = (data < 0).sum()
        if near_zero > 0 or negative > 0:
            print(f"  ⚠️  Near-zero (|x|<1): {near_zero}, Negative: {negative}")

        # Fetch regressors
        regressor_names = get_default_regressors(var)
        if not regressor_names:
            print("  No regressors configured")
            continue

        print(f"\nRegressors configured: {regressor_names}")

        regressors = await fetch_regressors_with_date_range(
            metric=var,
            historical_data_dates=list(data.index),
            periods_ahead=3,
            regressor_names=regressor_names,
        )

        print("\nRegressor alignment analysis:")
        for reg_name, reg_series in regressors.items():
            target_dates = set(data.index)
            reg_dates = set(reg_series.index)
            overlap = len(target_dates & reg_dates)
            overlap_pct = overlap / len(data) * 100

            # Find regressor date range
            reg_start, reg_end = reg_series.index.min(), reg_series.index.max()

            status = "✅" if overlap_pct >= 80 else "⚠️" if overlap_pct >= 50 else "❌"
            print(f"\n  {status} {reg_name}:")
            print(f"     Regressor range: {reg_start} to {reg_end} ({len(reg_series)} points)")
            print(f"     Overlap: {overlap}/{len(data)} ({overlap_pct:.1f}%)")

            if overlap_pct < 80:
                # Find which target dates are missing from regressor
                missing_in_reg = target_dates - reg_dates
                if missing_in_reg:
                    missing_sorted = sorted(missing_in_reg)
                    print(
                        f"     Missing dates: {missing_sorted[0]} to {missing_sorted[-1]} ({len(missing_in_reg)} gaps)"
                    )


async def main():
    """Run investigation."""
    await investigate_alignment()

    # Also check the poor performers as standalone targets
    print(f"\n\n{'=' * 70}")
    print("POOR PERFORMERS - Root Cause Analysis")
    print(f"{'=' * 70}")

    from raglite.forecasting.model_selection_job import fetch_historical_data

    poor_performers = [
        ("ttf_gas_price", "Extreme price volatility (2022 energy crisis)"),
        ("euribor_3m", "Regime change (0% to 4% in 18 months)"),
        ("api2_coal", "Supply chain disruptions + energy crisis"),
    ]

    for var, expected_issue in poor_performers:
        data = await fetch_historical_data(var, min_points=12)
        if data is None:
            continue

        print(f"\n{var}:")
        print(f"  Expected issue: {expected_issue}")
        print(f"  Data points: {len(data)}")

        # Calculate volatility metrics
        if len(data) > 2:
            pct_change = data.pct_change().dropna()
            volatility = pct_change.std() * 100
            max_spike = pct_change.max() * 100
            max_drop = pct_change.min() * 100

            print(f"  Monthly volatility (std): {volatility:.1f}%")
            print(f"  Max monthly spike: {max_spike:.1f}%")
            print(f"  Max monthly drop: {max_drop:.1f}%")

            # Check for regime changes (large shifts in mean)
            if len(data) >= 24:
                first_half = data[: len(data) // 2].mean()
                second_half = data[len(data) // 2 :].mean()
                shift = (second_half - first_half) / first_half * 100 if first_half != 0 else 0
                print(f"  Mean shift (1st vs 2nd half): {shift:+.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
