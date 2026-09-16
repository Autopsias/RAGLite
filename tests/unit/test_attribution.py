"""Unit tests for source attribution and citation generation (raglite/retrieval/attribution.py).

Test Coverage:
    - Citation generation for query results
    - Citation format validation
    - Error handling (missing metadata)
    - Edge cases (empty results, missing page numbers)
    - NFR7 validation (95%+ attribution accuracy)

Priority: P0 (Critical - NFR7 depends on accurate citations)
"""

import pytest

from raglite.retrieval.attribution import CitationError, generate_citations
from tests.support.factories import create_query_result, create_query_results


class TestCitationGeneration:
    """Test citation generation for query results."""

    @pytest.mark.unit
    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_generate_citations_adds_formatted_citation(self):
        """Generate citations - should append formatted citation to text."""
        # GIVEN: Query result with metadata
        result = create_query_result(
            text="Q3 revenue was $50M, up 20% YoY",
            source_document="Q3_2024_Report.pdf",
            page_number=12,
            chunk_index=5,
        )

        # WHEN: Generating citations
        cited_results = await generate_citations([result])

        # THEN: Citation appended to text
        assert len(cited_results) == 1
        assert cited_results[0].text.startswith("Q3 revenue was $50M, up 20% YoY\n\n")
        assert "(Source: Q3_2024_Report.pdf, page 12, chunk 5)" in cited_results[0].text

    @pytest.mark.unit
    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_generate_citations_preserves_original_text(self):
        """Generate citations - should preserve original text before citation."""
        # GIVEN: Query result
        original_text = "EBITDA margin improved to 25% from 20%"
        result = create_query_result(text=original_text)

        # WHEN: Generating citations
        cited_results = await generate_citations([result])

        # THEN: Original text preserved
        assert cited_results[0].text.startswith(original_text)
        assert original_text in cited_results[0].text

    @pytest.mark.unit
    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_generate_citations_multiple_results(self):
        """Generate citations for multiple results - each gets unique citation."""
        # GIVEN: Multiple query results from different sources
        results = [
            create_query_result(source_document="Report_A.pdf", page_number=10, chunk_index=1),
            create_query_result(source_document="Report_B.pdf", page_number=25, chunk_index=3),
            create_query_result(source_document="Report_A.pdf", page_number=11, chunk_index=2),
        ]

        # WHEN: Generating citations
        cited_results = await generate_citations(results)

        # THEN: Each result has unique citation
        assert len(cited_results) == 3
        assert "(Source: Report_A.pdf, page 10, chunk 1)" in cited_results[0].text
        assert "(Source: Report_B.pdf, page 25, chunk 3)" in cited_results[1].text
        assert "(Source: Report_A.pdf, page 11, chunk 2)" in cited_results[2].text

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_generate_citations_empty_results_returns_empty(self):
        """Generate citations for empty results - should return empty list."""
        # GIVEN: Empty results list
        results = []

        # WHEN: Generating citations
        cited_results = await generate_citations(results)

        # THEN: Empty list returned
        assert cited_results == []

    @pytest.mark.unit
    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_generate_citations_missing_page_number_shows_na(self):
        """Generate citations with missing page number - should show 'N/A'."""
        # GIVEN: Result with None page_number
        result = create_query_result(
            source_document="Report.pdf",
            page_number=None,  # Missing page number
            chunk_index=7,
        )

        # WHEN: Generating citations
        cited_results = await generate_citations([result])

        # THEN: Citation shows 'page N/A'
        assert "(Source: Report.pdf, page N/A, chunk 7)" in cited_results[0].text


class TestCitationErrorHandling:
    """Test error handling for missing metadata."""

    @pytest.mark.unit
    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_generate_citations_missing_source_document_raises_error(self):
        """Generate citations with missing source_document - should raise CitationError."""
        # GIVEN: Result with missing source_document
        result = create_query_result(
            source_document="",  # Empty source document (critical metadata)
            page_number=10,
            chunk_index=5,
        )

        # WHEN/THEN: Generating citations raises CitationError
        with pytest.raises(CitationError, match="Missing source_document for chunk 5"):
            await generate_citations([result])

    @pytest.mark.unit
    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_generate_citations_whitespace_source_document_raises_error(self):
        """Generate citations with whitespace-only source_document - should raise CitationError."""
        # GIVEN: Result with whitespace source_document
        result = create_query_result(
            source_document="   ",  # Whitespace only
            chunk_index=3,
        )

        # WHEN/THEN: Generating citations raises CitationError
        with pytest.raises(CitationError, match="Missing source_document for chunk 3"):
            await generate_citations([result])

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_citation_error_is_exception(self):
        """Verify CitationError is an Exception."""
        # GIVEN/WHEN: Creating exception
        error = CitationError("Test error")

        # THEN: Is Exception subclass
        assert isinstance(error, Exception)
        assert str(error) == "Test error"


