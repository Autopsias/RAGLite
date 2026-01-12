"""Unit tests for query-time metadata enrichment.

Story 5.0.6 Task 5.6: Tests for query-time metadata enrichment that adds
metadata to query results without slowing down ingestion.
"""

import asyncio

import pytest

from raglite.retrieval.search import enrich_results_with_metadata
from raglite.shared import config
from raglite.shared.models import ExtractedMetadata, QueryResult


@pytest.mark.asyncio
async def test_enrich_results_with_metadata_success(
    test_settings, mock_mistral_client, monkeypatch
):
    """Test successful metadata enrichment of query results."""

    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", "test-key")

    # Create test results
    results = [
        QueryResult(
            score=0.95,
            text="EBITDA for Portugal Cement in Q3 2025 was 128.8 Meur",
            source_document="Q3_Report.pdf",
            page_number=12,
            chunk_index=45,
            word_count=150,
        ),
        QueryResult(
            score=0.88,
            text="Variable costs decreased to 23.2 EUR/ton in August",
            source_document="Performance_Review.pdf",
            page_number=8,
            chunk_index=23,
            word_count=120,
        ),
    ]

    # Enrich results (metadata extraction will be mocked)
    enriched = await enrich_results_with_metadata(results)

    # Verify results returned (even if metadata not attached to model yet)
    assert len(enriched) == 2
    assert enriched[0].score == 0.95
    assert enriched[1].score == 0.88


@pytest.mark.asyncio
async def test_enrich_results_disabled(test_settings, monkeypatch):
    """Test enrichment is skipped when disabled."""
    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", False)

    results = [
        QueryResult(
            score=0.95,
            text="Test content",
            source_document="test.pdf",
            page_number=1,
            chunk_index=0,
            word_count=50,
        )
    ]

    # Should return unchanged
    enriched = await enrich_results_with_metadata(results)
    assert enriched == results


@pytest.mark.asyncio
async def test_enrich_results_no_api_key(test_settings, monkeypatch):
    """Test graceful degradation when API key missing."""
    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", None)

    results = [
        QueryResult(
            score=0.95,
            text="Test content",
            source_document="test.pdf",
            page_number=1,
            chunk_index=0,
            word_count=50,
        )
    ]

    # Should return unchanged (graceful degradation)
    enriched = await enrich_results_with_metadata(results)
    assert enriched == results


@pytest.mark.asyncio
async def test_enrich_results_timeout(test_settings, mock_mistral_client, monkeypatch):
    """Test timeout handling returns results unchanged."""
    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", "test-key")

    # Mock extract_chunk_metadata to timeout
    async def slow_extract(*args, **kwargs):
        await asyncio.sleep(5)  # Exceeds 2.5s timeout
        return None

    monkeypatch.setattr(
        "raglite.ingestion.embedding_generation.extract_chunk_metadata", slow_extract
    )

    results = [
        QueryResult(
            score=0.95,
            text="Test content",
            source_document="test.pdf",
            page_number=1,
            chunk_index=0,
            word_count=50,
        )
    ]

    # Should timeout and return unchanged
    enriched = await enrich_results_with_metadata(results)
    assert enriched == results


@pytest.mark.asyncio
async def test_enrich_results_empty_list(test_settings, monkeypatch):
    """Test enrichment with empty results list."""
    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", "test-key")

    # Empty results
    enriched = await enrich_results_with_metadata([])
    assert enriched == []


@pytest.mark.asyncio
async def test_enrich_results_partial_failure(test_settings, mock_mistral_client, monkeypatch):
    """Test enrichment continues when some results fail."""
    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", "test-key")

    # Mock extract_chunk_metadata to fail for first result
    call_count = 0

    async def failing_extract(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Extraction failed")
        # Return mock metadata for other calls
        return ExtractedMetadata(
            company_name="Test Corp",
            metric_category="Revenue",
            reporting_period="Q3 2025",
        )

    monkeypatch.setattr(
        "raglite.ingestion.embedding_generation.extract_chunk_metadata", failing_extract
    )

    results = [
        QueryResult(
            score=0.95,
            text="First result",
            source_document="test1.pdf",
            page_number=1,
            chunk_index=0,
            word_count=50,
        ),
        QueryResult(
            score=0.88,
            text="Second result",
            source_document="test2.pdf",
            page_number=2,
            chunk_index=1,
            word_count=60,
        ),
    ]

    # Should handle partial failure gracefully
    enriched = await enrich_results_with_metadata(results)
    assert len(enriched) == 2
    assert enriched[0].score == 0.95  # Unchanged despite failure
    assert enriched[1].score == 0.88


@pytest.mark.asyncio
@pytest.mark.priority("P0")
async def test_enrich_results_attaches_metadata(test_settings, mock_mistral_client, monkeypatch):
    """Test that enrich_results_with_metadata attaches metadata to QueryResult objects.

    Story 5.0.6 AC5 Fix: Verify metadata field is populated after enrichment.
    """
    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", "test-key")

    # Mock extract_chunk_metadata to return test metadata
    async def mock_extract(*args, **kwargs):
        return ExtractedMetadata(
            company_name="ACME Corp",
            reporting_period="Q4 2025",
            metric_category="EBITDA",
            document_type="Income Statement",
            section_type="Table",
        )

    monkeypatch.setattr(
        "raglite.ingestion.embedding_generation.extract_chunk_metadata", mock_extract
    )

    # Create test results without metadata
    results = [
        QueryResult(
            score=0.95,
            text="EBITDA increased by 15% in Q4 2025",
            source_document="quarterly_report.pdf",
            page_number=5,
            chunk_index=10,
            word_count=50,
        ),
        QueryResult(
            score=0.88,
            text="Revenue growth exceeded expectations",
            source_document="quarterly_report.pdf",
            page_number=3,
            chunk_index=5,
            word_count=45,
        ),
    ]

    # Verify metadata is None before enrichment
    assert results[0].metadata is None
    assert results[1].metadata is None

    # Enrich results
    enriched = await enrich_results_with_metadata(results)

    # Verify metadata is attached after enrichment
    assert len(enriched) == 2

    # First result should have metadata attached
    assert enriched[0].metadata is not None
    assert enriched[0].metadata.company_name == "ACME Corp"
    assert enriched[0].metadata.reporting_period == "Q4 2025"
    assert enriched[0].metadata.metric_category == "EBITDA"
    assert enriched[0].metadata.document_type == "Income Statement"
    assert enriched[0].metadata.section_type == "Table"

    # Second result should also have metadata attached
    assert enriched[1].metadata is not None
    assert enriched[1].metadata.company_name == "ACME Corp"
    assert enriched[1].metadata.reporting_period == "Q4 2025"

    # Original result fields should be unchanged
    assert enriched[0].score == 0.95
    assert enriched[0].text == "EBITDA increased by 15% in Q4 2025"
    assert enriched[0].source_document == "quarterly_report.pdf"
