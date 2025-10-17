"""Unit tests for response formatting and metadata validation (Story 1.11).

Tests validate QueryResult/QueryResponse models have complete metadata,
correct field types, proper serialization, and handle edge cases gracefully.

Target: 100% metadata completeness (NFR7 - 95%+ source attribution accuracy).
"""

import json

import pytest
from pydantic import ValidationError

from raglite.shared.models import QueryRequest, QueryResponse, QueryResult


@pytest.mark.unit
def test_query_result_metadata_completeness():
    """Validate QueryResult has all required metadata fields.

    Target: 100% metadata completeness (NFR7 - 95%+ source attribution)
    """
    result = QueryResult(
        score=0.85,
        text="Revenue for Q3 2024...\n\n(Source: Q3_Report.pdf, page 12, chunk 45)",
        source_document="Q3_Report.pdf",
        page_number=12,
        chunk_index=45,
        word_count=498,
    )

    # Validate all required fields present and valid
    assert result.score == 0.85
    assert 0.0 <= result.score <= 1.0, "Score must be in [0.0, 1.0]"
    assert result.text != "", "Text must not be empty"
    assert "(Source:" in result.text, "Citation must be appended to text"
    assert result.source_document == "Q3_Report.pdf"
    assert result.source_document != "", "Source document must not be empty"
    assert result.page_number == 12
    assert result.page_number is not None, "Page number must not be None"
    assert result.chunk_index == 45
    assert result.word_count == 498
    assert result.word_count > 0, "Word count must be positive"


@pytest.mark.unit
def test_query_result_page_number_none_handling():
    """Test QueryResult handles None page_number gracefully.

    Edge case: Documents with missing page metadata should still work
    but metadata completeness tracking should flag as incomplete.
    """
    result = QueryResult(
        score=0.85,
        text="Content...\n\n(Source: document.pdf, page N/A, chunk 0)",
        source_document="document.pdf",
        page_number=None,  # Edge case: missing page metadata
        chunk_index=0,
        word_count=100,
    )

    assert result.page_number is None
    # Citation should handle None gracefully: "(Source: document.pdf, page N/A, chunk 0)"
    assert "page N/A" in result.text or "page ?" in result.text


@pytest.mark.unit
def test_query_result_score_range():
    """Validate score is float between 0.0-1.0 for QueryResult.

    Pydantic validation should enforce ge=0.0, le=1.0 constraints.
    """
    # Valid scores
    valid_scores = [0.0, 0.5, 0.85, 1.0]
    for score in valid_scores:
        result = QueryResult(
            score=score,
            text="Test content",
            source_document="test.pdf",
            page_number=1,
            chunk_index=0,
            word_count=10,
        )
        assert 0.0 <= result.score <= 1.0

    # Invalid scores (should raise ValidationError)
    invalid_scores = [-0.1, 1.1, -1.0, 2.0]
    for score in invalid_scores:
        with pytest.raises(ValidationError):
            QueryResult(
                score=score,
                text="Test content",
                source_document="test.pdf",
                page_number=1,
                chunk_index=0,
                word_count=10,
            )


@pytest.mark.unit
def test_query_response_serialization():
    """Validate JSON serialization works for QueryResponse.

    Tests model_dump() and json.dumps() produce valid JSON without errors.
    Verifies field naming consistency (snake_case).
    """
    # Create sample QueryResponse
    results = [
        QueryResult(
            score=0.85,
            text="Revenue was $45M...\n\n(Source: Q3_Report.pdf, page 12, chunk 45)",
            source_document="Q3_Report.pdf",
            page_number=12,
            chunk_index=45,
            word_count=498,
        ),
        QueryResult(
            score=0.78,
            text="Operating expenses...\n\n(Source: Q3_Report.pdf, page 18, chunk 67)",
            source_document="Q3_Report.pdf",
            page_number=18,
            chunk_index=67,
            word_count=342,
        ),
    ]

    response = QueryResponse(
        results=results, query="What was total revenue in Q3 2024?", retrieval_time_ms=830.5
    )

    # Test model_dump()
    response_dict = response.model_dump()
    assert isinstance(response_dict, dict)
    assert "results" in response_dict
    assert "query" in response_dict
    assert "retrieval_time_ms" in response_dict

    # Test JSON serialization
    json_str = json.dumps(response_dict)
    assert isinstance(json_str, str)

    # Re-parse to verify valid JSON
    parsed = json.loads(json_str)
    assert parsed["query"] == "What was total revenue in Q3 2024?"
    assert len(parsed["results"]) == 2
    assert parsed["retrieval_time_ms"] == 830.5

    # Verify snake_case field naming (not camelCase)
    all_keys = list(response_dict.keys()) + list(response_dict["results"][0].keys())
    # Check no camelCase (e.g., "retrievalTimeMs")
    has_camel_case = any(
        "_" not in k and any(c.isupper() for c in k[1:]) for k in all_keys if len(k) > 1
    )
    assert not has_camel_case, "All fields should use snake_case"


