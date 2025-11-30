"""Export PostgreSQL data to JSON for CI caching.

This script exports the PostgreSQL financial_tables and financial_chunks tables
to JSON files that can be cached by CI and restored in subsequent runs.

Usage:
    python scripts/export-postgres-data.py

    # Custom output directory
    python scripts/export-postgres-data.py --output .postgres-export

The export includes:
- financial_tables (all table rows)
- financial_chunks (all chunk metadata)
- entity_mappings (entity normalization)

Typical file size: ~10-20 MB for 160-page PDF
"""

import argparse
import json
from pathlib import Path

import psycopg2

from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def export_postgres_data(output_dir: str = ".postgres-export") -> Path:
    """Export PostgreSQL data to JSON files for CI caching.

    Args:
        output_dir: Directory to store export files

    Returns:
        Path to exported data directory

    Raises:
        ValueError: If tables are empty or don't exist
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Exporting PostgreSQL data to: {output_path}")

    # Build connection string
    conn_str = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"

    # Connect to PostgreSQL
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()

    # Export financial_tables
    logger.info("Exporting financial_tables...")
    cursor.execute("SELECT * FROM financial_tables")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    financial_tables_data = {
        "table_name": "financial_tables",
        "columns": columns,
        "row_count": len(rows),
        "rows": [dict(zip(columns, row, strict=False)) for row in rows],
    }

    tables_file = output_path / "financial_tables.json"
    with open(tables_file, "w") as f:
        json.dump(financial_tables_data, f, indent=2, default=str)

    logger.info(
        f"✅ Exported financial_tables: {len(rows)} rows ({tables_file.stat().st_size / 1024 / 1024:.1f} MB)"
    )

    # Export financial_chunks
    logger.info("Exporting financial_chunks...")
    cursor.execute("SELECT * FROM financial_chunks")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    financial_chunks_data = {
        "table_name": "financial_chunks",
        "columns": columns,
        "row_count": len(rows),
        "rows": [dict(zip(columns, row, strict=False)) for row in rows],
    }

    chunks_file = output_path / "financial_chunks.json"
    with open(chunks_file, "w") as f:
        json.dump(financial_chunks_data, f, indent=2, default=str)

    logger.info(
        f"✅ Exported financial_chunks: {len(rows)} rows ({chunks_file.stat().st_size / 1024 / 1024:.1f} MB)"
    )

    # Export entity_mappings
    logger.info("Exporting entity_mappings...")
    cursor.execute("SELECT * FROM entity_mappings")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    entity_mappings_data = {
        "table_name": "entity_mappings",
        "columns": columns,
        "row_count": len(rows),
        "rows": [dict(zip(columns, row, strict=False)) for row in rows],
    }

    mappings_file = output_path / "entity_mappings.json"
    with open(mappings_file, "w") as f:
        json.dump(entity_mappings_data, f, indent=2, default=str)

    logger.info(
        f"✅ Exported entity_mappings: {len(rows)} rows ({mappings_file.stat().st_size / 1024:.1f} KB)"
    )

    cursor.close()
    conn.close()

    logger.info(f"✅ PostgreSQL export complete: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Export PostgreSQL data to JSON")
    parser.add_argument(
        "--output",
        "-o",
        default=".postgres-export",
        help="Output directory for export files (default: .postgres-export)",
    )

    args = parser.parse_args()

    try:
        export_postgres_data(args.output)
        print("\n✅ Export complete")
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        raise


if __name__ == "__main__":
    main()
