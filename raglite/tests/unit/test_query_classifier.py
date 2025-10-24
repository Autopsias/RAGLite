"""Unit tests for query type classification (Story 2.7 AC1).

Tests the heuristic-based query classifier that routes queries to appropriate
retrieval indexes (VECTOR_ONLY, SQL_ONLY, or HYBRID).
"""

import time

import pytest

from raglite.retrieval.query_classifier import QueryType, classify_query


class TestQueryClassification:
    """Test suite for query type classification heuristics."""

    # SQL_ONLY test queries (10 queries)
    sql_only_queries = [
        "What is the exact revenue in Q3 2024?",
        "Show me the table for operating expenses",
        "Give me the precise cost per ton",
        "What is the value in row 5 column 3?",
        "Display the specific EBITDA for Portugal",
        "List all table entries for August",
        "What is 23.5 EUR/ton for variable costs?",
        "Show me the cell with thermal energy data",
        "What is the production volume at 1.2M tonnes?",
        "Give me the exact profit margin of 15%",
    ]

    # VECTOR_ONLY test queries (5 queries)
    vector_only_queries = [
        "Explain the company's growth strategy",
        "Summarize the financial performance",
        "Why did the management make this decision?",
        "Describe the competitive landscape",
        "How does the business model work?",
    ]

    # HYBRID test queries (5 queries)
    hybrid_queries = [
        "Why did EBITDA increase 15% in Q3?",
        "Explain the revenue growth of $1.2M",
        "How did costs decrease to 23 EUR/ton?",
        "Describe the 10% margin improvement",
        "Why did production reach 500K tonnes?",
    ]

    def test_sql_only_classification(self) -> None:
        """Test SQL_ONLY query classification."""
        correct = 0
        for query in self.sql_only_queries:
            result = classify_query(query)
            if result == QueryType.SQL_ONLY:
                correct += 1
            else:
                print(f"FAILED SQL_ONLY: '{query}' classified as {result.value}")

        # Target: ≥9/10 correct (90% accuracy)
        accuracy = correct / len(self.sql_only_queries)
        assert accuracy >= 0.9, f"SQL_ONLY accuracy {accuracy:.1%} < 90%"

    def test_vector_only_classification(self) -> None:
        """Test VECTOR_ONLY query classification."""
        correct = 0
        for query in self.vector_only_queries:
            result = classify_query(query)
            if result == QueryType.VECTOR_ONLY:
                correct += 1
            else:
                print(f"FAILED VECTOR_ONLY: '{query}' classified as {result.value}")

        # Target: ≥4/5 correct (80% accuracy, lower threshold for semantic queries)
        accuracy = correct / len(self.vector_only_queries)
        assert accuracy >= 0.8, f"VECTOR_ONLY accuracy {accuracy:.1%} < 80%"

    def test_hybrid_classification(self) -> None:
        """Test HYBRID query classification."""
        correct = 0
        for query in self.hybrid_queries:
            result = classify_query(query)
            if result == QueryType.HYBRID:
                correct += 1
            else:
                print(f"FAILED HYBRID: '{query}' classified as {result.value}")

        # Target: ≥4/5 correct (80% accuracy)
        accuracy = correct / len(self.hybrid_queries)
        assert accuracy >= 0.8, f"HYBRID accuracy {accuracy:.1%} < 80%"

    def test_overall_accuracy(self) -> None:
        """Test overall classification accuracy ≥90%."""
        all_queries = [
            *[(q, QueryType.SQL_ONLY) for q in self.sql_only_queries],
            *[(q, QueryType.VECTOR_ONLY) for q in self.vector_only_queries],
            *[(q, QueryType.HYBRID) for q in self.hybrid_queries],
        ]

        correct = 0
        for query, expected_type in all_queries:
            result = classify_query(query)
            if result == expected_type:
                correct += 1

        accuracy = correct / len(all_queries)
        assert accuracy >= 0.9, f"Overall accuracy {accuracy:.1%} < 90% (AC1 requirement)"

    def test_classification_latency(self) -> None:
        """Test classification latency <50ms (AC1 requirement)."""
        test_query = "What is the revenue for Q3 2024?"
        iterations = 100

        start_time = time.time()
        for _ in range(iterations):
            classify_query(test_query)
        elapsed_ms = (time.time() - start_time) * 1000

        avg_latency_ms = elapsed_ms / iterations
        assert avg_latency_ms < 50, (
            f"Avg classification latency {avg_latency_ms:.2f}ms >= 50ms (AC1 requirement)"
        )

        print(f"✅ Classification latency: {avg_latency_ms:.2f}ms (target: <50ms)")

    def test_empty_query(self) -> None:
        """Test classification handles empty queries gracefully."""
        result = classify_query("")
        # Empty query defaults to VECTOR_ONLY (safe default)
        assert result == QueryType.VECTOR_ONLY

    def test_numeric_pattern_detection(self) -> None:
        """Test numeric pattern detection in queries."""
        numeric_queries = [
            ("Revenue is $1.2M", QueryType.SQL_ONLY),
            ("Costs are 23.5 EUR/ton", QueryType.SQL_ONLY),
            ("Margin improved by 15%", QueryType.SQL_ONLY),
            ("Production reached 500K tonnes", QueryType.SQL_ONLY),
        ]

        for query, expected_type in numeric_queries:
            result = classify_query(query)
            assert result == expected_type, f"Query '{query}' misclassified as {result.value}"

    def test_semantic_keyword_detection(self) -> None:
        """Test semantic keyword detection in queries."""
        semantic_queries = [
            ("Explain the strategy", QueryType.VECTOR_ONLY),
            ("Summarize the report", QueryType.VECTOR_ONLY),
            ("Why did this happen?", QueryType.VECTOR_ONLY),
            ("Describe the process", QueryType.VECTOR_ONLY),
            ("How does it work?", QueryType.VECTOR_ONLY),
        ]

        for query, expected_type in semantic_queries:
            result = classify_query(query)
            assert result == expected_type, f"Query '{query}' misclassified as {result.value}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
