#!/usr/bin/env python3
"""Export PostgreSQL table data for caching in CI.

Exports all rows from financial_chunks, financial_tables, and entity_mappings
to JSON files that can be restored later to skip ingestion.

Usage:
    python scripts/export-postgres-data.py --output .postgres-export
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.config import settings  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def json_serializer(obj):
    """Custom JSON serializer for PostgreSQL types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (bytes, bytearray)):
        return obj.decode("utf-8", errors="replace")
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def export_table(cursor, table_name: str, output_dir: Path) -> int:
    """Export a single table to JSON.

    Args:
        cursor: Database cursor
        table_name: Name of table to export
        output_dir: Directory to store export files

    Returns:
        Number of rows exported
    """
    # Check if table exists
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
    """,
        (table_name,),
    )
    if not cursor.fetchone()[0]:
        logger.warning(f"Table '{table_name}' does not exist, skipping")
        return 0

    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")  # noqa: S608
    row_count = cursor.fetchone()[0]

    if row_count == 0:
        logger.info(f"Table '{table_name}' is empty, skipping")
        return 0

    # Export all rows
    cursor.execute(f"SELECT * FROM {table_name}")  # noqa: S608
    rows = cursor.fetchall()

    # Convert to list of dicts
    data = [dict(row) for row in rows]

    # Save to JSON file
    export_file = output_dir / f"{table_name}.json"
    with open(export_file, "w") as f:
        json.dump(data, f, default=json_serializer)

    logger.info(f"  ✓ Exported {len(data)} rows from {table_name}")
    return len(data)


def export_postgres_data(output_dir: Path) -> None:
    """Export PostgreSQL tables to JSON files.

    Args:
        output_dir: Directory to store export files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"Connecting to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )

    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        cursor_factory=RealDictCursor,
    )
    cursor = conn.cursor()

    # Tables to export
    tables = ["financial_chunks", "financial_tables", "entity_mappings"]

    total_rows = 0
    for table_name in tables:
        rows = export_table(cursor, table_name, output_dir)
        total_rows += rows

    # Save metadata
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(
            {
                "exported_at": datetime.now().isoformat(),
                "database": settings.postgres_db,
                "tables": tables,
                "total_rows": total_rows,
            },
            f,
            indent=2,
        )

    cursor.close()
    conn.close()

    logger.info(f"✅ Exported {total_rows} total rows to {output_dir}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Export PostgreSQL tables for caching")
    parser.add_argument(
        "--output",
        type=str,
        default=".postgres-export",
        help="Output directory for export files",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)

    try:
        export_postgres_data(output_dir)
        return 0
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
