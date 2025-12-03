#!/usr/bin/env python3
"""Clean production database completely (DESTRUCTIVE).

This script safely deletes ALL data from production databases:
- Qdrant collection (all vector embeddings)
- PostgreSQL tables (financial_chunks, financial_tables)

**IMPORTANT:** This script requires typed confirmation for destructive operations.
You must type the exact phrase:
"DELETE ALL FINANCIAL DOCUMENTS, TABLES, AND VECTOR EMBEDDINGS FROM PRODUCTION"

Usage:
    python scripts/cleanup-production.py
"""

import os
import sys
from pathlib import Path

# Ensure production environment
os.environ["APP_ENV"] = "production"

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient

from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.safety import OperationType, SafetyGuard

logger = get_logger(__name__)


def cleanup_production_database(guard: SafetyGuard) -> bool:
    """Clean production database (DESTRUCTIVE).

    Returns:
        True if successful, False otherwise
    """
    # Require typed confirmation for destructive operation
    guard.require_typed_confirmation(
        "cleanup_production", "financial documents, tables, and vector embeddings"
    )

    # Check if operation is allowed (after typed confirmation)
    guard.check_operation("cleanup_production", OperationType.DESTRUCTIVE, force_data_loss=True)

    try:
        # Connect to production Qdrant
        _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        # Delete existing collection
        collection_name = settings.qdrant_collection_name
        try:
            _qdrant.delete_collection(collection_name)
            print(f"  ✅ Deleted Qdrant collection '{collection_name}'")
            logger.warning(
                "Production collection deleted",
                extra={"collection": collection_name},
            )
        except Exception:
            print(f"  ℹ️  Collection '{collection_name}' did not exist")

        # Clean PostgreSQL tables
        import psycopg2

        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        cursor = conn.cursor()

        # Check if actual tables exist (financial_chunks and financial_tables)
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ('financial_chunks', 'financial_tables')
        """
        )
        existing_tables = [row[0] for row in cursor.fetchall()]

        if existing_tables:
            # Delete all data from actual tables used by the ingestion pipeline
            if "financial_tables" in existing_tables:
                cursor.execute("DELETE FROM financial_tables")
                deleted_count = cursor.rowcount
                print(f"  ✅ Deleted {deleted_count} rows from financial_tables")
            if "financial_chunks" in existing_tables:
                cursor.execute("DELETE FROM financial_chunks")
                deleted_count = cursor.rowcount
                print(f"  ✅ Deleted {deleted_count} rows from financial_chunks")
            conn.commit()
        else:
            print("  ℹ️  PostgreSQL tables do not exist")

        conn.close()

        return True

    except Exception as e:
        logger.error("Cleanup failed", extra={"error": str(e)})
        print(f"  ❌ ERROR: {e}")
        return False


def verify_cleanup(guard: SafetyGuard) -> None:
    """Verify that data was properly cleaned."""
    print("\n--- Verification ---")

    try:
        # Check Qdrant
        _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        try:
            collection_info = _qdrant.get_collection(settings.qdrant_collection_name)
            print(f"  ⚠️  Qdrant collection '{settings.qdrant_collection_name}' still exists!")
            print(f"    Vectors count: {collection_info.vectors_count}")
            print(f"    Points count: {collection_info.points_count}")
        except Exception:
            print(
                f"  ✅ Qdrant collection '{settings.qdrant_collection_name}' deleted successfully"
            )

        # Check PostgreSQL
        import psycopg2

        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        cursor = conn.cursor()

        # Check the actual tables used by the ingestion pipeline
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ('financial_chunks', 'financial_tables')
        """
        )
        existing_tables = [row[0] for row in cursor.fetchall()]

        print("  PostgreSQL:")

        if "financial_chunks" in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM financial_chunks")
            chunk_count = cursor.fetchone()[0]
            if chunk_count == 0:
                print("    ✅ Financial Chunks: Empty (0 rows)")
            else:
                print(f"    ⚠️  Financial Chunks: {chunk_count} rows still exist!")
        else:
            print("    ✅ Financial Chunks: Table does not exist")

        if "financial_tables" in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM financial_tables")
            table_count = cursor.fetchone()[0]
            if table_count == 0:
                print("    ✅ Financial Tables: Empty (0 rows)")
            else:
                print(f"    ⚠️  Financial Tables: {table_count} rows still exist!")
        else:
            print("    ✅ Financial Tables: Table does not exist")

        conn.close()

    except Exception as e:
        print(f"  ⚠️  Verification error: {e}")


def main() -> int:
    """Main entry point."""
    # Initialize SafetyGuard
    guard = SafetyGuard()
    guard.display_environment_banner()

    print("\n" + "=" * 70)
    print("⚠️  PRODUCTION DATABASE CLEANUP (DESTRUCTIVE)")
    print("=" * 70)
    print("\nThis will permanently delete:")
    print("  - All vector embeddings from Qdrant")
    print("  - All financial chunks from PostgreSQL")
    print("  - All financial tables from PostgreSQL")
    print("\nYou will need to re-ingest all documents after this operation.")

    if not cleanup_production_database(guard):
        print("\n❌ Cleanup failed!")
        return 1

    verify_cleanup(guard)

    print("\n" + "=" * 70)
    print("✅ CLEANUP COMPLETE")
    print("=" * 70)
    print("\nProduction database is now empty.")
    print("To re-ingest documents, use:")
    print("  python scripts/cleanup-and-reingest.py /path/to/documents")
    print("\nOr use the MCP server:")
    print("  await ingest_financial_document(doc_path='/path/to/document.pdf')")

    return 0


if __name__ == "__main__":
    sys.exit(main())
