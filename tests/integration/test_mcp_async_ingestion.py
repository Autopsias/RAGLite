"""Integration tests for async MCP document ingestion (Story 4.0.3 AC3, AC5).

Tests:
1. Sync ingestion completes within timeout for small PDFs
2. Async ingestion workflow: start → poll → complete
3. End-to-end: async ingest → query validation
"""

import asyncio
from pathlib import Path

import pytest

from raglite.main import (
    get_ingestion_status,
    ingest_financial_document,
    ingest_financial_document_async,
    query_financial_documents,
)
from raglite.shared.models import QueryRequest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_sync_ingestion_small_pdf_no_timeout():
    """Test AC1: Small PDF ingestion completes within MCP timeout (60-120s).

    Story 4.0.3 AC1: PDF ingestion completes within MCP timeout for typical documents.
    Test with 4-page PDF: <30s ingestion time (well within 60s timeout).
    """
    print("\n" + "=" * 80)
    print("TEST: Sync Ingestion - Small PDF (4 pages) - No Timeout")
    print("=" * 80)

    # Use small test fixture (4 pages, 228 KB)
    test_pdf = Path("tests/fixtures/sample-small-3-pages.pdf")
    assert test_pdf.exists(), f"Test fixture not found: {test_pdf}"

    print(f"Test PDF: {test_pdf.name}")
    print(f"Size: {test_pdf.stat().st_size / 1024:.1f} KB")
    print()

    try:
        # Measure ingestion time
        import time

        start_time = time.perf_counter()
        # Use .fn to access underlying async function (FastMCP FunctionTool wrapper)
        metadata = await ingest_financial_document.fn(str(test_pdf))
        duration_s = time.perf_counter() - start_time

        print(f"✅ Ingestion COMPLETED in {duration_s:.2f}s")
        print(f"   Document: {metadata.filename}")
        print(f"   Pages: {metadata.page_count}")
        print(f"   Chunks: {metadata.chunk_count}")
        print(f"   Doc Type: {metadata.doc_type}")
        print()

        # AC1 validation: <30s for 10-page PDF, <90s for 30-page PDF
        # Our 4-page PDF should complete in <30s
        assert duration_s < 30, f"Ingestion took {duration_s:.2f}s, expected <30s for 4-page PDF"

        # Validate metadata
        assert metadata.page_count == 4, f"Expected 4 pages, got {metadata.page_count}"
        assert metadata.chunk_count > 0, "No chunks created"
        assert metadata.doc_type == "PDF"

        print("✅ AC1 VALIDATION PASSED: Small PDF ingestion within timeout")
        print()

        return True

    except Exception as e:
        print(f"❌ Sync ingestion failed: {e}")
        import traceback

        traceback.print_exc()
        pytest.fail(f"Sync ingestion failed: {e}")


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_async_ingestion_workflow():
    """Test AC5: Async ingestion workflow (start → poll → complete).

    Story 4.0.3 AC5: Async ingestion for large documents.
    - Immediate response with job ID
    - Status polling returns job status
    - Job completes successfully
    """
    print("\n" + "=" * 80)
    print("TEST: Async Ingestion Workflow - Start → Poll → Complete")
    print("=" * 80)

    # Use small test fixture for fast test (simulates async pattern)
    test_pdf = Path("tests/fixtures/sample-small-3-pages.pdf")
    assert test_pdf.exists(), f"Test fixture not found: {test_pdf}"

    print(f"Test PDF: {test_pdf.name}")
    print(f"Size: {test_pdf.stat().st_size / 1024:.1f} KB")
    print()

    try:
        # Step 1: Start async ingestion
        print("Step 1: Starting async ingestion...")
        response = await ingest_financial_document_async.fn(str(test_pdf))

        print("✅ Job started successfully")
        print(f"   Job ID: {response.job_id}")
        print(f"   Status: {response.status}")
        print(f"   Message: {response.message}")
        print()

        # Validate immediate response
        assert response.job_id is not None, "No job ID returned"
        assert response.status == "started", f"Expected status='started', got '{response.status}'"
        assert "get_ingestion_status" in response.message.lower(), (
            "Message missing polling instructions"
        )

        # Step 2: Poll status until complete
        print("Step 2: Polling job status...")
        max_polls = 60  # Max 1 minute polling (1s intervals)
        poll_count = 0

        while poll_count < max_polls:
            poll_count += 1
            status = await get_ingestion_status.fn(response.job_id)

            print(f"   Poll {poll_count}: status={status.status}, progress={status.progress}%")

            if status.status in ["completed", "failed"]:
                break

            await asyncio.sleep(1)  # 1-second polling interval for testing

        # Validate completion
        assert status.status == "completed", f"Job failed: {status.error}"
        assert status.result is not None, "No result metadata in completed job"
        assert status.progress == 100, f"Expected progress=100, got {status.progress}"
        assert status.completed_at is not None, "No completion timestamp"

        print()
        print(f"✅ Job COMPLETED after {poll_count} polls")
        print(f"   Document: {status.result.filename}")
        print(f"   Pages: {status.result.page_count}")
        print(f"   Chunks: {status.result.chunk_count}")
        print(f"   Started: {status.started_at}")
        print(f"   Completed: {status.completed_at}")
        print()

        print("✅ AC5 VALIDATION PASSED: Async ingestion workflow complete")
        print()

        return True

    except Exception as e:
        print(f"❌ Async ingestion workflow failed: {e}")
        import traceback

        traceback.print_exc()
        pytest.fail(f"Async ingestion workflow failed: {e}")


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_async_ingestion_end_to_end_with_query():
    """Test AC3: Integration test validates MCP ingestion → query flow without timeout.

    Story 4.0.3 AC3: End-to-end test: ingest via MCP, verify chunks stored, query via MCP.
    """
    print("\n" + "=" * 80)
    print("TEST: End-to-End - Async Ingest → Query Validation")
    print("=" * 80)

    # Use small test fixture
    test_pdf = Path("tests/fixtures/sample-small-3-pages.pdf")
    assert test_pdf.exists(), f"Test fixture not found: {test_pdf}"

    print(f"Test PDF: {test_pdf.name}")
    print()

    try:
        # Step 1: Async ingestion
        print("Step 1: Starting async ingestion...")
        response = await ingest_financial_document_async.fn(str(test_pdf))
        job_id = response.job_id
        print(f"✅ Job ID: {job_id}")
        print()

        # Step 2: Poll until complete
        print("Step 2: Polling until complete...")
        max_polls = 60
        poll_count = 0

        while poll_count < max_polls:
            poll_count += 1
            status = await get_ingestion_status.fn(job_id)

            if status.status in ["completed", "failed"]:
                break

            await asyncio.sleep(1)

        assert status.status == "completed", f"Ingestion failed: {status.error}"
        print(f"✅ Ingestion completed ({status.result.chunk_count} chunks)")
        print()

        # Step 3: Query the ingested document
        print("Step 3: Querying ingested document...")
        query_request = QueryRequest(
            query="What are the key financial metrics?",
            top_k=5,
        )
        query_response = await query_financial_documents.fn(query_request)

        print(f"✅ Query returned {len(query_response.results)} results")
        print()

        # Validate query results
        assert len(query_response.results) > 0, "No query results returned"
        assert query_response.retrieval_time_ms > 0, (
            f"Invalid retrieval time: {query_response.retrieval_time_ms}"
        )

        # Validate results come from our ingested document
        for i, result in enumerate(query_response.results[:3], 1):
            print(f"Result {i}:")
            print(f"   Score: {result.score:.4f}")
            print(f"   Source: {result.source_document}")
            print(f"   Page: {result.page_number}")
            print(f"   Text: {result.text[:100]}...")
            print()

            # Validate result came from our document
            assert test_pdf.name in result.source_document, (
                f"Result not from our document: {result.source_document}"
            )

        print("✅ AC3 VALIDATION PASSED: End-to-end async ingest → query flow")
        print()

        return True

    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback

        traceback.print_exc()
        pytest.fail(f"End-to-end test failed: {e}")


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_async_ingestion_invalid_file():
    """Test error handling: async ingestion with non-existent file."""
    print("\n" + "=" * 80)
    print("TEST: Async Ingestion Error Handling - Invalid File")
    print("=" * 80)

    invalid_path = "tests/fixtures/nonexistent-file.pdf"

    try:
        # Should raise DocumentProcessingError before creating job
        from raglite.main import DocumentProcessingError

        with pytest.raises(DocumentProcessingError, match="Document not found"):
            await ingest_financial_document_async.fn(invalid_path)

        print("✅ Error handling PASSED: Invalid file rejected before job creation")
        print()

        return True

    except AssertionError:
        raise  # Re-raise pytest assertion failures
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        pytest.fail(f"Error handling test failed: {e}")


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_get_ingestion_status_invalid_job_id():
    """Test error handling: status check with invalid job ID."""
    print("\n" + "=" * 80)
    print("TEST: Status Check Error Handling - Invalid Job ID")
    print("=" * 80)

    invalid_job_id = "00000000-0000-0000-0000-000000000000"

    try:
        # Should raise ValueError for non-existent job
        with pytest.raises(ValueError, match="Job not found"):
            await get_ingestion_status.fn(invalid_job_id)

        print("✅ Error handling PASSED: Invalid job ID rejected")
        print()

        return True

    except AssertionError:
        raise  # Re-raise pytest assertion failures
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        pytest.fail(f"Error handling test failed: {e}")
