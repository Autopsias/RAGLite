"""Unit tests for query complexity classifier (Story 3.5 Task 1.4).

Tests AC1: Query complexity classifier distinguishes simple vs multi-step analytical queries
- Simple queries (<5 words, no comparative language) routed directly to retrieval
- Analytical queries (contains: "growth", "variance", "trend", "compare", "explain") marked as analytical
- Classifier accuracy >90% on test queries from ground truth set
"""

import pytest

from raglite.agentic.planner import QueryComplexity, classify_query_complexity


class TestSimpleQueries:
    """Test classification of simple retrieval queries."""

    @pytest.mark.asyncio
    async def test_simple_what_query(self):
        """Simple 'what is' query should be classified as SIMPLE."""
        query = "What is Q3 revenue?"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_simple_list_query(self):
        """Simple 'list' query should be classified as SIMPLE."""
        query = "List all expenses"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_simple_show_query(self):
        """Simple 'show' query should be classified as SIMPLE."""
        query = "Show Q3 2024 results"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_simple_find_query(self):
        """Simple 'find' query should be classified as SIMPLE."""
        query = "Find revenue information"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_simple_get_query(self):
        """Simple 'get' query should be classified as SIMPLE."""
        query = "Get financial statements"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.SIMPLE


class TestAnalyticalQueries:
    """Test classification of analytical/multi-step queries."""

    @pytest.mark.asyncio
    async def test_analytical_calculate_growth(self):
        """'Calculate growth' query should be ANALYTICAL."""
        query = "Calculate YoY revenue growth"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_analytical_compare(self):
        """'Compare' query should be ANALYTICAL."""
        query = "Compare Q3 2023 and Q4 2024"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_analytical_explain_variance(self):
        """'Explain variance' query should be ANALYTICAL."""
        query = "Explain the variance in expenses"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_analytical_analyze(self):
        """'Analyze' query should be ANALYTICAL."""
        query = "Analyze revenue trends"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_analytical_trend(self):
        """'Trend' query should be ANALYTICAL."""
        query = "What is the trend in revenue?"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_analytical_yoy(self):
        """'YoY' query should be ANALYTICAL."""
        query = "What is the YoY change?"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_analytical_percentage(self):
        """'Percentage' query should be ANALYTICAL."""
        query = "What percentage did revenue increase?"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_analytical_growth(self):
        """'Growth' query should be ANALYTICAL."""
        query = "What drove revenue growth?"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_analytical_driver(self):
        """'Driver' query should be ANALYTICAL."""
        query = "What are the revenue drivers?"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_analytical_impact(self):
        """'Impact' query should be ANALYTICAL."""
        query = "What is the impact of marketing spend?"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Empty query should default to SIMPLE."""
        query = ""
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_single_word_query(self):
        """Single word query should be SIMPLE."""
        query = "Revenue"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_case_insensitive_analytical(self):
        """Classifier should be case-insensitive (uppercase analytical)."""
        query = "CALCULATE REVENUE GROWTH"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_case_insensitive_simple(self):
        """Classifier should be case-insensitive (uppercase simple)."""
        query = "WHAT IS REVENUE"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_mixed_case_analytical(self):
        """Classifier should handle mixed case."""
        query = "ExPlAiN the VaRiAnCe"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_query_with_punctuation(self):
        """Queries with punctuation should work correctly."""
        query = "Calculate YoY growth, and explain drivers?"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL

    @pytest.mark.asyncio
    async def test_long_simple_query(self):
        """Long query without analytical keywords should be SIMPLE."""
        query = "Show me the revenue information from the financial statements for Q3 2024"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_percentage_symbol(self):
        """Query with '%' symbol should be ANALYTICAL."""
        query = "What is the % change in revenue?"
        result = await classify_query_complexity(query)
        assert result == QueryComplexity.ANALYTICAL


class TestGroundTruthAccuracy:
    """Test classifier accuracy on ground truth queries (AC1: >90%)."""

    @pytest.mark.asyncio
    async def test_ground_truth_simple_queries(self):
        """Test SIMPLE classification on ground truth simple queries."""
        simple_queries = [
            "What is revenue?",
            "List expenses",
            "Show Q3 results",
            "Find profit information",
            "Get operating costs",
            "What are liabilities?",
            "Display cash flow",
            "Retrieve balance sheet",
            "Show assets",
            "What is EBITDA?",
        ]

        correct_count = 0
        for query in simple_queries:
            result = await classify_query_complexity(query)
            if result == QueryComplexity.SIMPLE:
                correct_count += 1

        accuracy = correct_count / len(simple_queries)
        assert accuracy >= 0.9, f"Simple query accuracy {accuracy:.1%} < 90%"

    @pytest.mark.asyncio
    async def test_ground_truth_analytical_queries(self):
        """Test ANALYTICAL classification on ground truth analytical queries."""
        analytical_queries = [
            "Calculate YoY revenue growth",
            "Compare Q3 2023 and Q3 2024",
            "Explain the variance in expenses",
            "Analyze revenue trends over 4 quarters",
            "What drove the increase in costs?",
            "Determine the percentage change",
            "Compute the impact of marketing spend",
            "What is the YoY change in profit?",
            "Forecast revenue for next quarter",
            "Assess the difference between Q3 and Q4",
        ]

        correct_count = 0
        for query in analytical_queries:
            result = await classify_query_complexity(query)
            if result == QueryComplexity.ANALYTICAL:
                correct_count += 1

        accuracy = correct_count / len(analytical_queries)
        assert accuracy >= 0.9, f"Analytical query accuracy {accuracy:.1%} < 90%"

    @pytest.mark.asyncio
    async def test_overall_classifier_accuracy(self):
        """Test overall classifier accuracy >90% (AC1)."""
        test_cases = [
            # Simple queries (expected: SIMPLE)
            ("What is revenue?", QueryComplexity.SIMPLE),
            ("List expenses", QueryComplexity.SIMPLE),
            ("Show Q3 results", QueryComplexity.SIMPLE),
            ("Find profit", QueryComplexity.SIMPLE),
            ("Get costs", QueryComplexity.SIMPLE),
            # Analytical queries (expected: ANALYTICAL)
            ("Calculate YoY growth", QueryComplexity.ANALYTICAL),
            ("Compare Q3 and Q4", QueryComplexity.ANALYTICAL),
            ("Explain variance", QueryComplexity.ANALYTICAL),
            ("Analyze trends", QueryComplexity.ANALYTICAL),
            ("What is the percentage change?", QueryComplexity.ANALYTICAL),
            ("Determine the impact", QueryComplexity.ANALYTICAL),
            ("What drove revenue growth?", QueryComplexity.ANALYTICAL),
            ("Forecast revenue", QueryComplexity.ANALYTICAL),
            ("Assess the difference", QueryComplexity.ANALYTICAL),
            ("Compute YoY %", QueryComplexity.ANALYTICAL),
        ]

        correct_count = 0
        for query, expected in test_cases:
            result = await classify_query_complexity(query)
            if result == expected:
                correct_count += 1

        accuracy = correct_count / len(test_cases)
        assert accuracy >= 0.9, f"Overall classifier accuracy {accuracy:.1%} < 90% (AC1)"
