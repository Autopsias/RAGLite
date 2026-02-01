"""Query and search result test data factories.

Provides factory functions for generating natural language queries, search results,
and Qdrant ScoredPoint mocks with realistic financial content.
"""

import os
from typing import Any
from unittest.mock import MagicMock

from faker import Faker

from raglite.shared.models import QueryResult

_FAKER_SEED = int(os.getenv("FAKER_SEED", "42"))
fake = Faker()
Faker.seed(_FAKER_SEED)


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
