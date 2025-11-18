#!/usr/bin/env python3
"""Ingest PDF for NFR Accuracy Validation workflow.

This script is specifically designed for the GitHub Actions workflow
to ingest the full 160-page PDF into both Qdrant and PostgreSQL when
the cache misses.

Usage:
    python scripts/ingest-for-validation.py

Requirements:
    - Qdrant running at localhost:6333
    - PostgreSQL running at localhost:5432
    - Environment variables set (POSTGRES_HOST, POSTGRES_PORT, etc.)
"""

import asyncio
import sys
from pathlib import Path

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings


async def main() -> None:
    """Ingest full 160-page PDF for accuracy validation."""
    print("=" * 80)
    print("NFR Accuracy Validation - Full PDF Ingestion")
    print("=" * 80)
    print()

    # Full PDF path (relative to repo root)
    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    if not pdf_path.exists():
        print(f"❌ Error: PDF not found: {pdf_path}")
        print(f"   Current working directory: {Path.cwd()}")
        sys.exit(1)

    print(f"📄 Source: {pdf_path}")
    print(f"📦 Collection: {settings.qdrant_collection_name}")
    print(f"🗄️  PostgreSQL: {settings.postgres_db}")
    print()
    print("Expected:")
    print("  - ~180-220 chunks (512-token fixed chunking)")
    print("  - ~13-15 minutes processing time")
    print("  - Qdrant: Vector embeddings + metadata")
    print("  - PostgreSQL: Structured chunks + tables")
    print("=" * 80)
    print()

    # Verify Qdrant connection before ingestion
    try:
        _ = get_qdrant_client()  # Just verify connection
        print("✅ Qdrant connection verified")
    except Exception as e:
        print(f"❌ Error connecting to Qdrant: {e}")
        sys.exit(1)

    print()
    print(f"🚀 Starting ingestion of {pdf_path.name} (160 pages)...")
    print(f"   Collection will be cleared and recreated: {settings.qdrant_collection_name}")
    print("   This will take ~13-15 minutes...")
    print()

    try:
        # Run full ingestion pipeline
        await ingest_pdf(str(pdf_path))

        print()
        print("=" * 80)
        print("✅ SUCCESS: Ingestion completed")
        print("=" * 80)
        print()
        print("Next Steps:")
        print("  1. Run accuracy validation: python scripts/validate-epic-2-final.py")
        print("  2. Check NFR6 (≥70% retrieval accuracy)")
        print("  3. Check NFR7 (≥95% source attribution accuracy)")
        print()
        print("Caching:")
        print("  - .qdrant-export/ → Qdrant snapshot")
        print("  - .postgres-export/ → PostgreSQL snapshot")
        print("  - These will be cached for future runs")
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR: Ingestion failed")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("  - Check Qdrant is running: docker ps | grep qdrant")
        print("  - Check PostgreSQL is running: docker ps | grep postgres")
        print("  - Check environment variables are set")
        print("  - Check PDF file exists and is readable")
        print()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
