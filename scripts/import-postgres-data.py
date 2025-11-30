#!/usr/bin/env python3
"""Import PostgreSQL table data from cached export.

Restores rows from JSON files exported by export-postgres-data.py,
allowing CI to skip PDF ingestion when data hasn't changed.

Usage:
    python scripts/import-postgres-data.py --input .postgres-export
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.config import settings  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def import_table(cursor, table_name: str, input_dir: Path) -> int:
    """Import a single table from JSON.

    Args:
        cursor: Database cursor
        table_name: Name of table to import
        input_dir: Directory containing export files

    Returns:
        Number of rows imported
    """
    json_file = input_dir / f"{table_name}.json"

    if not json_file.exists():
        logger.warning(f"Export file not found for {table_name}, skipping")
        return 0

    with open(json_file) as f:
        data = json.load(f)

    if not data:
        logger.info(f"No data for {table_name}, skipping")
        return 0

    # Clear existing data
    cursor.execute(f"DELETE FROM {table_name}")  # noqa: S608

    # Get column names from first row
    columns = list(data[0].keys())

    # Prepare insert statement
    placeholders = ", ".join(["%s"] * len(columns))
    column_names = ", ".join(columns)
    insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"  # noqa: S608

    # Insert rows in batches
    batch_size = 100
    for i in range(0, len(data), batch_size):
        batch = data[i : i + batch_size]
        values = []
        for row in batch:
            row_values = []
            for col in columns:
                val = row.get(col)
                # Handle datetime strings
                if isinstance(val, str) and col in ("created_at", "updated_at", "ingested_at"):
                    try:
                        val = datetime.fromisoformat(val)
                    except ValueError:
                        pass
                row_values.append(val)
            values.append(tuple(row_values))

        cursor.executemany(insert_sql, values)

    logger.info(f"  ✓ Imported {len(data)} rows into {table_name}")
    return len(data)


def import_postgres_data(input_dir: Path) -> None:
    """Import PostgreSQL tables from JSON files.

    Args:
        input_dir: Directory containing export files
    """
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)

    metadata_file = input_dir / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)
        logger.info(f"Loading export from {metadata.get('exported_at', 'unknown')}")

    logger.info(
        f"Connecting to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )

    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Tables to import (order matters due to potential foreign keys)
    tables = ["financial_chunks", "financial_tables", "entity_mappings"]

    total_rows = 0
    for table_name in tables:
        rows = import_table(cursor, table_name, input_dir)
        total_rows += rows

    cursor.close()
    conn.close()

    logger.info(f"✅ Imported {total_rows} total rows from {input_dir}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Import PostgreSQL tables from cache")
    parser.add_argument(
        "--input",
        type=str,
        default=".postgres-export",
        help="Input directory containing export files",
    )
    args = parser.parse_args()

    input_dir = Path(args.input)

    try:
        import_postgres_data(input_dir)
        return 0
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