class TestCitationFormat:
    """Test citation format compliance."""

    @pytest.mark.unit
    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_citation_format_matches_specification(self):
        """Citation format should match spec: (Source: doc, page N, chunk M)."""
        # GIVEN: Result with known metadata
        result = create_query_result(
            text="Test content",
            source_document="Financial_Report_2024.pdf",
            page_number=42,
            chunk_index=15,
        )

        # WHEN: Generating citation
        cited_results = await generate_citations([result])

        # THEN: Format matches specification exactly
        expected_citation = "(Source: Financial_Report_2024.pdf, page 42, chunk 15)"
        assert expected_citation in cited_results[0].text

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_citation_separated_by_double_newline(self):
        """Citation should be separated from text by double newline."""
        # GIVEN: Result with text
        result = create_query_result(text="Original content here")

        # WHEN: Generating citation
        cited_results = await generate_citations([result])

        # THEN: Double newline separates text and citation
        assert "\n\n(Source:" in cited_results[0].text

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_citation_handles_special_characters_in_filename(self):
        """Citation should handle special characters in document filename."""
        # GIVEN: Result with special characters in filename
        result = create_query_result(
            source_document="Report_2024-Q3_(FINAL)_v2.1.pdf",
            page_number=5,
            chunk_index=2,
        )

        # WHEN: Generating citation
        cited_results = await generate_citations([result])

        # THEN: Special characters preserved in citation
        assert "(Source: Report_2024-Q3_(FINAL)_v2.1.pdf, page 5, chunk 2)" in cited_results[0].text


class TestCitationNFR7Compliance:
    """Test NFR7 compliance (95%+ attribution accuracy)."""

    @pytest.mark.unit
    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_citations_contain_all_required_fields(self):
        """All citations must contain source, page, and chunk for NFR7."""
        # GIVEN: Multiple results
        results = create_query_results(10)

        # WHEN: Generating citations
        cited_results = await generate_citations(results)

        # THEN: Every citation contains all required fields
        for result in cited_results:
            assert "(Source:" in result.text
            assert "page" in result.text
            assert "chunk" in result.text

    @pytest.mark.unit
    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_citations_uniquely_identify_source_location(self):
        """Each citation must uniquely identify source location (NFR7)."""
        # GIVEN: Results from same document, different locations
        results = [
            create_query_result(source_document="Report.pdf", page_number=10, chunk_index=1),
            create_query_result(source_document="Report.pdf", page_number=10, chunk_index=2),
            create_query_result(source_document="Report.pdf", page_number=11, chunk_index=1),
        ]

        # WHEN: Generating citations
        cited_results = await generate_citations(results)

        # THEN: Citations are unique (different chunk_index or page_number)
        citations = [r.text.split("(Source:")[-1] for r in cited_results]
        assert len(set(citations)) == 3  # All citations unique

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_citations_traceable_to_original_document(self):
        """Citations must be traceable back to original document (NFR7)."""
        # GIVEN: Result with full metadata
        result = create_query_result(
            source_document="Annual_Report_2024.pdf",
            page_number=37,
            chunk_index=89,
        )

        # WHEN: Generating citation
        cited_results = await generate_citations([result])

        # THEN: Citation contains document name (traceable)
        citation = cited_results[0].text
        assert "Annual_Report_2024.pdf" in citation
        assert "page 37" in citation
        assert "chunk 89" in citation


class TestCitationEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_citation_with_large_chunk_index(self):
        """Citation should handle large chunk indices."""
        # GIVEN: Result with large chunk index
        result = create_query_result(chunk_index=9999)

        # WHEN: Generating citation
        cited_results = await generate_citations([result])

        # THEN: Large index handled correctly
        assert "chunk 9999)" in cited_results[0].text

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_citation_with_zero_chunk_index(self):
        """Citation should handle zero chunk index (first chunk)."""
        # GIVEN: Result with chunk_index=0
        result = create_query_result(chunk_index=0)

        # WHEN: Generating citation
        cited_results = await generate_citations([result])

        # THEN: Zero index handled correctly
        assert "chunk 0)" in cited_results[0].text

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    async def test_citation_with_page_one(self):
        """Citation should handle page 1 (first page)."""
        # GIVEN: Result from page 1
        result = create_query_result(page_number=1)

        # WHEN: Generating citation
        cited_results = await generate_citations([result])

        # THEN: Page 1 handled correctly
        assert "page 1" in cited_results[0].text

    @pytest.mark.unit
    @pytest.mark.priority("P3")
    @pytest.mark.asyncio
    async def test_citation_with_multiline_text(self):
        """Citation should handle multiline original text."""
        # GIVEN: Result with multiline text
        multiline_text = "Line 1: Revenue data\nLine 2: EBITDA data\nLine 3: Cash flow"
        result = create_query_result(text=multiline_text)

        # WHEN: Generating citation
        cited_results = await generate_citations([result])

        # THEN: Multiline text preserved, citation appended
        assert multiline_text in cited_results[0].text
        assert "\n\n(Source:" in cited_results[0].text
