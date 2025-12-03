#!/usr/bin/env python3
"""Find which metric or combination equals €207M for 2025."""

import asyncio
import os

os.environ["APP_ENV"] = "production"

from raglite.shared.clients import get_postgresql_connection


async def find_207m_metric():
    print("🎯 Searching for Metrics Totaling ~€207M for 2025")
    print("=" * 80)
    print()

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Search for any metric (not just EBITDA) that might total €207M
    query = """
        SELECT
            metric,
            COUNT(DISTINCT period) as period_count,
            SUM(value) as total_2025,
            AVG(value) as avg_value
        FROM financial_tables
        WHERE period LIKE '%-25'
          AND period ~ '^[A-Z][a-z]{2}-[0-9]{2}$'
          AND value IS NOT NULL
          AND value > 0
        GROUP BY metric
        HAVING SUM(value) BETWEEN 180000 AND 230000
        ORDER BY SUM(value) DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()

    if results:
        print("✅ Metrics with 2025 totals between €180M-€230M:")
        print(f"{'Metric':<50} | {'Periods':>7} | {'2025 Total (€K)':>20} | {'Avg/Period':>15}")
        print("-" * 110)

        for metric, period_count, total, avg in results:
            print(f"{metric:<50} | {period_count:>7} | {int(total):>20,} | {int(avg):>15,}")
    else:
        print("❌ No single metric found totaling €180M-€230M")

    print()
    print("=" * 80)
    print("📊 Checking if €207M comes from summing multiple EBITDA variants:")
    print("=" * 80)
    print()

    # Check what combination of EBITDA metrics might sum to €207M
    query_combo = """
        SELECT
            metric,
            SUM(value) as total_2025
        FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND period LIKE '%-25'
          AND period ~ '^[A-Z][a-z]{2}-[0-9]{2}$'
          AND value IS NOT NULL
        GROUP BY metric
        ORDER BY SUM(value) DESC
    """

    cursor.execute(query_combo)
    ebitda_variants = cursor.fetchall()

    print(f"{'EBITDA Variant':<50} | {'2025 Total (€K)':>20}")
    print("-" * 75)

    running_total = 0
    for metric, total in ebitda_variants:
        running_total += total
        marker = " ⬅️ Running total" if abs(running_total - 207000) < 10000 else ""
        print(f"{metric:<50} | {int(total):>20,}{marker}")
        if abs(running_total - 207000) < 10000:
            print(f"{'':>51}   {'=' * 20}")
            print(f"{'Running Total:':<50} | {int(running_total):>20,} ← MATCHES €207M!")

    print(f"{'':>51}   {'=' * 20}")
    print(f"{'Grand Total (All EBITDA variants):':<50} | {int(running_total):>20,}")

    cursor.close()
    print()


if __name__ == "__main__":
    asyncio.run(find_207m_metric())
