"""Test data factories using faker for deterministic test data generation.

This module provides factory functions for generating test data with realistic
values. All factories support overrides for specific test scenarios.

Best Practices (from production codebases):
- Use faker for all random data (no hardcoded values)
- Support overrides via **kwargs for specific test needs
- Return Pydantic models when possible for type safety
- Keep factories pure (no side effects, no DB/API calls)

Example Usage:
    # Default financial document
    doc = create_financial_document()

    # Override specific fields
    doc = create_financial_document(page_count=50, filename="Q4_2024.pdf")

    # Create multiple documents
    docs = create_financial_documents(5)

    # Create chunk with custom content
    chunk = create_chunk(content="Revenue was $100M in Q3")
"""

# Initialize faker with seed for deterministic test data
# Seed can be overridden via environment variable for reproducibility
import os
from typing import Any
from unittest.mock import MagicMock

from faker import Faker

from raglite.shared.models import Chunk, DocumentMetadata, QueryResult

_FAKER_SEED = int(os.getenv("FAKER_SEED", "42"))
fake = Faker()
Faker.seed(_FAKER_SEED)


def create_document_metadata(**overrides: Any) -> DocumentMetadata:
    """Create sample document metadata with realistic values.

    Args:
        **overrides: Override specific fields (filename, doc_type, page_count, etc.)

    Returns:
        DocumentMetadata instance with generated or overridden values

    Example:
        # Default quarterly report
        doc = create_document_metadata()

        # Annual report with 100 pages
        doc = create_document_metadata(
            filename="Annual_Report_2024.pdf",
            page_count=100
        )
    """
    defaults = {
        "filename": f"{fake.company()}_Q{fake.random_int(1, 4)}_{fake.year()}.pdf",
        "doc_type": "PDF",
        "ingestion_timestamp": fake.iso8601(),
        "page_count": fake.random_int(10, 200),
        "source_path": f"/tmp/{fake.file_name(extension='pdf')}",
    }
    defaults.update(overrides)
    return DocumentMetadata(**defaults)


def create_document_metadatas(count: int, **overrides: Any) -> list[DocumentMetadata]:
    """Create multiple document metadata instances.

    Args:
        count: Number of documents to create
        **overrides: Override fields for ALL documents

    Returns:
        List of DocumentMetadata instances

    Example:
        # Create 5 quarterly reports
        docs = create_document_metadatas(5)
    """
    return [create_document_metadata(**overrides) for _ in range(count)]


def create_chunk(metadata: DocumentMetadata | None = None, **overrides: Any) -> Chunk:
    """Create sample chunk with realistic financial content.

    Args:
        metadata: Optional DocumentMetadata (creates default if not provided)
        **overrides: Override specific fields (content, page_number, embedding, etc.)

    Returns:
        Chunk instance with generated or overridden values

    Example:
        # Random financial chunk
        chunk = create_chunk()

        # Specific revenue statement
        chunk = create_chunk(
            content="Q3 revenue was $50M, up 20% YoY",
            page_number=5
        )

        # Chunk with custom metadata
        doc = create_document_metadata(filename="Custom.pdf")
        chunk = create_chunk(metadata=doc)
    """
    if metadata is None:
        metadata = create_document_metadata()

    # Generate realistic financial content variations
    content_templates = [
        f"Revenue for Q{fake.random_int(1, 4)} was ${fake.random_int(10, 500)}M, up {fake.random_int(5, 50)}% YoY.",
        f"Operating expenses increased {fake.random_int(5, 30)}% to ${fake.random_int(5, 100)}M.",
        f"Net income for the period was ${fake.random_int(10, 200)}M, representing a {fake.random_int(5, 40)}% margin.",
        f"Cash position at end of quarter: ${fake.random_int(50, 500)}M.",
        f"{fake.company()} reported EBITDA of ${fake.random_int(20, 300)}M for the fiscal year.",
    ]

    defaults = {
        "chunk_id": f"chunk-{fake.uuid4()}",
        "content": fake.random_element(content_templates),
        "metadata": metadata,
        "page_number": fake.random_int(1, metadata.page_count),
        "embedding": [fake.pyfloat(min_value=-1, max_value=1) for _ in range(1024)],
    }
    defaults.update(overrides)
    return Chunk(**defaults)


def create_chunks(
    count: int, metadata: DocumentMetadata | None = None, **overrides: Any
) -> list[Chunk]:
    """Create multiple chunks sharing the same document metadata.

    Args:
        count: Number of chunks to create
        metadata: Optional shared DocumentMetadata (creates default if not provided)
        **overrides: Override fields for ALL chunks

    Returns:
        List of Chunk instances

    Example:
        # Create 10 chunks from same document
        chunks = create_chunks(10)

        # Create 5 chunks from specific document
        doc = create_document_metadata(filename="Report.pdf")
        chunks = create_chunks(5, metadata=doc)
    """
    if metadata is None:
        metadata = create_document_metadata()
    return [create_chunk(metadata=metadata, **overrides) for _ in range(count)]


