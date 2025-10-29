"""Test PostgreSQL ↔ Qdrant linking during ingestion (Story 2.6 AC4).

This script tests that metadata is automatically stored in PostgreSQL during document
ingestion with proper linkage to Qdrant vectors via chunk_id (embedding_id).

Usage:
    python scripts/test-ac4-postgresql-linking.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import ingest_pdf  # noqa: E402
from raglite.shared.clients import get_postgresql_connection  # noqa: E402
from raglite.shared.config import Settings  # noqa: E402


async def test_ac4_postgresql_linking():
    """Test that metadata is stored in PostgreSQL during ingestion with Qdrant linkage."""
    settings = Settings()
    test_pdf = Path("docs/sample pdf/test-10-pages.pdf")

    if not test_pdf.exists():
        print(f"❌ ERROR: Test PDF not found: {test_pdf}")
        sys.exit(1)

    if not settings.mistral_api_key:
        print(
            "❌ ERROR: MISTRAL_API_KEY not configured - metadata extraction required for this test"
        )
        sys.exit(1)

    print("=" * 80)
    print("Story 2.6 AC4 - PostgreSQL ↔ Qdrant Linking Test")
    print("=" * 80)
    print()
    print(f"Test PDF: {test_pdf.name}")
    print("Test: Metadata stored in PostgreSQL during ingestion")
    print()

    # Ingest PDF (should store both in Qdrant AND PostgreSQL)
    print("Step 1: Ingesting PDF (with automatic PostgreSQL storage)...")
    metadata = await ingest_pdf(test_pdf)

    print("\n✓ Ingestion complete:")
    print(f"  • Pages: {metadata.page_count}")
    print(f"  • Chunks created: {metadata.chunk_count}")

    # Verify PostgreSQL storage
    print("\nStep 2: Verifying PostgreSQL storage...")
    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Check total records
        cursor.execute("SELECT COUNT(*) FROM financial_chunks")
        total_records = cursor.fetchone()[0]

        # Check records with metadata
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(company_name) as with_company,
                COUNT(metric_category) as with_metric,
                COUNT(section_type) as with_section,
                COUNT(embedding_id) as with_qdrant_link
            FROM financial_chunks
        """
        )
        row = cursor.fetchone()

        cursor.close()

        print("\n✓ PostgreSQL verification:")
        print(f"  • Total records: {row[0]}")
        print(f"  • With company_name: {row[1]} ({row[1] / row[0] * 100:.1f}%)")
        print(f"  • With metric_category: {row[2]} ({row[2] / row[0] * 100:.1f}%)")
        print(f"  • With section_type: {row[3]} ({row[3] / row[0] * 100:.1f}%)")
        print(f"  • With Qdrant link (embedding_id): {row[4]} ({row[4] / row[0] * 100:.1f}%)")

        # AC4 SUCCESS CRITERIA: 100% of chunks have PostgreSQL metadata records linked to Qdrant vectors
        print("\n" + "=" * 80)
        print("AC4 SUCCESS CRITERIA VALIDATION")
        print("=" * 80)

        if total_records >= metadata.chunk_count:
            print(
                f"✅ PASS - PostgreSQL has {total_records} records (>= {metadata.chunk_count} chunks)"
            )
        else:
            print(
                f"❌ FAIL - PostgreSQL has only {total_records} records (expected {metadata.chunk_count})"
            )

        if row[4] == total_records:
            print("✅ PASS - 100% of records linked to Qdrant (embedding_id)")
        else:
            print(f"❌ FAIL - Only {row[4] / total_records * 100:.1f}% linked to Qdrant")

        metadata_coverage = (row[1] + row[2] + row[3]) / (total_records * 3) * 100
        print(f"\n📊 Metadata coverage: {metadata_coverage:.1f}% (avg across 3 key fields)")

    except Exception as e:
        print(f"\n❌ ERROR: PostgreSQL verification failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_ac4_postgresql_linking())
