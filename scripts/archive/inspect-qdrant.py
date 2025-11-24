#!/usr/bin/env python3
"""Inspect and clean Qdrant vector database."""

import sys
from pathlib import Path

# Add parent directory to path to import raglite modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient  # noqa: E402

from raglite.shared.config import settings  # noqa: E402


def inspect_qdrant():
    """Inspect current Qdrant database state."""
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    print("=" * 60)
    print("QDRANT DATABASE INSPECTION")
    print("=" * 60)

    # List all collections
    collections = client.get_collections().collections
    print(f"\n📚 Total Collections: {len(collections)}")

    for collection in collections:
        print(f"\n📁 Collection: {collection.name}")

        # Get collection info
        info = client.get_collection(collection.name)
        print(f"   - Vectors: {info.vectors_count}")
        print(f"   - Points: {info.points_count}")

        # Sample a few points to see what's in there
        if info.points_count > 0:
            sample = client.scroll(
                collection_name=collection.name, limit=3, with_payload=True, with_vectors=False
            )

            print("   - Sample documents:")
            for point in sample[0]:
                payload = point.payload
                doc_id = payload.get("document_id", "unknown")
                page_num = payload.get("page_number", "?")
                chunk_id = payload.get("chunk_id", "?")
                text_preview = payload.get("text", "")[:100]
                print(f"      • {doc_id} (page {page_num}, chunk {chunk_id})")
                print(f"        Text: {text_preview}...")


def clean_qdrant():
    """Clean/reset Qdrant database by deleting all collections."""
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    print("\n" + "=" * 60)
    print("CLEANING QDRANT DATABASE")
    print("=" * 60)

    collections = client.get_collections().collections

    if not collections:
        print("\n✅ Database is already empty!")
        return

    print(f"\n⚠️  Found {len(collections)} collection(s) to delete:")
    for collection in collections:
        print(f"   - {collection.name}")

    confirm = input("\n❓ Delete all collections? (yes/no): ").strip().lower()

    if confirm == "yes":
        for collection in collections:
            print(f"   🗑️  Deleting {collection.name}...")
            client.delete_collection(collection.name)
        print("\n✅ All collections deleted!")
    else:
        print("\n❌ Cleanup cancelled.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Inspect and clean Qdrant database")
    parser.add_argument(
        "--clean", action="store_true", help="Clean the database (requires confirmation)"
    )

    args = parser.parse_args()

    if args.clean:
        inspect_qdrant()  # Show what will be deleted
        clean_qdrant()
    else:
        inspect_qdrant()
