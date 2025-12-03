#!/usr/bin/env python3
"""Check production database status (READ-ONLY)."""

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

logger = get_logger(__name__)


def main() -> int:
    """Check production database status."""
    print("\n" + "=" * 70)
    print("📊 PRODUCTION DATABASE STATUS")
    print("=" * 70)
    print("\nEnvironment: PRODUCTION")
    print(f"Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
    print(f"PostgreSQL: {settings.postgres_db}@{settings.postgres_host}:{settings.postgres_port}")
    print("\n" + "-" * 70)

    try:
        # Check Qdrant
        print("\n🔍 Qdrant Status:")
        _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        try:
            collection_info = _qdrant.get_collection(settings.qdrant_collection_name)
            print(f"  Collection: '{settings.qdrant_collection_name}'")
            print(f"  ✅ Vectors count: {collection_info.vectors_count:,}")
            print(f"  ✅ Points count: {collection_info.points_count:,}")
        except Exception as e:
            print(f"  ❌ Collection does not exist: {e}")

        # Check PostgreSQL
        print("\n🗄️  PostgreSQL Status:")
        import psycopg2

        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        cursor = conn.cursor()

        # Check if tables exist
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ('financial_chunks', 'financial_tables')
            ORDER BY table_name
        """
        )
        existing_tables = [row[0] for row in cursor.fetchall()]

        if not existing_tables:
            print("  ⚠️  No tables found")
        else:
            # Get chunk counts
            if "financial_chunks" in existing_tables:
                cursor.execute("SELECT COUNT(*) FROM financial_chunks")
                chunk_count = cursor.fetchone()[0]
                print(f"  ✅ financial_chunks: {chunk_count:,} rows")

                # Get unique documents from chunks
                cursor.execute("SELECT COUNT(DISTINCT document_id) FROM financial_chunks")
                unique_docs = cursor.fetchone()[0]
                print(f"     └─ Unique documents: {unique_docs:,}")
            else:
                print("  ⚠️  financial_chunks: Table does not exist")

            # Get table counts
            if "financial_tables" in existing_tables:
                cursor.execute("SELECT COUNT(*) FROM financial_tables")
                table_count = cursor.fetchone()[0]
                print(f"  ✅ financial_tables: {table_count:,} rows")

                # Get unique documents from tables
                cursor.execute("SELECT COUNT(DISTINCT document_id) FROM financial_tables")
                unique_docs_tables = cursor.fetchone()[0]
                print(f"     └─ Unique documents: {unique_docs_tables:,}")
            else:
                print("  ⚠️  financial_tables: Table does not exist")

        conn.close()

        print("\n" + "=" * 70)
        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
