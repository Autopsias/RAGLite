#!/usr/bin/env python3
"""
Diagnose ingestion pipeline issue.
Traces chunking, embedding generation, and storage steps.
"""

import asyncio
from pathlib import Path

from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings


async def main():
    """Diagnose ingestion pipeline."""
    print("=" * 80)
    print("INGESTION PIPELINE DIAGNOSTICS")
    print("=" * 80)

    # Check Qdrant connection
    try:
        client = get_qdrant_client()
        collections = client.get_collections().collections
        print(f"\n✅ Qdrant connected: http://{settings.qdrant_host}:{settings.qdrant_port}")
        print(f"Collections: {[c.name for c in collections]}")

        if settings.qdrant_collection_name in [c.name for c in collections]:
            # Check collection stats
            collection_info = client.get_collection(settings.qdrant_collection_name)
            print(f"  - {settings.qdrant_collection_name}: {collection_info.points_count} points")
        else:
            print(f"  - ❌ Collection '{settings.qdrant_collection_name}' does NOT exist")
    except Exception as e:
        print(f"\n❌ Qdrant connection failed: {e}")

    # Check PostgreSQL
    try:
        from raglite.shared.clients import get_postgresql_connection

        conn = get_postgresql_connection()
        cursor = conn.cursor()

        print(
            f"\n✅ PostgreSQL connected: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )

        # Check table counts
        cursor.execute("SELECT COUNT(*) FROM financial_chunks")
        chunk_count = cursor.fetchone()[0]
        print(f"  - financial_chunks: {chunk_count} rows")

        cursor.execute("SELECT COUNT(*) FROM financial_tables")
        table_count = cursor.fetchone()[0]
        print(f"  - financial_tables: {table_count} rows")

        # Check which documents are stored
        cursor.execute("SELECT DISTINCT document_id FROM financial_tables")
        doc_ids = [row[0] for row in cursor.fetchall()]
        print(f"  - Documents in PostgreSQL: {doc_ids}")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"\n❌ PostgreSQL connection failed: {e}")

    # Check PDF file
    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
    if pdf_path.exists():
        print(f"\n✅ PDF found: {pdf_path}")
        print(f"  - Size: {pdf_path.stat().st_size / (1024 * 1024):.1f} MB")
    else:
        print(f"\n❌ PDF NOT found: {pdf_path}")

    # Check configuration
    print("\n📋 Configuration:")
    print(f"  - Qdrant collection: {settings.qdrant_collection_name}")
    print(f"  - Embedding model: {settings.embedding_model}")
    print(f"  - Embedding dimension: {settings.embedding_dimension}")
    print(f"  - Mistral API key: {'✅ Set' if settings.mistral_api_key else '❌ Not set'}")

    print("\n" + "=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    print("The ingestion completed successfully but data wasn't written to databases.")
    print("This suggests chunks or embeddings were empty.")
    print("\nNext steps:")
    print("1. Check if Mistral API key is working")
    print("2. Check embedding generation logs for errors")
    print("3. Re-run ingestion with verbose logging")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
