#!/usr/bin/env python3
"""Forecast EBITDA for 2026."""

import asyncio
import os

os.environ["APP_ENV"] = "production"

from raglite.forecasting.hybrid import generate_forecast
from raglite.forecasting.timeseries_extract import extract_timeseries_from_sql


async def forecast_ebitda():
    print("\n" + "=" * 80)
    print("📊 EBITDA FORECAST FOR 2026")
    print("=" * 80)
    print()

    # Extract historical data
    print("🔍 Extracting historical EBITDA data...")
    ts_data = await extract_timeseries_from_sql(metric="EBITDA IFRS", min_points=8)

    print(f"✅ Historical data: {len(ts_data.points)} months")
    print(
        f"   Date range: {ts_data.points[0].date.strftime('%B %Y')} to {ts_data.points[-1].date.strftime('%B %Y')}"
    )
    print(
        f"   Latest value: €{int(ts_data.points[-1].value):,}K ({ts_data.points[-1].date.strftime('%b-%y')})"
    )
    print()

    # Generate 12-month forecast
    print("🔮 Generating 12-month forecast...")
    result = await generate_forecast(
        metric="EBITDA IFRS", historical_data=ts_data, periods_ahead=12
    )

    print("✅ Forecast complete!")
    print()
    print("=" * 80)
    print("2026 EBITDA PROJECTIONS")
    print("=" * 80)
    print()

    # Display forecast table
    print(f"{'Period':<12} | {'Forecast (€K)':>15} | {'Lower Bound':>15} | {'Upper Bound':>15}")
    print("-" * 80)

    for pred in result.forecast:
        period = pred.date.strftime("%b %Y")
        forecast_val = int(pred.value)
        lower = (
            int(pred.lower_bound)
            if hasattr(pred, "lower_bound")
            else forecast_val - int(abs(forecast_val * 0.15))
        )
        upper = (
            int(pred.upper_bound)
            if hasattr(pred, "upper_bound")
            else forecast_val + int(abs(forecast_val * 0.15))
        )

        print(f"{period:<12} | {forecast_val:>15,} | {lower:>15,} | {upper:>15,}")

    print()
    print("=" * 80)
    print("EBITDA SUMMARY - 2026")
    print("=" * 80)
    print()

    # Calculate summary statistics
    forecast_values = [int(p.value) for p in result.forecast]
    avg_2026 = sum(forecast_values) / len(forecast_values)
    min_2026 = min(forecast_values)
    max_2026 = max(forecast_values)
    total_2026 = sum(forecast_values)

    print(f"Total EBITDA (2026):     €{total_2026:,}K")
    print(f"Monthly Average:         €{int(avg_2026):,}K")
    print(f"Minimum (Projected):     €{min_2026:,}K")
    print(f"Maximum (Projected):     €{max_2026:,}K")
    print(f"Range:                   €{max_2026 - min_2026:,}K")
    print()

    # Year-over-year comparison
    latest_historical = int(ts_data.points[-1].value)
    avg_forecast = int(avg_2026)
    if latest_historical != 0:
        yoy_change = ((avg_forecast - latest_historical) / abs(latest_historical)) * 100
    else:
        yoy_change = 0

    print(f"Latest Historical (Oct-25): €{latest_historical:,}K")
    print(f"Avg 2026 Forecast:          €{avg_forecast:,}K")
    print(f"Change:                     {yoy_change:+.1f}%")
    print()

    # Show AI reasoning
    print("=" * 80)
    print("AI FORECAST REASONING")
    print("=" * 80)
    print()
    print(result.confidence_reasoning)
    print()

    print("=" * 80)
    print("FORECAST BASIS & ACCURACY")
    print("=" * 80)
    print()
    print(f"Basis: {result.basis}")
    print(f"Accuracy: {result.accuracy_estimate}")
    print()


if __name__ == "__main__":
    asyncio.run(forecast_ebitda())
