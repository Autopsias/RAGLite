#!/usr/bin/env python
"""Setup script to pre-ingest test data for integration tests.

Run this script ONCE before running integration tests to avoid waiting
60-90 seconds for PDF ingestion on every test session.

Usage:
    python tests/integration/setup_test_data.py

Then run tests normally:
    pytest tests/integration/
"""

import asyncio
from pathlib import Path

from qdrant_client.models import Distance, VectorParams

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings


async def main():
    """Ingest Performance Review PDF into Qdrant for testing."""
    print("=" * 70)
    print("RAGLite Integration Test Data Setup")
    print("=" * 70)

    # Locate Performance Review PDF
    full_pdf = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    if not full_pdf.exists():
        print("\n❌ ERROR: Performance Review PDF not found at:")
        print(f"   {full_pdf.absolute()}")
        print("\n   Integration tests will use sample PDF with lower accuracy.")
        return 1

    print(f"\n✓ Found PDF: {full_pdf}")
    print(f"  Size: {full_pdf.stat().st_size / 1024 / 1024:.1f} MB")

    # Setup Qdrant collection
    qdrant = get_qdrant_client()
    collections = [c.name for c in qdrant.get_collections().collections]

    if settings.qdrant_collection_name in collections:
        count = qdrant.count(collection_name=settings.qdrant_collection_name)
        print(
            f"\n✓ Collection '{settings.qdrant_collection_name}' exists with {count.count} chunks"
        )

        # Check if it's the right document
        if count.count > 0:
            sample = qdrant.scroll(
                collection_name=settings.qdrant_collection_name, limit=1, with_payload=True
            )
            doc = sample[0][0].payload.get("source_document", "") if sample[0] else ""

            if "Performance Review" in doc:
                print("  ✓ Already contains Performance Review data")
                print("\n✅ Setup complete - integration tests ready to run!")
                return 0
            else:
                print(f"  ⚠️  Contains wrong document: {doc}")
                print("  Clearing and re-ingesting...")
                qdrant.delete_collection(collection_name=settings.qdrant_collection_name)

    # Create collection if needed
    if settings.qdrant_collection_name not in collections:
        print(f"\n⚙️  Creating collection '{settings.qdrant_collection_name}'...")
        qdrant.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
        print("  ✓ Collection created")
    else:
        print(f"\n✓ Collection '{settings.qdrant_collection_name}' ready")

    # Ingest PDF
    print(f"\n⚙️  Ingesting {full_pdf.name}...")
    print("  This will take 60-90 seconds for 160 pages...")
    print("  Progress indicators:")

    result = await ingest_pdf(str(full_pdf))

    # Verify
    count_after = qdrant.count(collection_name=settings.qdrant_collection_name)

    print("\n✅ Ingestion complete!")
    print(f"  Pages ingested: {result.page_count}")
    print(f"  Chunks created: {count_after.count}")
    print(f"  Avg chunks/page: {count_after.count / result.page_count:.1f}")
    print("\n✅ Setup complete - integration tests ready to run!")
    print("\nYou can now run:")
    print("  pytest tests/integration/test_epic2_regression.py -v")
    print("  pytest tests/integration/test_e2e_query_validation.py -v")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