def create_financial_table_row(**overrides: Any) -> dict[str, Any]:
    """Create sample financial table row with realistic values.

    Args:
        **overrides: Override specific fields

    Returns:
        Dictionary representing a PostgreSQL financial_tables row

    Example:
        row = create_financial_table_row()
        row = create_financial_table_row(entity="Apple Inc", metric="Revenue")
    """
    entities = ["Company A", "Company B", "Division X", "Division Y", "Segment Alpha"]
    metrics = ["Revenue", "EBITDA", "Net Income", "Operating Expenses", "Cash Flow"]
    units = ["USD millions", "EUR millions", "GBP millions", "percentage", "count"]
    periods = ["Q1", "Q2", "Q3", "Q4", "FY", "H1", "H2"]

    defaults = {
        "entity": fake.random_element(entities),
        "metric": fake.random_element(metrics),
        "value": fake.pydecimal(left_digits=6, right_digits=2, positive=True),
        "unit": fake.random_element(units),
        "period": fake.random_element(periods),
        "fiscal_year": fake.random_int(2020, 2025),
        "page_number": fake.random_int(1, 50),
    }
    defaults.update(overrides)
    return defaults


def create_financial_table_rows(count: int, **overrides: Any) -> list[dict[str, Any]]:
    """Create multiple financial table rows.

    Args:
        count: Number of rows to create
        **overrides: Override fields for ALL rows

    Returns:
        List of dictionaries representing PostgreSQL rows
    """
    return [create_financial_table_row(**overrides) for _ in range(count)]


def create_query(**overrides: Any) -> str:
    """Create sample natural language query for financial documents.

    Args:
        **overrides: Override 'query' key to provide specific query

    Returns:
        Natural language query string

    Example:
        q = create_query()  # Random financial query
        q = create_query(query="What was Q3 revenue?")  # Specific query
    """
    query_templates = [
        f"What was the {fake.random_element(['revenue', 'net income', 'EBITDA'])} in Q{fake.random_int(1, 4)}?",
        f"How did {fake.random_element(['operating expenses', 'cash flow', 'margins'])} change YoY?",
        f"What are the key financial metrics for {fake.random_element(['FY2023', 'FY2024', 'Q4'])}?",
        f"Compare revenue between Q{fake.random_int(1, 4)} and Q{fake.random_int(1, 4)}",
        "What were the main factors affecting profitability?",
    ]

    if "query" in overrides:
        return overrides["query"]

    return fake.random_element(query_templates)


def create_queries(count: int, **overrides: Any) -> list[str]:
    """Create multiple financial queries.

    Args:
        count: Number of queries to create
        **overrides: Override 'query' key for ALL queries

    Returns:
        List of query strings
    """
    return [create_query(**overrides) for _ in range(count)]


def create_query_result(**overrides: Any) -> QueryResult:
    """Create sample query result for search/retrieval testing.

    Args:
        **overrides: Override specific fields (score, text, source_document, etc.)

    Returns:
        QueryResult instance with generated or overridden values

    Example:
        # Default search result
        result = create_query_result()

        # High-scoring result with specific content
        result = create_query_result(
            score=0.95,
            text="Q3 revenue was $50M, up 20% YoY",
            source_document="Q3_2024_Report.pdf",
            page_number=12
        )
    """
    # Generate realistic financial content
    content_templates = [
        f"Revenue for Q{fake.random_int(1, 4)} was ${fake.random_int(10, 500)}M, representing {fake.random_int(5, 50)}% growth.",
        f"EBITDA margin improved to {fake.random_int(15, 40)}% from {fake.random_int(10, 35)}% in the prior period.",
        f"Operating cash flow reached ${fake.random_int(50, 300)}M, up {fake.random_int(10, 40)}% year-over-year.",
        f"Net income for the fiscal year was ${fake.random_int(20, 200)}M, exceeding analyst expectations.",
        f"The company reported total assets of ${fake.random_int(500, 2000)}M at quarter end.",
    ]

    text = fake.random_element(content_templates)

    defaults = {
        "score": fake.pyfloat(min_value=0.5, max_value=1.0),
        "text": text,
        "source_document": f"{fake.company()}_Q{fake.random_int(1, 4)}_{fake.year()}.pdf",
        "page_number": fake.random_int(1, 100),
        "chunk_index": fake.random_int(0, 200),
        "word_count": len(text.split()),  # Calculate from text
    }
    defaults.update(overrides)

    # Recalculate word_count if text was overridden
    if "text" in overrides and "word_count" not in overrides:
        defaults["word_count"] = len(overrides["text"].split())

    return QueryResult(**defaults)


def create_query_results(count: int, **overrides: Any) -> list[QueryResult]:
    """Create multiple query results for search testing.

    Args:
        count: Number of results to create
        **overrides: Override fields for ALL results

    Returns:
        List of QueryResult instances

    Example:
        # Create 5 results from same document
        results = create_query_results(5, source_document="Report.pdf")

        # Create results with descending scores
        results = [create_query_result(score=1.0 - i*0.1) for i in range(5)]
    """
    return [create_query_result(**overrides) for _ in range(count)]


