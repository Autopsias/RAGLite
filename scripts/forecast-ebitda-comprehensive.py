#!/usr/bin/env python3
"""Comprehensive EBITDA forecasting across all variants with data quality analysis.

Forecasts EBITDA for:
- Global consolidated (EBITDA, EBITDA IFRS, EBITDA Group Structure)
- By country (Portugal, Tunisia, Angola, Lebanon, Brazil)
- By business line (Cement Unit, Ready-Mix, Aggregates)

Also investigates data quality issues (negative values, entity structure).
"""

import asyncio
import os

os.environ["APP_ENV"] = "production"

from raglite.forecasting.hybrid import generate_forecast
from raglite.forecasting.timeseries_extract import extract_timeseries_from_sql
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# EBITDA variants to forecast (discovered from database analysis)
EBITDA_VARIANTS = {
    "Global Consolidated": [
        ("EBITDA", "Base EBITDA metric"),
        ("EBITDA IFRS", "IFRS reporting standard"),
        ("EBITDA Group Structure", "Group consolidated view"),
    ],
    "By Country": [
        ("EBITDA Portugal", "Portugal operations"),
        ("EBITDA Tunisia", "Tunisia operations"),
        ("EBITDA Angola", "Angola operations"),
        ("EBITDA Lebanon", "Lebanon operations"),
        ("EBITDA Brazil", "Brazil operations"),
    ],
    "By Business Line": [
        ("Cement Unit", "Cement production unit"),
        ("Ready-Mix", "Ready-mix concrete unit"),
        ("Aggregates", "Aggregates production unit"),
    ],
}


async def investigate_ebitda_data_quality(metric: str = "EBITDA"):
    """Investigate data quality for EBITDA metric.

    Analyzes:
    - Sample raw rows to understand data structure
    - Entity column values
    - Value distributions (positive vs negative)
    - Period coverage
    """
    print(f"\n{'=' * 80}")
    print(f"DATA QUALITY INVESTIGATION: {metric}")
    print(f"{'=' * 80}\n")

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Query 1: Sample raw rows to understand structure
    query_sample = """
        SELECT
            metric,
            entity,
            period,
            value,
            fiscal_year,
            document_id
        FROM financial_tables
        WHERE metric = %s
        ORDER BY period DESC, document_id DESC
        LIMIT 20
    """

    cursor.execute(query_sample, (metric,))
    sample_rows = cursor.fetchall()

    print(f'📊 Sample Raw Rows for "{metric}":')
    print(
        f"{'Metric':<20} | {'Entity':<30} | {'Period':<10} | {'Value':>15} | {'FY':>4} | {'Doc ID'}"
    )
    print("-" * 120)

    for row in sample_rows:
        metric_name, entity, period, value, fy, doc_id = row
        period_str = period if period else "NULL"
        fy_str = str(fy) if fy else "NULL"
        value_str = f"{value:>15,.0f}" if value is not None else f"{'NULL':>15}"
        print(
            f"{metric_name:<20} | {entity or 'NULL':<30} | {period_str:<10} | {value_str} | {fy_str:>4} | {doc_id}"
        )

    # Query 2: Entity analysis
    query_entities = """
        SELECT
            entity,
            COUNT(*) as row_count,
            COUNT(DISTINCT period) as period_count,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value
        FROM financial_tables
        WHERE metric = %s
        GROUP BY entity
        ORDER BY COUNT(*) DESC
        LIMIT 15
    """

    cursor.execute(query_entities, (metric,))
    entity_analysis = cursor.fetchall()

    print(f'\n📋 Entity Breakdown for "{metric}":')
    print(
        f"{'Entity':<40} | {'Rows':>6} | {'Periods':>7} | {'Avg Value':>15} | {'Min':>15} | {'Max':>15}"
    )
    print("-" * 120)

    for row in entity_analysis:
        entity, row_count, period_count, avg_val, min_val, max_val = row
        print(
            f"{entity or 'NULL':<40} | {row_count:>6} | {period_count:>7} | {avg_val:>15,.0f} | {min_val:>15,.0f} | {max_val:>15,.0f}"
        )

    # Query 3: Value distribution analysis
    query_distribution = """
        SELECT
            CASE
                WHEN value < 0 THEN 'Negative'
                WHEN value = 0 THEN 'Zero'
                WHEN value > 0 THEN 'Positive'
            END as value_category,
            COUNT(*) as row_count,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value
        FROM financial_tables
        WHERE metric = %s
        GROUP BY
            CASE
                WHEN value < 0 THEN 'Negative'
                WHEN value = 0 THEN 'Zero'
                WHEN value > 0 THEN 'Positive'
            END
        ORDER BY value_category
    """

    cursor.execute(query_distribution, (metric,))
    distribution = cursor.fetchall()

    print(f'\n📈 Value Distribution for "{metric}":')
    print(f"{'Category':<15} | {'Row Count':>10} | {'Avg Value':>15} | {'Min':>15} | {'Max':>15}")
    print("-" * 80)

    for row in distribution:
        category, row_count, avg_val, min_val, max_val = row
        cat_str = category if category else "NULL"
        avg_str = f"{avg_val:>15,.0f}" if avg_val is not None else f"{'NULL':>15}"
        min_str = f"{min_val:>15,.0f}" if min_val is not None else f"{'NULL':>15}"
        max_str = f"{max_val:>15,.0f}" if max_val is not None else f"{'NULL':>15}"
        print(f"{cat_str:<15} | {row_count:>10} | {avg_str} | {min_str} | {max_str}")

    cursor.close()

    # Interpretation
    print("\n💡 Data Quality Insights:")
    print(f"{'=' * 80}")

    if any(row[0] == "Negative" for row in distribution):
        print("⚠️  NEGATIVE VALUES DETECTED")
        print("   This suggests the metric may be:")
        print("   - Delta/variance data (change vs budget or prior period)")
        print("   - Business unit-specific (not consolidated)")
        print("   - Mixed entities with different calculation methodologies")
        print()

    if len(entity_analysis) > 5:
        print(f"⚠️  MULTIPLE ENTITIES ({len(entity_analysis)} distinct)")
        print("   Different entities may represent:")
        print("   - Geographic segments (countries, regions)")
        print("   - Business units (cement, ready-mix, aggregates)")
        print("   - Organizational levels (group, division, subsidiary)")
        print()

    print()


