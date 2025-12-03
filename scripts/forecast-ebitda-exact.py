#!/usr/bin/env python3
"""Forecast EBITDA using exact metric match to avoid aggregation issues."""

import asyncio
import os
from datetime import datetime

os.environ["APP_ENV"] = "production"

from raglite.forecasting.hybrid import generate_forecast
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

logger = get_logger(__name__)


async def extract_ebitda_exact_match(
    metric_exact: str = "EBITDA", min_points: int = 8
) -> TimeSeriesData:
    """Extract EBITDA with EXACT metric name matching (not wildcard).

    Avoids aggregation issues from LIKE '%ebitda%' matching multiple variants.
    """
    logger.info(f"Extracting {metric_exact} with exact match")

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Use exact match to avoid aggregating across EBITDA variants
    query = """
        WITH periods_with_year AS (
            SELECT
                period,
                COALESCE(
                    fiscal_year,
                    2000 + CAST(SUBSTRING(period FROM '[0-9]{2}$') AS INTEGER)
                ) as inferred_fiscal_year,
                document_id,
                value
            FROM financial_tables
            WHERE metric = %s  -- EXACT MATCH (not LIKE)
              AND period IS NOT NULL
              AND period ~ '^[A-Z][a-z]{2}-[0-9]{2}$'
              AND value IS NOT NULL
        ),
        latest_doc_per_period AS (
            SELECT
                period,
                inferred_fiscal_year,
                MAX(document_id) as latest_doc
            FROM periods_with_year
            GROUP BY period, inferred_fiscal_year
        )
        SELECT
            ft.period,
            ft.inferred_fiscal_year as fiscal_year,
            SUM(ft.value) as total_value,
            COUNT(*) as row_count
        FROM periods_with_year ft
        INNER JOIN latest_doc_per_period ld
            ON ft.period = ld.period
            AND ft.inferred_fiscal_year = ld.inferred_fiscal_year
            AND ft.document_id = ld.latest_doc
        GROUP BY ft.period, ft.inferred_fiscal_year
        HAVING SUM(ft.value) > 0
        ORDER BY ft.inferred_fiscal_year, ft.period
    """

    cursor.execute(query, (metric_exact,))
    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        raise ValueError(f"No data found for metric '{metric_exact}'")

    # Parse into TimeSeriesPoint objects
    points = []
    for period_str, fiscal_year, total_value, row_count in rows:
        # Parse period (e.g., "Jan-25" -> 2025-01-01)
        month_abbrev = period_str.split("-")[0]

        month_map = {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }

        month = month_map[month_abbrev]
        date = datetime(fiscal_year, month, 1)

        points.append(
            TimeSeriesPoint(
                date=date,
                value=float(total_value),
                label=f"{period_str} (FY{fiscal_year}, {row_count} rows)",
            )
        )

    if len(points) < min_points:
        raise ValueError(f"Insufficient data: {len(points)} points (need {min_points})")

    logger.info(f"Extracted {len(points)} data points for {metric_exact}")

    return TimeSeriesData(
        metric_name=metric_exact, points=points, interval="monthly", source_documents=[]
    )


async def forecast_ebitda_2026():
    """Forecast EBITDA for 2026."""
    print("\n" + "=" * 80)
    print("📊 EBITDA FORECAST FOR 2026")
    print("=" * 80)
    print()

    # Extract with exact match
    print("🔍 Extracting EBITDA data (exact match)...")
    ts_data = await extract_ebitda_exact_match(metric_exact="EBITDA", min_points=8)

    print(f"✅ Extracted: {len(ts_data.points)} months")
    print(
        f"   Range: {ts_data.points[0].date.strftime('%b-%y')} to {ts_data.points[-1].date.strftime('%b-%y')}"
    )
    print(f"   Latest: €{int(ts_data.points[-1].value):,}K")
    print()

    # Generate forecast
    print("🔮 Generating 12-month forecast...")
    result = await generate_forecast(metric="EBITDA", historical_data=ts_data, periods_ahead=12)

    print("✅ Complete!")
    print()
    print("=" * 80)
    print("2026 EBITDA PROJECTIONS")
    print("=" * 80)
    print()

    print(f"{'Period':<12} | {'Forecast (€K)':>15}")
    print("-" * 40)

    for pred in result.forecast[:12]:
        period = pred.date.strftime("%b %Y")
        forecast_val = int(pred.value)
        print(f"{period:<12} | €{forecast_val:>12,}K")

    print()
    total = sum(int(p.value) for p in result.forecast[:12])
    avg = total // 12
    print(f"Total 2026 EBITDA: €{total:,}K")
    print(f"Monthly Average:   €{avg:,}K")
    print()

    # Show AI reasoning
    print("=" * 80)
    print("AI FORECAST REASONING")
    print("=" * 80)
    print()
    print(result.confidence_reasoning)
    print()


if __name__ == "__main__":
    asyncio.run(forecast_ebitda_2026())
