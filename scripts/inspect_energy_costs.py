#!/usr/bin/env python3
"""Inspect raw data for Electricity Cost and Thermal Energy Cost.

Story 6.23: Investigate extreme MAPE values (650% and 276%) for energy cost metrics.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.forecasting.timeseries_extract import extract_timeseries_from_sql
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def inspect_energy_costs():
    """Extract and inspect Electricity Cost and Thermal Energy Cost data."""

    print("\n" + "=" * 80)
    print("ELECTRICITY COST DATA INSPECTION")
    print("=" * 80)

    # Metric names from validation config
    elec_aliases = ["Electrical Energy", "electrical energy", "electricity"]
    thermal_aliases = ["Thermal Energy", "thermal energy", "fuel_cost"]

    # Try each alias for Electricity Cost
    elec_data = None
    for alias in elec_aliases:
        try:
            print(f"\nTrying alias: '{alias}'")
            elec_data = await extract_timeseries_from_sql(alias, min_points=6)
            if elec_data and len(elec_data.points) >= 6:
                print(f"✓ Found data with alias: '{alias}'")
                break
        except Exception as e:
            print(f"✗ Failed with alias '{alias}': {e}")

    if elec_data:
        print(f"\nElectricity Cost data points ({len(elec_data.points)} total):")
        print(f"{'Date':<12} {'Value':>15} {'Label'}")
        print("-" * 80)
        for p in sorted(elec_data.points, key=lambda x: x.date):
            print(f"{p.date.strftime('%Y-%m-%d'):<12} {p.value:>15.2f} {p.label or ''}")

        # Calculate statistics
        values = [p.value for p in elec_data.points if p.value is not None]
        if values:
            import statistics

            print("\nStatistics:")
            print(f"  Min:    {min(values):,.2f}")
            print(f"  Max:    {max(values):,.2f}")
            print(f"  Mean:   {statistics.mean(values):,.2f}")
            print(f"  Median: {statistics.median(values):,.2f}")
            print(f"  StdDev: {statistics.stdev(values) if len(values) > 1 else 0:,.2f}")

            # Check for outliers (>3 std from mean)
            mean = statistics.mean(values)
            std = statistics.stdev(values) if len(values) > 1 else 0
            outliers = [v for v in values if abs(v - mean) > 3 * std]
            if outliers:
                print(f"\n  ⚠️ Outliers (>3σ): {len(outliers)} values")
                print(f"     {outliers}")
    else:
        print("\n✗ No Electricity Cost data found with any alias")

    print("\n" + "=" * 80)
    print("THERMAL ENERGY COST DATA INSPECTION")
    print("=" * 80)

    # Try each alias for Thermal Energy Cost
    thermal_data = None
    for alias in thermal_aliases:
        try:
            print(f"\nTrying alias: '{alias}'")
            thermal_data = await extract_timeseries_from_sql(alias, min_points=6)
            if thermal_data and len(thermal_data.points) >= 6:
                print(f"✓ Found data with alias: '{alias}'")
                break
        except Exception as e:
            print(f"✗ Failed with alias '{alias}': {e}")

    if thermal_data:
        print(f"\nThermal Energy Cost data points ({len(thermal_data.points)} total):")
        print(f"{'Date':<12} {'Value':>15} {'Label'}")
        print("-" * 80)
        for p in sorted(thermal_data.points, key=lambda x: x.date):
            print(f"{p.date.strftime('%Y-%m-%d'):<12} {p.value:>15.2f} {p.label or ''}")

        # Calculate statistics
        values = [p.value for p in thermal_data.points if p.value is not None]
        if values:
            import statistics

            print("\nStatistics:")
            print(f"  Min:    {min(values):,.2f}")
            print(f"  Max:    {max(values):,.2f}")
            print(f"  Mean:   {statistics.mean(values):,.2f}")
            print(f"  Median: {statistics.median(values):,.2f}")
            print(f"  StdDev: {statistics.stdev(values) if len(values) > 1 else 0:,.2f}")

            # Check for outliers (>3 std from mean)
            mean = statistics.mean(values)
            std = statistics.stdev(values) if len(values) > 1 else 0
            outliers = [v for v in values if abs(v - mean) > 3 * std]
            if outliers:
                print(f"\n  ⚠️ Outliers (>3σ): {len(outliers)} values")
                print(f"     {outliers}")
    else:
        print("\n✗ No Thermal Energy Cost data found with any alias")

    print("\n" + "=" * 80)
    print("VALIDATION CONFIG CHECK")
    print("=" * 80)

    # Check validation script config
    from scripts.validate_forecasting_unified import CEMENT_FORECAST_VARIABLES

    elec_config = CEMENT_FORECAST_VARIABLES.get("electricity_cost")
    thermal_config = CEMENT_FORECAST_VARIABLES.get("thermal_cost")

    print("\nElectricity Cost config:")
    print(f"  Aliases: {elec_config.db_metric_aliases if elec_config else 'NOT FOUND'}")
    print(f"  Target MAPE: {elec_config.target_mape if elec_config else 'NOT FOUND'}%")

    print("\nThermal Energy Cost config:")
    print(f"  Aliases: {thermal_config.db_metric_aliases if thermal_config else 'NOT FOUND'}")
    print(f"  Target MAPE: {thermal_config.target_mape if thermal_config else 'NOT FOUND'}%")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(inspect_energy_costs())