async def forecast_ebitda_variant(metric: str, description: str, periods_ahead: int = 12):
    """Forecast a single EBITDA variant.

    Args:
        metric: Exact metric name (e.g., "EBITDA Portugal")
        description: Human-readable description
        periods_ahead: Number of periods to forecast

    Returns:
        Forecast result or None if insufficient data
    """
    try:
        # Extract historical data
        ts_data = await extract_timeseries_from_sql(metric=metric, min_points=8)

        # Generate forecast
        result = await generate_forecast(
            metric=metric,
            historical_data=ts_data,
            periods_ahead=periods_ahead,
        )

        return result

    except Exception as e:
        logger.warning(f"Failed to forecast {metric}: {e}")
        return None


async def forecast_all_ebitda_variants(periods_ahead: int = 12):
    """Forecast all EBITDA variants and display comparison.

    Args:
        periods_ahead: Number of periods to forecast ahead (default 12 for full year)
    """
    print(f"\n{'=' * 80}")
    print("COMPREHENSIVE EBITDA FORECASTING")
    print(f"{'=' * 80}")
    print(f"Forecast horizon: {periods_ahead} periods ahead")
    print("Target: 2026 full-year projections")
    print(f"{'=' * 80}\n")

    all_results = {}

    for category, variants in EBITDA_VARIANTS.items():
        print(f"\n{'─' * 80}")
        print(f"📊 {category}")
        print(f"{'─' * 80}\n")

        category_results = {}

        for metric, description in variants:
            print(f"🔮 Forecasting: {metric} ({description})")

            result = await forecast_ebitda_variant(metric, description, periods_ahead)

            if result:
                # Calculate summary stats
                forecast_values = [p.value for p in result.forecast]
                total = sum(forecast_values)
                avg = total / len(forecast_values)
                min_val = min(forecast_values)
                max_val = max(forecast_values)

                print("   ✅ Success!")
                print(f"      Historical: {len(result.historical_data)} data points")
                print(f"      2026 Total: €{int(total):,}K")
                print(f"      Monthly Avg: €{int(avg):,}K")
                print(f"      Range: €{int(min_val):,}K to €{int(max_val):,}K")
                print()

                category_results[metric] = {
                    "result": result,
                    "total": total,
                    "avg": avg,
                    "description": description,
                }
            else:
                print("   ❌ Insufficient data or error")
                print()

        all_results[category] = category_results

    # Summary comparison table
    print(f"\n{'=' * 80}")
    print("2026 EBITDA FORECAST SUMMARY")
    print(f"{'=' * 80}\n")

    print(f"{'Metric':<35} | {'Category':<20} | {'2026 Total (€K)':>20} | {'Monthly Avg':>15}")
    print("-" * 100)

    for category, results in all_results.items():
        for metric, data in results.items():
            total = data["total"]
            avg = data["avg"]
            print(f"{metric:<35} | {category:<20} | {int(total):>20,} | {int(avg):>15,}")

    print()

    return all_results


