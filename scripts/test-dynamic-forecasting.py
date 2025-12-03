#!/usr/bin/env python3
"""Test Dynamic Metric Forecasting with Diverse Variables.

Tests forecasting functionality with non-traditional financial metrics
to validate Story 5.0.4 dynamic metric support.

Usage:
    uv run python scripts/test-dynamic-forecasting.py [--production]
"""

import argparse
import asyncio
import os

from raglite.forecasting.hybrid import generate_forecast
from raglite.forecasting.metrics import list_available_metrics
from raglite.forecasting.timeseries_extract import (
    MetricValidationError,
    extract_timeseries_from_sql,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# Test metrics covering diverse financial areas (using exact database names)
TEST_METRICS = {
    # Traditional financial metrics
    "EBITDA IFRS": "EBITDA (Earnings Before Interest, Taxes, Depreciation, Amortization)",
    "CAPEX": "Capital Expenditures",
    "Turnover": "Revenue/Sales",
    # Operational cost metrics
    "Electrical Energy": "Electricity Costs",
    "Thermal Energy": "Thermal Energy Costs (includes pet coke, coal, etc.)",
    "Employee": "Employee/Salary Costs",
    "Raw Materials": "Raw Material Costs",
    # Balance sheet metrics
    "Financial net debt - Closing Balance": "Net Debt",
    "Trade Working Capital": "Working Capital",
    "Inventories": "Inventory Levels",
    "Accounts receivable": "Accounts Receivable",
    "Accounts payable": "Accounts Payable",
    # Cash flow metrics
    "CF from Operating Activities": "Operating Cash Flow",
    "Net Cash Flow": "Net Cash Flow",
    # Operational metrics
    "Sales Volumes": "Sales Volume",
    "Sales Price": "Sales Price",
    "Margin": "Profit Margins",
    # Additional diverse metrics
    "Variable Cost": "Variable Manufacturing Costs",
    "Fixed Costs": "Fixed Operating Costs",
    "Other costs/income": "Other Costs and Income",
}


class ForecastTestResult:
    """Result of forecasting test for a single metric."""

    def __init__(
        self,
        metric_name: str,
        description: str,
        success: bool,
        data_points: int | None = None,
        forecast_periods: int | None = None,
        error: str | None = None,
    ):
        self.metric_name = metric_name
        self.description = description
        self.success = success
        self.data_points = data_points
        self.forecast_periods = forecast_periods
        self.error = error


async def test_metric_forecast(
    metric_name: str,
    description: str,
    periods: int = 3,
) -> ForecastTestResult:
    """Test forecasting for a single metric.

    Args:
        metric_name: Metric to forecast
        description: Human-readable description
        periods: Number of periods to forecast ahead

    Returns:
        ForecastTestResult with success/failure status
    """
    try:
        # Extract time-series data
        logger.info(f"Testing metric: {metric_name}")
        ts_data = await extract_timeseries_from_sql(metric=metric_name, min_points=8)

        # Generate forecast
        forecast = await generate_forecast(
            metric=metric_name,
            historical_data=ts_data,
            periods_ahead=periods,
        )

        return ForecastTestResult(
            metric_name=metric_name,
            description=description,
            success=True,
            data_points=len(ts_data.points),
            forecast_periods=len(forecast.predictions),
        )

    except MetricValidationError as e:
        # Metric exists but insufficient data
        return ForecastTestResult(
            metric_name=metric_name,
            description=description,
            success=False,
            data_points=e.data_points_found,
            error=f"Insufficient data: {e.data_points_found} points (need {e.minimum_required})",
        )

    except Exception as e:
        # Other errors (metric not found, SQL errors, etc.)
        return ForecastTestResult(
            metric_name=metric_name,
            description=description,
            success=False,
            error=str(e),
        )


async def run_forecast_tests(periods: int = 3) -> list[ForecastTestResult]:
    """Run forecasting tests on all test metrics.

    Args:
        periods: Number of periods to forecast ahead

    Returns:
        List of ForecastTestResult objects
    """
    results = []

    print("\n" + "=" * 80)
    print("DYNAMIC METRIC FORECASTING TEST SUITE")
    print("=" * 80)
    print(f"Testing {len(TEST_METRICS)} diverse financial metrics")
    print(f"Forecast horizon: {periods} periods ahead")
    print("=" * 80 + "\n")

    for metric_name, description in TEST_METRICS.items():
        result = await test_metric_forecast(metric_name, description, periods)
        results.append(result)

    return results


def print_results(results: list[ForecastTestResult]) -> None:
    """Print formatted test results.

    Args:
        results: List of ForecastTestResult objects
    """
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print("\n" + "=" * 80)
    print(f"✅ SUCCESSFUL FORECASTS: {len(successful)}/{len(results)}")
    print("=" * 80)

    if successful:
        print(f"\n{'Metric':<45} | {'Data Points':>12} | {'Forecast Periods':>16}")
        print("-" * 80)
        for r in successful:
            print(f"{r.description:<45} | {r.data_points:>12} | {r.forecast_periods:>16}")

    if failed:
        print("\n" + "=" * 80)
        print(f"❌ FAILED FORECASTS: {len(failed)}/{len(results)}")
        print("=" * 80)
        print(f"\n{'Metric':<45} | {'Error':<30}")
        print("-" * 80)
        for r in failed:
            error_msg = r.error[:30] + "..." if len(r.error or "") > 30 else r.error
            print(f"{r.description:<45} | {error_msg:<30}")

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(
        f"Success Rate: {len(successful)}/{len(results)} ({100 * len(successful) / len(results):.1f}%)"
    )

    if successful:
        avg_data_points = sum(r.data_points for r in successful) / len(successful)
        print(f"Average Data Points (successful): {avg_data_points:.0f}")

    # Categorize results
    categories = {
        "Traditional Financial": ["EBITDA IFRS", "CAPEX", "Turnover"],
        "Operational Costs": [
            "Electrical Energy",
            "Thermal Energy",
            "Employee",
            "Raw Materials",
            "Variable Cost",
            "Fixed Costs",
            "Other costs/income",
        ],
        "Balance Sheet": [
            "Financial net debt - Closing Balance",
            "Trade Working Capital",
            "Inventories",
            "Accounts receivable",
            "Accounts payable",
        ],
        "Cash Flow": ["CF from Operating Activities", "Net Cash Flow"],
        "Operational Metrics": ["Sales Volumes", "Sales Price", "Margin"],
    }

    print("\n" + "=" * 80)
    print("BY CATEGORY")
    print("=" * 80)

    for category, metrics in categories.items():
        category_results = [r for r in results if r.metric_name in metrics]
        category_success = [r for r in category_results if r.success]
        print(f"\n{category}: {len(category_success)}/{len(category_results)} successful")
        for r in category_results:
            status = "✅" if r.success else "❌"
            print(f"  {status} {r.metric_name}")


async def discover_alternative_metrics() -> None:
    """Discover alternative metric names that might work.

    Helps identify variations in metric naming (e.g., "Employee" vs "Salary Costs").
    """
    print("\n" + "=" * 80)
    print("DISCOVERING ALTERNATIVE METRIC NAMES")
    print("=" * 80)

    metrics = await list_available_metrics(min_points=8, use_cache=False)

    # Search for cost-related metrics
    cost_keywords = [
        "cost",
        "expense",
        "employee",
        "salary",
        "energy",
        "electric",
        "thermal",
        "fuel",
        "coke",
        "coal",
        "material",
    ]

    print("\nCost-Related Metrics:")
    print("-" * 80)
    for m in metrics:
        if any(kw in m.name.lower() for kw in cost_keywords):
            print(f"  {m.name:<50} | {m.data_point_count:>6} points")

    # Search for debt/capital metrics
    capital_keywords = [
        "debt",
        "capital",
        "working",
        "cash",
        "inventory",
        "receivable",
        "payable",
    ]

    print("\nDebt/Capital Metrics:")
    print("-" * 80)
    for m in metrics:
        if any(kw in m.name.lower() for kw in capital_keywords):
            print(f"  {m.name:<50} | {m.data_point_count:>6} points")


async def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(description="Test dynamic metric forecasting")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Use production database (default: test database)",
    )
    parser.add_argument(
        "--periods",
        type=int,
        default=3,
        help="Number of periods to forecast ahead (default: 3)",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Also discover alternative metric names",
    )
    args = parser.parse_args()

    # Set environment
    if args.production:
        os.environ["APP_ENV"] = "production"
        print("\n⚠️  WARNING: Using PRODUCTION database (Qdrant:6333, PostgreSQL:5432)")
    else:
        os.environ["APP_ENV"] = "test"
        print("\n✅ Using TEST database (Qdrant:6335, PostgreSQL:5433)")

    # Run tests
    results = await run_forecast_tests(periods=args.periods)
    print_results(results)

    # Discover alternatives if requested
    if args.discover:
        await discover_alternative_metrics()

    # Exit with appropriate code
    failed_count = sum(1 for r in results if not r.success)
    if failed_count > 0:
        print(f"\n⚠️  {failed_count} metrics failed forecasting")
        return 1
    else:
        print("\n✅ All metrics forecasted successfully!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
