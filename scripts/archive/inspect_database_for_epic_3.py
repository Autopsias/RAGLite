#!/usr/bin/env python3
"""Inspect PostgreSQL financial_tables and catalog available data for Epic 3.

Story 3.0.2: Create Epic 3 Data Dictionary
Purpose: Query database to catalog all available metrics, periods, entities, and
         currencies to prevent ground truth misalignment (Epic 2's 12% → 77.6% issue).

Usage:
    python scripts/inspect-database-for-epic-3.py
    python scripts/inspect-database-for-epic-3.py --output custom-path.json
"""

import json
import sys
from pathlib import Path

# Add parent directory to path to import raglite modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.clients import get_postgresql_connection  # noqa: E402


def inspect_database(output_path: str | None = None) -> dict:
    """Inspect PostgreSQL financial_tables and catalog available data.

    Queries financial_tables to extract all unique values for:
    - metrics (EBITDA, Revenue, Variable Cost, etc.)
    - periods (Aug-25, Sep-25, Aug-25 YTD, etc.)
    - entities (Portugal Cement, Tunisia Cement, etc.)
    - units (EUR, USD, EUR/ton, etc.) - actual column name is 'unit', not 'currency'
    - total row count

    Args:
        output_path: Optional custom path for JSON output.
                    Defaults to docs/data-dictionary-epic-3.json

    Returns:
        dict: Catalog with keys: metrics, periods, entities, units, total_rows

    Raises:
        ConnectionError: If database connection fails
        RuntimeError: If inspection queries fail

    Example:
        >>> catalog = inspect_database()
        >>> print(f"Found {len(catalog['metrics'])} metrics")
        >>> print(f"Total rows: {catalog['total_rows']}")
    """
    # Set default output path
    if output_path is None:
        output_path = str(Path(__file__).parent.parent / "docs" / "data-dictionary-epic-3.json")

    print("=" * 70)
    print("POSTGRESQL DATABASE INSPECTION - Epic 3 Data Dictionary")
    print("=" * 70)
    print("\nTarget Table: financial_tables")
    print(f"Output: {output_path}\n")

    # Connect to PostgreSQL
    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()
    except Exception as e:
        raise ConnectionError(f"Failed to connect to PostgreSQL: {e}") from e

    try:
        # Query 1: Total row count
        print("📊 Querying total row count...")
        cursor.execute("SELECT COUNT(*) FROM financial_tables;")
        total_rows = cursor.fetchone()[0]
        print(f"   ✓ Total rows: {total_rows:,}")

        # Query 2: All unique metrics
        print("\n📈 Querying unique metrics...")
        cursor.execute("SELECT DISTINCT metric FROM financial_tables ORDER BY metric;")
        metrics = [row[0] for row in cursor.fetchall()]
        print(f"   ✓ Found {len(metrics)} unique metrics")
        print(f"   📋 Sample: {', '.join(metrics[:5])}...")

        # Query 3: All unique periods
        print("\n📅 Querying unique periods...")
        cursor.execute("SELECT DISTINCT period FROM financial_tables ORDER BY period;")
        periods = [row[0] for row in cursor.fetchall()]
        print(f"   ✓ Found {len(periods)} unique periods")
        print(f"   📋 Sample: {', '.join(periods[:5])}...")

        # Query 4: All unique entities
        print("\n🏢 Querying unique entities...")
        cursor.execute("SELECT DISTINCT entity FROM financial_tables ORDER BY entity;")
        entities = [row[0] for row in cursor.fetchall()]
        print(f"   ✓ Found {len(entities)} unique entities")
        print(f"   📋 Sample: {', '.join(entities[:3])}...")

        # Query 5: All unique units (column is named 'unit', not 'currency')
        print("\n💵 Querying unique units...")
        cursor.execute("SELECT DISTINCT unit FROM financial_tables ORDER BY unit;")
        units = [row[0] for row in cursor.fetchall()]
        print(f"   ✓ Found {len(units)} unique units")
        print(f"   📋 Sample units: {', '.join(units[:5])}...")

    except Exception as e:
        raise RuntimeError(f"Failed to inspect database: {e}") from e
    finally:
        cursor.close()

    # Build comprehensive data catalog
    catalog = {
        "metrics": metrics,
        "periods": periods,
        "entities": entities,
        "units": units,  # Note: column is 'unit', not 'currency'
        "total_rows": total_rows,
    }

    # Save JSON catalog
    print(f"\n💾 Saving catalog to: {output_path}")
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with output_file.open("w") as f:
            json.dump(catalog, f, indent=2)

        print(f"   ✓ Catalog saved successfully ({output_file.stat().st_size:,} bytes)")
    except Exception as e:
        raise RuntimeError(f"Failed to save catalog to {output_path}: {e}") from e

    # Print summary
    print("\n" + "=" * 70)
    print("INSPECTION COMPLETE")
    print("=" * 70)
    print("\n📊 Summary:")
    print(f"   • Total Rows:    {total_rows:,}")
    print(f"   • Metrics:       {len(metrics)}")
    print(f"   • Periods:       {len(periods)}")
    print(f"   • Entities:      {len(entities)}")
    print(f"   • Units:         {len(units)}")
    print("\n✅ Catalog ready for Epic 3 test creation")
    print("   Next step: Create data dictionary (docs/data-dictionary-epic-3.md)\n")

    return catalog


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect PostgreSQL financial_tables for Epic 3 data dictionary"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output path for JSON catalog (default: docs/data-dictionary-epic-3.json)",
    )

    args = parser.parse_args()

    try:
        catalog = inspect_database(output_path=args.output)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