async def show_detailed_forecast(metric: str, result, periods_ahead: int = 12):
    """Show detailed monthly forecast breakdown for a metric.

    Args:
        metric: Metric name
        result: ForecastResult object
        periods_ahead: Number of periods shown
    """
    print(f"\n{'=' * 80}")
    print(f"DETAILED FORECAST: {metric}")
    print(f"{'=' * 80}\n")

    # Historical summary
    hist_values = [p.value for p in result.historical_data]
    print(f"📈 Historical Data ({len(result.historical_data)} periods):")
    print(
        f"   Range: {result.historical_data[0].date.strftime('%b-%y')} to {result.historical_data[-1].date.strftime('%b-%y')}"
    )
    print(
        f"   Latest: €{int(hist_values[-1]):,}K ({result.historical_data[-1].date.strftime('%b-%y')})"
    )
    print(f"   Average: €{int(sum(hist_values) / len(hist_values)):,}K")
    print()

    # Forecast table
    print("🔮 2026 Monthly Projections:")
    print(f"{'Period':<12} | {'Forecast (€K)':>15}")
    print("-" * 40)

    for pred in result.forecast[:periods_ahead]:
        period = pred.date.strftime("%b %Y")
        forecast_val = int(pred.value)
        print(f"{period:<12} | {forecast_val:>15,}")

    print()

    # Summary statistics
    forecast_values = [int(p.value) for p in result.forecast[:periods_ahead]]
    total = sum(forecast_values)
    avg = total // len(forecast_values)
    min_val = min(forecast_values)
    max_val = max(forecast_values)

    print("📊 2026 Summary:")
    print(f"   Total EBITDA: €{total:,}K")
    print(f"   Monthly Average: €{avg:,}K")
    print(f"   Minimum: €{min_val:,}K")
    print(f"   Maximum: €{max_val:,}K")
    print(f"   Range: €{max_val - min_val:,}K")
    print()

    # AI reasoning
    print(f"{'=' * 80}")
    print("AI FORECAST REASONING")
    print(f"{'=' * 80}")
    print()
    print(result.confidence_reasoning)
    print()


async def main():
    """Main execution."""
    print("\n" + "=" * 80)
    print("🏢 SECIL EBITDA COMPREHENSIVE FORECASTING & DATA QUALITY ANALYSIS")
    print("=" * 80)
    print()
    print("⚠️  WARNING: Using PRODUCTION database (Qdrant:6333, PostgreSQL:5432)")
    print()

    # Task 3: Investigate base EBITDA data quality
    await investigate_ebitda_data_quality(metric="EBITDA")

    # Task 2: Forecast all EBITDA variants
    all_results = await forecast_all_ebitda_variants(periods_ahead=12)

    # Show detailed forecast for global consolidated EBITDA
    if "Global Consolidated" in all_results:
        if "EBITDA" in all_results["Global Consolidated"]:
            result_data = all_results["Global Consolidated"]["EBITDA"]
            await show_detailed_forecast("EBITDA", result_data["result"], periods_ahead=12)

    print(f"\n{'=' * 80}")
    print("✅ COMPREHENSIVE EBITDA ANALYSIS COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(main())
