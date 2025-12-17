#!/usr/bin/env python3
"""
Database Consistency Validation Script

Validates that Qdrant and PostgreSQL have exactly the same documents.
This script performs read-only checks and does not modify any data.

Usage:
    python scripts/validate-database-consistency.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient

# Production configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "financial_docs"


def get_qdrant_documents() -> set[str]:
    """Get all unique document names from Qdrant."""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    documents = set()
    offset = None

    while True:
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            offset=offset,
            with_payload=["source_document"],
            with_vectors=False,
        )
        points, next_offset = result

        for point in points:
            doc = point.payload.get("source_document")
            if doc:
                documents.add(doc)

        if next_offset is None:
            break
        offset = next_offset

    return documents


def get_postgresql_documents() -> set[str]:
    """Get all unique document names from PostgreSQL."""
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT document_id FROM financial_tables")
    documents = {row[0] for row in cursor.fetchall()}

    cursor.close()
    return documents


def validate_consistency() -> dict:
    """
    Validate that both databases have exactly the same documents.

    Returns:
        dict with validation results
    """
    print("=" * 60)
    print("DATABASE CONSISTENCY VALIDATION")
    print("=" * 60)

    # Get documents from both databases
    print("\nFetching Qdrant documents...")
    qdrant_docs = get_qdrant_documents()
    print(f"  Found {len(qdrant_docs)} unique documents in Qdrant")

    print("\nFetching PostgreSQL documents...")
    postgresql_docs = get_postgresql_documents()
    print(f"  Found {len(postgresql_docs)} unique documents in PostgreSQL")

    # Compare
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)

    only_in_qdrant = qdrant_docs - postgresql_docs
    only_in_postgresql = postgresql_docs - qdrant_docs
    common_docs = qdrant_docs & postgresql_docs

    is_consistent = len(only_in_qdrant) == 0 and len(only_in_postgresql) == 0

    if is_consistent:
        print(f"\n✅ CONSISTENT: Both databases have exactly {len(common_docs)} documents")
        print("\nDocuments (sorted):")
        for doc in sorted(common_docs):
            print(f"  • {doc}")
    else:
        print("\n❌ INCONSISTENT: Documents do not match!")

        if only_in_qdrant:
            print(f"\n⚠️  Only in Qdrant ({len(only_in_qdrant)}):")
            for doc in sorted(only_in_qdrant):
                print(f"    - {doc}")

        if only_in_postgresql:
            print(f"\n⚠️  Only in PostgreSQL ({len(only_in_postgresql)}):")
            for doc in sorted(only_in_postgresql):
                print(f"    - {doc}")

        print(f"\n📋 Common documents ({len(common_docs)}):")
        for doc in sorted(common_docs)[:10]:
            print(f"    • {doc}")
        if len(common_docs) > 10:
            print(f"    ... and {len(common_docs) - 10} more")

    return {
        "is_consistent": is_consistent,
        "qdrant_count": len(qdrant_docs),
        "postgresql_count": len(postgresql_docs),
        "common_count": len(common_docs),
        "only_in_qdrant": only_in_qdrant,
        "only_in_postgresql": only_in_postgresql,
        "common_documents": common_docs,
    }


def main() -> int:
    """Main entry point."""
    result = validate_consistency()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Qdrant documents:     {result['qdrant_count']}")
    print(f"PostgreSQL documents: {result['postgresql_count']}")
    print(f"Common documents:     {result['common_count']}")
    print(f"Status: {'✅ PASS' if result['is_consistent'] else '❌ FAIL'}")

    return 0 if result["is_consistent"] else 1


if __name__ == "__main__":
    sys.exit(main())
