#!/usr/bin/env python3
"""Show EBITDA IFRS data month-by-month."""

import asyncio
import os

os.environ["APP_ENV"] = "production"

from raglite.shared.clients import get_postgresql_connection


async def show_ebitda_ifrs():
    print("📊 EBITDA IFRS Data (Consolidated Reporting Standard)")
    print("=" * 80)
    print()

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    query = """
        WITH periods_with_year AS (
            SELECT
                period,
                COALESCE(
                    fiscal_year,
                    2000 + CAST(SUBSTRING(period FROM '[0-9]{2}$') AS INTEGER)
                ) as inferred_fiscal_year,
                document_id,
                value,
                entity
            FROM financial_tables
            WHERE metric = 'EBITDA IFRS'
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
            COUNT(DISTINCT ft.entity) as entity_count,
            COUNT(*) as row_count
        FROM periods_with_year ft
        INNER JOIN latest_doc_per_period ld
            ON ft.period = ld.period
            AND ft.inferred_fiscal_year = ld.inferred_fiscal_year
            AND ft.document_id = ld.latest_doc
        GROUP BY ft.period, ft.inferred_fiscal_year
        ORDER BY ft.inferred_fiscal_year, ft.period
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    if not rows:
        print('❌ No data found for "EBITDA IFRS" metric')
        return

    print(f"{'Period':<12} | {'FY':>4} | {'Value (€K)':>15} | {'Entities':>8} | {'Rows':>5}")
    print("-" * 80)

    total_2024 = 0
    total_2025 = 0
    months_2024 = 0
    months_2025 = 0

    for period, fy, value, entity_count, row_count in rows:
        print(f"{period:<12} | {fy:>4} | {int(value):>15,} | {entity_count:>8} | {row_count:>5}")

        if fy == 2024:
            total_2024 += value
            months_2024 += 1
        elif fy == 2025:
            total_2025 += value
            months_2025 += 1

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"2024 ({months_2024} months): €{int(total_2024):,}K (€{int(total_2024 / 1000)}M)")
    print(f"2025 ({months_2025} months): €{int(total_2025):,}K (€{int(total_2025 / 1000)}M)")
    print()

    if months_2025 > 0:
        avg_monthly_2025 = total_2025 / months_2025
        projected_full_year = avg_monthly_2025 * 12
        print(f"📈 Full-year 2025 projection (based on {months_2025}-month average):")
        print(f"   Monthly average: €{int(avg_monthly_2025):,}K")
        print(
            f"   Full-year projection: €{int(projected_full_year):,}K (€{int(projected_full_year / 1000)}M)"
        )
        print()

        print("📊 Comparison to €207M target:")
        target = 207000
        diff = projected_full_year - target
        pct = (diff / target) * 100
        print(f"   Target: €{int(target):,}K (€{int(target / 1000)}M)")
        print(f"   Projected: €{int(projected_full_year):,}K (€{int(projected_full_year / 1000)}M)")
        print(f"   Difference: €{int(diff):,}K ({pct:+.1f}%)")
    print()

    cursor.close()


if __name__ == "__main__":
    asyncio.run(show_ebitda_ifrs())
