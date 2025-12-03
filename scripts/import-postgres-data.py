#!/usr/bin/env python3
"""Import PostgreSQL table data from cached export.

Restores rows from JSON files exported by export-postgres-data.py,
allowing CI to skip PDF ingestion when data hasn't changed.

SAFETY: This script DELETES existing data before importing.
        It REFUSES to run against production ports (6333/5432) unless
        explicitly overridden with --force-production flag.

Usage:
    # Safe: Uses test ports from APP_ENV=test
    APP_ENV=test python scripts/import-postgres-data.py --input .postgres-export

    # DANGEROUS: Override production safety (requires typed confirmation)
    python scripts/import-postgres-data.py --input .postgres-export --force-production
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

# Production port constants (NEVER use these in CI/tests)
PRODUCTION_QDRANT_PORT = 6333
PRODUCTION_POSTGRES_PORT = 5432


def check_production_safety(force_production: bool = False) -> None:
    """Check if running against production and block unless explicitly forced.

    This is a CRITICAL safety check to prevent accidental data loss.
    The script DELETES existing data before importing, so running against
    production would destroy all ingested documents.

    Args:
        force_production: If True, allow running against production with warning

    Raises:
        SystemExit: If running against production without --force-production
    """
    postgres_port = settings.postgres_port

    is_production_postgres = postgres_port == PRODUCTION_POSTGRES_PORT

    if is_production_postgres:
        logger.error("=" * 70)
        logger.error("🚨 PRODUCTION DATABASE DETECTED - IMPORT BLOCKED 🚨")
        logger.error("=" * 70)
        logger.error(f"PostgreSQL port: {postgres_port} (production={is_production_postgres})")
        logger.error("")
        logger.error("This script DELETES existing data before importing!")
        logger.error("Running against production would DESTROY ALL DATA.")
        logger.error("")

        if not force_production:
            logger.error("To use test databases, set APP_ENV=test:")
            logger.error(
                "  APP_ENV=test python scripts/import-postgres-data.py --input .postgres-export"
            )
            logger.error("")
            logger.error("To force production (DANGEROUS), use --force-production flag")
            logger.error("=" * 70)
            sys.exit(1)

        # Force production requested - require typed confirmation
        logger.warning("⚠️  --force-production flag detected")
        logger.warning("You are about to DELETE AND REPLACE production data!")
        logger.warning("")

        confirmation = input("Type 'DELETE PRODUCTION DATA' to confirm: ")

        if confirmation != "DELETE PRODUCTION DATA":
            logger.error("Confirmation failed - aborting")
            sys.exit(1)

        logger.warning("Production override confirmed - proceeding with caution")
    else:
        logger.info(f"✅ Using test database (PostgreSQL:{postgres_port})")


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
    parser = argparse.ArgumentParser(
        description="Import PostgreSQL tables from cache (DELETES existing data!)",
        epilog="SAFETY: This script refuses to run against production ports without --force-production",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=".postgres-export",
        help="Input directory containing export files",
    )
    parser.add_argument(
        "--force-production",
        action="store_true",
        help="DANGEROUS: Allow running against production databases (requires typed confirmation)",
    )
    args = parser.parse_args()

    # CRITICAL: Check production safety BEFORE any database operations
    check_production_safety(force_production=args.force_production)

    input_dir = Path(args.input)

    try:
        import_postgres_data(input_dir)
        return 0
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