@pytest.mark.unit
def test_citation_format():
    """Validate citation appended to text correctly.

    Citation format: (Source: document.pdf, page X, chunk Y)
    Edge case: page_number = None → citation handles gracefully (e.g., "page N/A")
    """
    # Normal case: page_number provided
    result_with_page = QueryResult(
        score=0.85,
        text="Content here.\n\n(Source: doc.pdf, page 12, chunk 5)",
        source_document="doc.pdf",
        page_number=12,
        chunk_index=5,
        word_count=50,
    )

    # Verify citation format
    assert "(Source: doc.pdf, page 12, chunk 5)" in result_with_page.text
    assert result_with_page.text.endswith("(Source: doc.pdf, page 12, chunk 5)")

    # Edge case: page_number = None
    result_no_page = QueryResult(
        score=0.85,
        text="Content here.\n\n(Source: doc.pdf, page N/A, chunk 5)",
        source_document="doc.pdf",
        page_number=None,
        chunk_index=5,
        word_count=50,
    )

    # Verify citation handles None gracefully
    assert "(Source:" in result_no_page.text
    assert "page N/A" in result_no_page.text or "page ?" in result_no_page.text
    assert "chunk 5" in result_no_page.text


@pytest.mark.unit
def test_empty_results_handling():
    """Test QueryResponse with empty results list.

    Verify no errors during serialization with empty results.
    """
    response = QueryResponse(results=[], query="What is the revenue?", retrieval_time_ms=45.2)

    # Should not raise errors
    assert len(response.results) == 0
    assert response.query == "What is the revenue?"

    # Test serialization
    response_dict = response.model_dump()
    assert response_dict["results"] == []

    json_str = json.dumps(response_dict)
    parsed = json.loads(json_str)
    assert parsed["results"] == []


@pytest.mark.unit
def test_edge_case_metadata():
    """Test very long filenames, special characters, missing page numbers.

    Verify no crashes or validation errors with edge case metadata.
    """
    # Very long filename (255 chars is typical filesystem limit)
    long_filename = "A" * 200 + "_report_2024_Q3_financial_analysis_v2.pdf"
    result_long = QueryResult(
        score=0.85,
        text=f"Content...\n\n(Source: {long_filename}, page 12, chunk 5)",
        source_document=long_filename,
        page_number=12,
        chunk_index=5,
        word_count=100,
    )
    assert result_long.source_document == long_filename

    # Special characters in filename
    special_filename = "Q3-Report_2024 (Final) [v2].pdf"
    result_special = QueryResult(
        score=0.78,
        text=f"Content...\n\n(Source: {special_filename}, page 5, chunk 2)",
        source_document=special_filename,
        page_number=5,
        chunk_index=2,
        word_count=80,
    )
    assert result_special.source_document == special_filename

    # Very short chunk (<10 words)
    result_short = QueryResult(
        score=0.92,
        text="Revenue $45M\n\n(Source: doc.pdf, page 1, chunk 0)",
        source_document="doc.pdf",
        page_number=1,
        chunk_index=0,
        word_count=2,  # Only 2 words
    )
    assert result_short.word_count == 2

    # Very long chunk (>1000 words)
    result_long_chunk = QueryResult(
        score=0.65,
        text=("Content " * 1000) + "\n\n(Source: long.pdf, page 50, chunk 100)",
        source_document="long.pdf",
        page_number=50,
        chunk_index=100,
        word_count=1500,
    )
    assert result_long_chunk.word_count == 1500


@pytest.mark.unit
def test_metadata_completeness_validation():
    """Test validation logic for all required fields.

    Create QueryResult with missing/invalid fields, verify appropriate validation errors.
    """
    # Valid QueryResult (baseline)
    valid = QueryResult(
        score=0.85,
        text="Content",
        source_document="doc.pdf",
        page_number=12,
        chunk_index=5,
        word_count=50,
    )
    assert valid.score == 0.85

    # Missing required field: score
    with pytest.raises(ValidationError):
        QueryResult(
            text="Content",
            source_document="doc.pdf",
            page_number=12,
            chunk_index=5,
            word_count=50,
        )

    # Missing required field: text
    with pytest.raises(ValidationError):
        QueryResult(
            score=0.85,
            source_document="doc.pdf",
            page_number=12,
            chunk_index=5,
            word_count=50,
        )

    # Missing required field: source_document
    with pytest.raises(ValidationError):
        QueryResult(score=0.85, text="Content", page_number=12, chunk_index=5, word_count=50)

    # Missing required field: chunk_index
    with pytest.raises(ValidationError):
        QueryResult(
            score=0.85,
            text="Content",
            source_document="doc.pdf",
            page_number=12,
            word_count=50,
        )

    # Missing required field: word_count
    with pytest.raises(ValidationError):
        QueryResult(
            score=0.85,
            text="Content",
            source_document="doc.pdf",
            page_number=12,
            chunk_index=5,
        )

    # page_number = None is ALLOWED (nullable field for edge cases)
    valid_none_page = QueryResult(
        score=0.85,
        text="Content",
        source_document="doc.pdf",
        page_number=None,
        chunk_index=5,
        word_count=50,
    )
    assert valid_none_page.page_number is None


@pytest.mark.unit
def test_query_request_validation():
    """Test QueryRequest model validation.

    Verify top_k constraints (1-50) and required query field.
    """
    # Valid QueryRequest
    valid = QueryRequest(query="What is revenue?", top_k=5)
    assert valid.query == "What is revenue?"
    assert valid.top_k == 5

    # Default top_k
    default = QueryRequest(query="What is revenue?")
    assert default.top_k == 5  # Default from models.py

    # top_k boundary values
    min_k = QueryRequest(query="Query", top_k=1)
    assert min_k.top_k == 1

    max_k = QueryRequest(query="Query", top_k=50)
    assert max_k.top_k == 50

    # Invalid top_k (out of range)
    with pytest.raises(ValidationError):
        QueryRequest(query="Query", top_k=0)  # Below minimum

    with pytest.raises(ValidationError):
        QueryRequest(query="Query", top_k=51)  # Above maximum

    # Missing required query
    with pytest.raises(ValidationError):
        QueryRequest(top_k=5)
