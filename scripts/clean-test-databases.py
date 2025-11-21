"""Clean stale test data from Qdrant and PostgreSQL test databases.

This script resolves the "Chunk count 21 not in expected range (4, 10)" error
by deleting stale data from pre-Story 2.8 chunking algorithms.

Usage:
    uv run python scripts/clean-test-databases.py

Story 4.0.5: Test database separation ensures this only affects test databases.
"""

import os
import sys

# CRITICAL: Set APP_ENV=test before any imports
os.environ["APP_ENV"] = "test"
os.environ["TESTING"] = "true"

from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings

print("=" * 80)
print("CLEANING TEST DATABASES")
print("=" * 80)
print(f"Environment: APP_ENV={os.getenv('APP_ENV')}")
print(f"Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
print(f"Collection: {settings.qdrant_collection_name}")
print(f"PostgreSQL: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
print("=" * 80)

# Clean Qdrant test collection
print("\n🧹 Cleaning Qdrant test collection...")
try:
    qdrant = get_qdrant_client()
    count = qdrant.count(collection_name=settings.qdrant_collection_name).count
    print(f"   Current chunks: {count}")

    if count > 0:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
        print(f"   ✓ Deleted collection: {settings.qdrant_collection_name}")
    else:
        print("   ✓ Collection already empty")
except Exception as e:
    if "doesn't exist" in str(e) or "Not found" in str(e):
        print("   ✓ Collection doesn't exist (already clean)")
    else:
        print(f"   ⚠️  Error: {e}")
        sys.exit(1)

# Clean PostgreSQL test database
print("\n🧹 Cleaning PostgreSQL test database...")
try:
    import psycopg2

    conn_str = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    cursor = conn.cursor()

    # Check current row counts
    cursor.execute("SELECT COUNT(*) FROM financial_chunks")
    chunk_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    table_count = cursor.fetchone()[0]

    print(f"   Current rows: {table_count} tables, {chunk_count} chunks")

    if chunk_count > 0 or table_count > 0:
        cursor.execute("DELETE FROM financial_chunks")
        chunks_deleted = cursor.rowcount
        cursor.execute("DELETE FROM financial_tables")
        tables_deleted = cursor.rowcount
        print(f"   ✓ Deleted: {tables_deleted} table rows, {chunks_deleted} chunk rows")
    else:
        print("   ✓ Tables already empty")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"   ⚠️  Error: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ TEST DATABASES CLEANED SUCCESSFULLY")
print("=" * 80)
print("\nNext steps:")
print('  1. Run integration tests: uv run pytest tests/integration/ -m ""')
print("  2. Fixture will auto-ingest 4-page PDF → 7 chunks (expected range 4-10)")
print("  3. All 220 integration tests should pass")
print("=" * 80)
