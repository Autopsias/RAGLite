"""Quick smoke test for async ingestion (Story 4.0.3)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.main import get_ingestion_status, ingest_financial_document_async


async def test_async_ingestion():
    """Test async ingestion workflow."""
    print("Testing async ingestion...")

    # Start async ingestion
    resp = await ingest_financial_document_async.fn("tests/fixtures/sample-small-3-pages.pdf")
    print(f"✅ Job ID: {resp.job_id}")
    print(f"   Message: {resp.message}")

    # Check initial status
    status = await get_ingestion_status.fn(resp.job_id)
    print(f"✅ Initial Status: {status.status}")

    # Poll until complete
    while status.status not in ["completed", "failed"]:
        await asyncio.sleep(1)
        status = await get_ingestion_status.fn(resp.job_id)
        print(f"   Status: {status.status}, Progress: {status.progress}%")

    if status.status == "completed":
        print("✅ Ingestion COMPLETE")
        print(f"   Chunks: {status.result.chunk_count}")
        print(f"   Pages: {status.result.page_count}")
    else:
        print(f"❌ Ingestion FAILED: {status.error}")


if __name__ == "__main__":
    asyncio.run(test_async_ingestion())
