#!/usr/bin/env python3
"""Debug script to investigate Electricity and Thermal Energy cost extraction issues.

Story 6.23: Investigate 650% electricity MAPE and 276% thermal MAPE.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.forecasting.hybrid import generate_forecast
from raglite.forecasting.timeseries_extract import extract_timeseries_from_sql
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def debug_energy_cost(metric_name: str, display_name: str):
    """Debug single energy cost metric extraction and forecast."""
    print(f"\n{'=' * 80}")
    print(f"DEBUG: {display_name}")
    print(f"{'=' * 80}")

    # Extract timeseries data
    print(f"\n[1] Extracting {display_name} data...")
    try:
        data = await extract_timeseries_from_sql(
            metric=metric_name,
            min_points=6,
            aggregation="sum",  # Most metrics use sum
        )

        print(f"  ✓ Found {len(data.points)} data points")
        print(f"  Metric: {data.metric_name}")
        print(f"  Interval: {data.interval}")

        # Show all data points
        print(f"\n[2] Data points (all {len(data.points)} points):")
        print(f"  {'Date':<12} {'Value':>15} {'Notes':<30}")
        print(f"  {'-' * 60}")

        values = []
        for i, point in enumerate(data.points):
            values.append(point.value)
            # Flag outliers (>3 std devs from mean)
            notes = ""
            if i > 0:
                avg = sum(values) / len(values)
                import statistics

                if len(values) >= 3:
                    std = statistics.stdev(values)
                    z_score = abs((point.value - avg) / std) if std > 0 else 0
                    if z_score > 3:
                        notes = f"OUTLIER (z={z_score:.1f})"

            print(f"  {point.date.strftime('%Y-%m-%d'):<12} {point.value:>15.2f} {notes:<30}")

        # Statistics
        print("\n[3] Statistics:")
        print(f"  Min: {min(values):.2f}")
        print(f"  Max: {max(values):.2f}")
        print(f"  Mean: {sum(values) / len(values):.2f}")
        import statistics

        if len(values) >= 2:
            print(f"  Std Dev: {statistics.stdev(values):.2f}")
            print(
                f"  Coefficient of Variation: {(statistics.stdev(values) / (sum(values) / len(values)) * 100):.1f}%"
            )

        # Check for unit issues
        print("\n[4] Unit Check:")
        avg_value = sum(values) / len(values)
        if avg_value < 1:
            print(f"  ⚠️  WARNING: Average value {avg_value:.4f} is very low")
            print("      Expected range for EUR/ton: 10-200")
            print("      Possible unit issue: values in EUR/kWh instead of EUR/ton?")
        elif avg_value > 500:
            print(f"  ⚠️  WARNING: Average value {avg_value:.2f} is very high")
            print("      Expected range for EUR/ton: 10-200")
            print("      Possible unit issue: total cost instead of unit cost?")
        else:
            print(f"  ✓ Average value {avg_value:.2f} is in expected range (10-200 EUR/ton)")

        # Try forecasting
        print("\n[5] Generating forecast (holdout validation)...")
        holdout_size = 4
        train_points = data.points[:-holdout_size]
        test_points = data.points[-holdout_size:]

        from raglite.shared.models import TimeSeriesData

        train_data = TimeSeriesData(
            metric_name=data.metric_name,
            points=train_points,
            interval=data.interval,
            source_documents=data.source_documents,
        )

        result = await generate_forecast(
            metric=metric_name,
            historical_data=train_data,
            periods_ahead=holdout_size,
            external_regressors={},  # No regressors
            frequency="M",
        )

        if result and result.forecast:
            print(f"  ✓ Forecast generated ({len(result.forecast)} predictions)")
            print("\n  Forecast vs Actual:")
            print(f"  {'Date':<12} {'Actual':>12} {'Forecast':>12} {'Error %':>10}")
            print(f"  {'-' * 50}")

            errors = []
            for actual_point, forecast_point in zip(test_points, result.forecast, strict=False):
                error_pct = (
                    abs(forecast_point.value - actual_point.value) / actual_point.value * 100
                )
                errors.append(error_pct)
                print(
                    f"  {actual_point.date.strftime('%Y-%m-%d'):<12} "
                    f"{actual_point.value:>12.2f} "
                    f"{forecast_point.value:>12.2f} "
                    f"{error_pct:>9.1f}%"
                )

            mape = sum(errors) / len(errors)
            print(f"\n  MAPE: {mape:.2f}%")

            # Diagnose high MAPE
            if mape > 50:
                print(f"\n  ⚠️  CRITICAL: MAPE {mape:.1f}% is extremely high!")
                print("      Possible causes:")
                print("      1. Forecasts are flat but actuals have high variance")
                print("      2. Data has extreme outliers throwing off the model")
                print("      3. Unit mismatch (forecast in different units than actual)")
                print("      4. Insufficient training data for reliable forecast")
        else:
            print("  ✗ Forecast generation failed")

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Debug both energy cost metrics."""

    # Check Electricity Cost
    await debug_energy_cost(
        metric_name="Electrical Energy",
        display_name="Electricity Cost (EUR/ton)",
    )

    # Check Thermal Energy Cost
    await debug_energy_cost(
        metric_name="Thermal Energy",
        display_name="Thermal Energy Cost (EUR/ton)",
    )

    print(f"\n{'=' * 80}")
    print("DEBUG COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(main())
