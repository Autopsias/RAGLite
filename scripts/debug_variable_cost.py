#!/usr/bin/env python3
"""Debug script for variable_cost MAPE issue.

Compare forecasts with and without regressors to understand the degradation.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.forecasting.hybrid import generate_forecast
from raglite.forecasting.regressor_fetch import fetch_regressors_with_date_range
from raglite.forecasting.timeseries_extract import extract_timeseries_from_sql
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Compare variable_cost forecasts with/without regressors."""

    # Extract variable cost data
    logger.info("Extracting Variable Cost historical data...")
    historical_data = await extract_timeseries_from_sql(
        metric="Variable Cost",
        min_points=6,
        aggregation="sum",
    )

    if not historical_data:
        logger.error("No historical data found for Variable Cost")
        return

    logger.info(f"Historical data: {len(historical_data.points)} points")
    logger.info(
        f"Date range: {historical_data.points[0].date} to {historical_data.points[-1].date}"
    )

    # Show last 8 data points (training + test)
    print("\nHistorical Data (last 8 points):")
    for i, point in enumerate(historical_data.points[-8:]):
        print(f"  {i + 1}. {point.date}: {point.value:.2f}")

    # Split into train/test (holdout_size=4)
    holdout_size = 4
    train_points = historical_data.points[:-holdout_size]
    test_points = historical_data.points[-holdout_size:]

    print(f"\nTrain: {len(train_points)} points, Test: {len(test_points)} points")
    print("Test actuals:")
    for i, point in enumerate(test_points):
        print(f"  {i + 1}. {point.date}: {point.value:.2f}")

    # Create training data
    from raglite.shared.models import TimeSeriesData

    train_data = TimeSeriesData(
        metric_name=historical_data.metric_name,
        points=train_points,
        interval=historical_data.interval,
        source_documents=historical_data.source_documents,
    )

    # Test 1: Forecast WITHOUT regressors (baseline)
    logger.info("\n=== Forecast WITHOUT regressors ===")
    result_no_reg = await generate_forecast(
        metric="Variable Cost",
        historical_data=train_data,
        periods_ahead=holdout_size,
        external_regressors=None,
        frequency="M",
    )

    if result_no_reg and result_no_reg.forecast:
        print("\nForecast (no regressors):")
        for i, fp in enumerate(result_no_reg.forecast):
            actual = test_points[i].value if i < len(test_points) else "N/A"
            error = (
                abs(fp.value - test_points[i].value) / test_points[i].value * 100
                if i < len(test_points)
                else 0
            )
            print(
                f"  {i + 1}. {fp.date}: {fp.value:.2f} (actual: {actual if isinstance(actual, str) else f'{actual:.2f}'}, error: {error:.1f}%)"
            )

    # Test 2: Fetch regressors
    logger.info("\n=== Fetching regressors ===")
    historical_dates = [p.date for p in historical_data.points]
    regressors = await fetch_regressors_with_date_range(
        metric="Variable Cost",
        historical_data_dates=historical_dates,
        periods_ahead=holdout_size,
        regressor_names=["ttf_gas", "api2_coal", "industrial_production", "diesel"],
    )

    print(f"\nFetched {len(regressors)} regressors:")
    for name, series in regressors.items():
        print(
            f"  - {name}: {len(series)} points, range {series.index.min()} to {series.index.max()}"
        )

    # Test 3: Forecast WITH regressors
    logger.info("\n=== Forecast WITH regressors ===")
    result_with_reg = await generate_forecast(
        metric="Variable Cost",
        historical_data=train_data,
        periods_ahead=holdout_size,
        external_regressors=regressors,
        frequency="M",
    )

    if result_with_reg and result_with_reg.forecast:
        print("\nForecast (with regressors):")
        for i, fp in enumerate(result_with_reg.forecast):
            actual = test_points[i].value if i < len(test_points) else "N/A"
            error = (
                abs(fp.value - test_points[i].value) / test_points[i].value * 100
                if i < len(test_points)
                else 0
            )
            print(
                f"  {i + 1}. {fp.date}: {fp.value:.2f} (actual: {actual if isinstance(actual, str) else f'{actual:.2f}'}, error: {error:.1f}%)"
            )

    # Calculate MAPE for both
    from raglite.forecasting.validation_methods import calculate_holdout_mape

    mape_no_reg = (
        calculate_holdout_mape(
            historical_data.points, result_no_reg.forecast, holdout_size=holdout_size
        )
        if result_no_reg
        else None
    )
    mape_with_reg = (
        calculate_holdout_mape(
            historical_data.points, result_with_reg.forecast, holdout_size=holdout_size
        )
        if result_with_reg
        else None
    )

    print(f"\n{'=' * 60}")
    print(f"MAPE WITHOUT regressors: {mape_no_reg:.2f}%" if mape_no_reg else "N/A")
    print(f"MAPE WITH regressors: {mape_with_reg:.2f}%" if mape_with_reg else "N/A")
    print(f"{'=' * 60}")

    if mape_no_reg and mape_with_reg:
        if mape_with_reg > mape_no_reg:
            print(f"⚠️  WARNING: Regressors INCREASED MAPE by {mape_with_reg - mape_no_reg:.2f}%")
        else:
            print(f"✅ SUCCESS: Regressors DECREASED MAPE by {mape_no_reg - mape_with_reg:.2f}%")


if __name__ == "__main__":
    asyncio.run(main())