def create_qdrant_scored_point(
    chunk_id: str | None = None, score: float | None = None, **payload_overrides: Any
) -> MagicMock:
    """Create mock Qdrant ScoredPoint for search result testing.

    Args:
        chunk_id: Optional chunk ID (generates UUID if not provided)
        score: Optional relevance score (generates 0.5-1.0 if not provided)
        **payload_overrides: Override payload fields

    Returns:
        MagicMock instance configured as Qdrant ScoredPoint

    Example:
        # Default scored point
        point = create_qdrant_scored_point()

        # High-scoring point with specific data
        point = create_qdrant_scored_point(
            score=0.95,
            chunk_id="chunk-123",
            content="Q3 revenue was $50M"
        )
    """
    mock_point = MagicMock()
    mock_point.id = chunk_id or f"chunk-{fake.uuid4()}"
    mock_point.score = score if score is not None else fake.pyfloat(min_value=0.5, max_value=1.0)

    # Default payload
    default_payload = {
        "content": fake.random_element(
            [
                f"Revenue for Q{fake.random_int(1, 4)} was ${fake.random_int(10, 500)}M.",
                f"EBITDA margin improved to {fake.random_int(15, 40)}%.",
                f"Operating cash flow reached ${fake.random_int(50, 300)}M.",
            ]
        ),
        "source_document": f"{fake.company()}_Report.pdf",
        "page_number": fake.random_int(1, 100),
        "chunk_index": fake.random_int(0, 200),
    }
    default_payload.update(payload_overrides)
    mock_point.payload = default_payload

    return mock_point


def create_qdrant_scored_points(count: int, **overrides: Any) -> list[MagicMock]:
    """Create multiple Qdrant ScoredPoint mocks.

    Args:
        count: Number of points to create
        **overrides: Override fields for ALL points

    Returns:
        List of MagicMock ScoredPoint instances

    Example:
        # Create 5 results from same document
        points = create_qdrant_scored_points(5, source_document="Report.pdf")
    """
    return [create_qdrant_scored_point(**overrides) for _ in range(count)]


def create_mcp_tool_response(success: bool = True, **overrides: Any) -> dict[str, Any]:
    """Create MCP tool response structure for testing.

    Args:
        success: Whether response indicates success (default: True)
        **overrides: Override specific fields

    Returns:
        Dictionary representing MCP tool response

    Example:
        # Success response
        response = create_mcp_tool_response()

        # Error response
        response = create_mcp_tool_response(
            success=False,
            error="Query failed"
        )
    """
    if success:
        defaults = {
            "content": [
                {"type": "text", "text": f"Found {fake.random_int(1, 10)} results for your query."}
            ],
            "isError": False,
        }
    else:
        defaults = {
            "content": [{"type": "text", "text": overrides.get("error", "An error occurred")}],
            "isError": True,
        }

    defaults.update(overrides)
    return defaults


def create_sql_table_row(**overrides: Any) -> dict[str, Any]:
    """Create PostgreSQL financial_tables row for testing.

    Args:
        **overrides: Override specific fields

    Returns:
        Dictionary representing database row

    Example:
        row = create_sql_table_row(
            entity="Apple Inc",
            metric="Revenue",
            value=100.5,
            period="Q3-24"
        )
    """
    entities = ["Secil Group", "Company A", "Division X", "Segment Alpha"]
    metrics = ["EBITDA", "Revenue", "Cost per ton", "Operating margin", "Cash flow"]
    units = ["EUR millions", "USD millions", "EUR/ton", "percentage", "count"]

    defaults = {
        "id": fake.random_int(1, 10000),
        "entity": fake.random_element(entities),
        "metric": fake.random_element(metrics),
        "value": float(fake.pydecimal(left_digits=5, right_digits=2, positive=True)),
        "unit": fake.random_element(units),
        "period": f"Q{fake.random_int(1, 4)}-{fake.random_int(23, 25)}",
        "fiscal_year": fake.random_int(2023, 2025),
        "page_number": fake.random_int(1, 100),
        "source_document": f"Financial_Report_{fake.year()}.pdf",
    }
    defaults.update(overrides)
    return defaults


def create_sql_table_rows(count: int, **overrides: Any) -> list[dict[str, Any]]:
    """Create multiple PostgreSQL table rows.

    Args:
        count: Number of rows to create
        **overrides: Override fields for ALL rows

    Returns:
        List of database row dictionaries
    """
    return [create_sql_table_row(**overrides) for _ in range(count)]


# Cleanup helper for integration tests
def cleanup_test_data():
    """Clean up test data after integration tests.

    This is a placeholder for future cleanup logic if needed.
    Currently, tests use fixtures with auto-cleanup.
    """
    pass
