"""Unit tests for vector similarity search and retrieval.

Tests the generate_query_embedding and search_documents functions with mocked dependencies.
"""

import pytest

from raglite.retrieval.attribution import CitationError, generate_citations
from raglite.shared.models import QueryResult

pytestmark = [pytest.mark.unit]


class TestGenerateCitations:
    """Test suite for citation generation and source attribution."""

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_generate_citations_basic(self):
        """Test that single QueryResult gets citation appended to text.

        Verifies basic citation generation with correct format.
        """
        results = [
            QueryResult(
                score=0.87,
                text="Q3 revenue was $50M, up 20% YoY.",
                source_document="Q3_Report.pdf",
                page_number=5,
                chunk_index=0,
                word_count=8,
            )
        ]

        cited_results = await generate_citations(results)

        # Assertions
        assert len(cited_results) == 1
        assert "(Source: Q3_Report.pdf, page 5, chunk 0)" in cited_results[0].text
        assert cited_results[0].text.startswith("Q3 revenue was $50M")
        assert cited_results[0].text.endswith("(Source: Q3_Report.pdf, page 5, chunk 0)")

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_generate_citations_multi_source(self):
        """Test that multiple QueryResult objects get unique citations.

        Verifies that each chunk from different sources gets its own citation.
        """
        results = [
            QueryResult(
                score=0.87,
                text="Q3 revenue was $50M.",
                source_document="Q3_Report.pdf",
                page_number=5,
                chunk_index=0,
                word_count=5,
            ),
            QueryResult(
                score=0.75,
                text="Annual revenue is $180M.",
                source_document="Annual_Report.pdf",
                page_number=12,
                chunk_index=1,
                word_count=4,
            ),
            QueryResult(
                score=0.65,
                text="Operating expenses grew 10%.",
                source_document="Q3_Report.pdf",
                page_number=8,
                chunk_index=2,
                word_count=4,
            ),
        ]

        cited_results = await generate_citations(results)

        # Assertions - verify unique citations
        assert len(cited_results) == 3
        assert "(Source: Q3_Report.pdf, page 5, chunk 0)" in cited_results[0].text
        assert "(Source: Annual_Report.pdf, page 12, chunk 1)" in cited_results[1].text
        assert "(Source: Q3_Report.pdf, page 8, chunk 2)" in cited_results[2].text

        # Verify ordering preserved (highest score first)
        assert cited_results[0].score == 0.87
        assert cited_results[1].score == 0.75
        assert cited_results[2].score == 0.65

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_citation_format(self):
        """Test that citation format matches specification.

        Verifies format: "(Source: document.pdf, page 12, chunk 5)"
        """
        result = QueryResult(
            score=0.90,
            text="Test content",
            source_document="Financial_Report.pdf",
            page_number=42,
            chunk_index=17,
            word_count=2,
        )

        cited_results = await generate_citations([result])

        # Verify exact format
        expected_citation = "(Source: Financial_Report.pdf, page 42, chunk 17)"
        assert expected_citation in cited_results[0].text

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_missing_page_number(self):
        """Test graceful degradation when page_number is None.

        Verifies that warning is logged and citation uses 'N/A' for page.
        """
        result = QueryResult(
            score=0.80,
            text="Content without page number",
            source_document="report.pdf",
            page_number=None,  # Missing!
            chunk_index=0,
            word_count=4,
        )

        # Should not raise error (graceful degradation)
        cited_results = await generate_citations([result])

        # Verify citation uses 'N/A' for missing page
        assert len(cited_results) == 1
        assert "(Source: report.pdf, page N/A, chunk 0)" in cited_results[0].text

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_missing_source_document(self):
        """Test that CitationError is raised when source_document is missing.

        Verifies critical field validation (source_document required).
        """
        result = QueryResult(
            score=0.80,
            text="Content",
            source_document="",  # Empty! Critical field
            page_number=5,
            chunk_index=0,
            word_count=1,
        )

        # Should raise CitationError
        with pytest.raises(CitationError, match="Missing source_document for chunk 0"):
            await generate_citations([result])

        # Test with whitespace-only source_document
        result.source_document = "   "
        with pytest.raises(CitationError, match="Missing source_document"):
            await generate_citations([result])

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_citation_appended_to_text(self):
        """Test that original chunk text is preserved and citation appended.

        Verifies that citation doesn't replace text, but appends with newlines.
        """
        original_text = "Q3 revenue increased by 15% compared to Q2."
        result = QueryResult(
            score=0.85,
            text=original_text,
            source_document="Q3_Report.pdf",
            page_number=7,
            chunk_index=3,
            word_count=8,
        )

        cited_results = await generate_citations([result])

        # Verify original text preserved
        assert cited_results[0].text.startswith(original_text)

        # Verify citation appended with double newline
        assert "\n\n(Source:" in cited_results[0].text
        assert cited_results[0].text.count("\n\n") == 1  # Exactly one double newline

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_empty_results_list(self):
        """Test that empty results list is handled gracefully.

        Verifies no error when no results to cite.
        """
        cited_results = await generate_citations([])

        # Should return empty list
        assert cited_results == []
        assert len(cited_results) == 0

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_citation_ordering(self):
        """Test that citations match QueryResult order.

        Verifies that citation order follows result order (highest score first).
        """
        results = [
            QueryResult(
                score=0.95,
                text="Highest relevance chunk",
                source_document="report.pdf",
                page_number=1,
                chunk_index=0,
                word_count=3,
            ),
            QueryResult(
                score=0.80,
                text="Medium relevance chunk",
                source_document="report.pdf",
                page_number=2,
                chunk_index=1,
                word_count=3,
            ),
            QueryResult(
                score=0.60,
                text="Lower relevance chunk",
                source_document="report.pdf",
                page_number=3,
                chunk_index=2,
                word_count=3,
            ),
        ]

        cited_results = await generate_citations(results)

        # Verify ordering preserved
        assert cited_results[0].score == 0.95
        assert cited_results[1].score == 0.80
        assert cited_results[2].score == 0.60

        # Verify citations match order
        assert "page 1, chunk 0" in cited_results[0].text
        assert "page 2, chunk 1" in cited_results[1].text
        assert "page 3, chunk 2" in cited_results[2].text
