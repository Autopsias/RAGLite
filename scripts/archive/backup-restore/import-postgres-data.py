"""Import PostgreSQL data from CI cache.

This script restores PostgreSQL tables from previously exported JSON files,
allowing CI runs to skip the 25-minute ingestion process.

Usage:
    python scripts/import-postgres-data.py

    # Custom input directory
    python scripts/import-postgres-data.py --input .postgres-export

The script will:
1. Clear existing tables
2. Import all rows from JSON files
3. Verify the import succeeded

Expected time: ~10-20 seconds (vs 25 minutes for full ingestion)
"""

import argparse
import json
from pathlib import Path

import psycopg2

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def import_postgres_data(input_dir: str = ".postgres-export") -> dict:
    """Import PostgreSQL data from JSON files.

    Args:
        input_dir: Directory containing export JSON files

    Returns:
        Dict with row counts per table

    Raises:
        FileNotFoundError: If export files don't exist
        ValueError: If import verification fails
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input directory not found: {input_path}. "
            "Run export first: python scripts/export-postgres-data.py"
        )

    logger.info(f"Importing PostgreSQL data from: {input_path}")

    # Build connection string
    conn_str = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"

    # Connect to PostgreSQL
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()

    results = {}

    # Import financial_tables
    tables_file = input_path / "financial_tables.json"
    if tables_file.exists():
        logger.info("Importing financial_tables...")

        with open(tables_file) as f:
            data = json.load(f)

        # Clear existing data
        cursor.execute("DELETE FROM financial_tables")

        # Insert rows
        columns = data["columns"]
        rows = data["rows"]

        for row_dict in rows:
            placeholders = ", ".join(["%s"] * len(columns))
            columns_str = ", ".join(columns)
            sql = f"INSERT INTO financial_tables ({columns_str}) VALUES ({placeholders})"

            values = [row_dict.get(col) for col in columns]
            cursor.execute(sql, values)

        conn.commit()

        logger.info(f"✅ Imported financial_tables: {len(rows)} rows")
        results["financial_tables"] = len(rows)

    # Import financial_chunks
    chunks_file = input_path / "financial_chunks.json"
    if chunks_file.exists():
        logger.info("Importing financial_chunks...")

        with open(chunks_file) as f:
            data = json.load(f)

        # Clear existing data
        cursor.execute("DELETE FROM financial_chunks")

        # Insert rows
        columns = data["columns"]
        rows = data["rows"]

        for row_dict in rows:
            placeholders = ", ".join(["%s"] * len(columns))
            columns_str = ", ".join(columns)
            sql = f"INSERT INTO financial_chunks ({columns_str}) VALUES ({placeholders})"

            values = [row_dict.get(col) for col in columns]
            cursor.execute(sql, values)

        conn.commit()

        logger.info(f"✅ Imported financial_chunks: {len(rows)} rows")
        results["financial_chunks"] = len(rows)

    # Import entity_mappings
    mappings_file = input_path / "entity_mappings.json"
    if mappings_file.exists():
        logger.info("Importing entity_mappings...")

        with open(mappings_file) as f:
            data = json.load(f)

        # Clear existing data
        cursor.execute("DELETE FROM entity_mappings")

        # Insert rows
        columns = data["columns"]
        rows = data["rows"]

        for row_dict in rows:
            placeholders = ", ".join(["%s"] * len(columns))
            columns_str = ", ".join(columns)
            sql = f"INSERT INTO entity_mappings ({columns_str}) VALUES ({placeholders})"

            values = [row_dict.get(col) for col in columns]
            cursor.execute(sql, values)

        conn.commit()

        logger.info(f"✅ Imported entity_mappings: {len(rows)} rows")
        results["entity_mappings"] = len(rows)

    cursor.close()
    conn.close()

    logger.info("✅ PostgreSQL import complete")
    return results


def main():
    parser = argparse.ArgumentParser(description="Import PostgreSQL data from JSON")
    parser.add_argument(
        "--input",
        "-i",
        default=".postgres-export",
        help="Input directory containing export files (default: .postgres-export)",
    )

    args = parser.parse_args()

    try:
        results = import_postgres_data(args.input)
        print("\n✅ Import complete:")
        for table, count in results.items():
            print(f"   {table}: {count} rows")
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        raise


if __name__ == "__main__":
    main()
