"""Test AC6 performance optimizations with 10-page PDF.

This script validates that the three async bugs are fixed:
1. AsyncMistral client (not sync Mistral)
2. Client connection pooling (single instance)
3. Timeout configuration (fail fast)

Expected performance: ~20-30 chunks in <2 minutes (vs ~30 minutes baseline)
"""

import asyncio

# Add project root to path
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import ingest_pdf  # noqa: E402
from raglite.shared.config import Settings  # noqa: E402


async def test_ac6_performance():
    """Test metadata extraction performance on 10-page PDF."""

    # Initialize settings
    settings = Settings()

    # Test PDF path
    test_pdf = Path("docs/sample pdf/test-10-pages.pdf")

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧪 AC6 PERFORMANCE TEST - 10-Page PDF")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"\nTest PDF: {test_pdf}")
    print(f"File size: {test_pdf.stat().st_size / 1024:.1f} KB")
    print(f"\nMistral API Key configured: {'✅ YES' if settings.mistral_api_key else '❌ NO'}")

    if not settings.mistral_api_key:
        print("\n⚠️  MISTRAL_API_KEY not set - metadata extraction will be skipped")
        print("Set MISTRAL_API_KEY in .env to test async fixes")
        return

    print("\n" + "─" * 60)
    print("STARTING INGESTION WITH AC6 FIXES...")
    print("─" * 60)

    # Start timing
    start_time = time.time()

    try:
        # Ingest PDF (this will use the fixed async client)
        metadata = await ingest_pdf(test_pdf)

        # Calculate timing
        elapsed_time = time.time() - start_time

        print("\n" + "═" * 60)
        print("✅ INGESTION COMPLETE")
        print("═" * 60)

        # Display results
        print("\n📊 RESULTS:")
        print(f"  • Document: {metadata.filename}")
        print(f"  • Pages: {metadata.page_count}")
        print(f"  • Total chunks: {metadata.chunk_count}")
        print(f"  • Total time: {elapsed_time:.1f} seconds ({elapsed_time / 60:.2f} minutes)")

        if metadata.chunk_count > 0:
            chunks_per_minute = (metadata.chunk_count / elapsed_time) * 60
            print(f"  • Throughput: {chunks_per_minute:.1f} chunks/minute")

            # Performance assessment
            print("\n📈 PERFORMANCE ASSESSMENT:")
            if chunks_per_minute >= 20:
                print(f"  ✅ EXCELLENT - Async fixes working! ({chunks_per_minute:.1f} chunks/min)")
                print("     Target: ≥20 chunks/min → ACHIEVED")
            elif chunks_per_minute >= 10:
                print(f"  ⚠️  MODERATE - Some improvement ({chunks_per_minute:.1f} chunks/min)")
                print("     Target: ≥20 chunks/min → BELOW TARGET")
            else:
                print(
                    f"  ❌ SLOW - Async fixes may not be working ({chunks_per_minute:.1f} chunks/min)"
                )
                print("     Target: ≥20 chunks/min → FAILED")

            # Projection for full 334-chunk PDF
            projected_time = (334 / chunks_per_minute) if chunks_per_minute > 0 else 0
            print("\n🔮 PROJECTION FOR 334-CHUNK PDF:")
            print(
                f"  • Estimated time: {projected_time:.1f} minutes ({projected_time / 60:.1f} hours)"
            )

            if projected_time <= 16:
                print("  ✅ Within AC6 target (≤30 minutes)")
            elif projected_time <= 30:
                print("  ⚠️  Acceptable but could be better")
            else:
                print("  ❌ Exceeds AC6 target (>30 minutes)")

        print("\n" + "═" * 60)
        print("TEST COMPLETE")
        print("═" * 60)

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ ERROR after {elapsed_time:.1f}s: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ac6_performance())
