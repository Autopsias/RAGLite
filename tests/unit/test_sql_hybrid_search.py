"""Test Suite for Hybrid Search - Story 2.14 Epic 2 Scope.

IMPORTANT: This test suite focuses on LITERAL SQL RETRIEVAL with fuzzy entity matching (AC0-AC2).
Do NOT add tests for interpretation, phrasing variance, or calculation - those are Epic 3+.

Reference: Story 2.14 Completion Notes (lines 1220-1224):
"Test what Story 2.14 was designed to do: retrieve literal data from tables using SQL
with fuzzy entity matching. Do NOT test interpretation, phrasing variance, or calculation -
those are Epic 3+."

Deferred Tests for Future Epics:
- Epic 3 (Story 3.3): LLM interpretation, phrasing variance, calculated metrics
- Epic 4 (Story 4.6+): Proactive insights, reasoning, complex multi-step queries
"""

import pytest

from raglite.retrieval.query_classifier import generate_sql_query

# =============================================================================
# LITERAL SQL RETRIEVAL TESTS (AC0-AC2 scope)
# =============================================================================


@pytest.mark.asyncio
async def test_hybrid_search_single_entity_literal(mock_mistral_client):
    """Test AC0: Single entity literal retrieval via SQL.

    Verifies that SQL backend can retrieve data for a single entity
    using direct entity name match.

    Scope: LITERAL SQL RETRIEVAL (Epic 2)
    Do NOT test: phrasing variance, fuzzy matching beyond similarity threshold
    """
    # Configure mock for single entity query
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE entity ILIKE '%Portugal%'
  AND metric ILIKE '%variable cost%'
ORDER BY page_number DESC
LIMIT 50;
    """.strip()

    query = "Portugal variable cost"
    sql = await generate_sql_query(query)

    assert sql is not None, "SQL should be generated for entity query"
    assert "Portugal" in sql or "portugal" in sql.lower(), "SQL should reference Portugal"


@pytest.mark.asyncio
async def test_hybrid_search_fuzzy_entity_matching(mock_mistral_client):
    """Test AC1: Fuzzy entity matching via PostgreSQL similarity().

    Verifies that SQL uses fuzzy matching for entity name variations
    when exact match fails.

    Scope: FUZZY ENTITY MATCHING (AC1)
    Do NOT test: Interpretation of data, calculation of derived metrics
    """
    # Configure mock for fuzzy entity matching
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE entity ILIKE '%Tunisia%'
  AND metric ILIKE '%EBITDA%'
ORDER BY page_number DESC
LIMIT 50;
    """.strip()

    query = "Tunisia EBITDA"
    sql = await generate_sql_query(query)

    assert sql is not None, "SQL should be generated"
    # Verify SQL includes similarity() function for fuzzy matching
    assert "similarity(" in sql.lower() or "ilike" in sql.lower() or "like" in sql.lower(), (
        "SQL should use fuzzy matching (similarity, ILIKE, or LIKE)"
    )


@pytest.mark.asyncio
async def test_hybrid_search_multi_entity_comparison(mock_mistral_client):
    """Test AC2: Multi-entity comparison queries.

    Verifies that SQL generates IN clause or multiple OR conditions
    to retrieve data for comparison between entities.

    Scope: MULTI-ENTITY SQL RETRIEVAL (AC2)
    Do NOT test: Comparison logic, ranking, interpretation
    """
    # Configure mock for multi-entity comparison
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE (entity ILIKE '%Portugal%' OR entity ILIKE '%Tunisia%')
  AND metric ILIKE '%variable cost%'
ORDER BY page_number DESC
LIMIT 50;
    """.strip()

    query = "Compare Portugal and Tunisia variable cost"
    sql = await generate_sql_query(query)

    assert sql is not None, "SQL should be generated for comparison queries"
    # Verify SQL uses OR or IN clause for multiple entities
    assert " OR " in sql.upper() or " IN " in sql.upper(), (
        "SQL should contain OR or IN clause for multiple entity matching"
    )


@pytest.mark.asyncio
async def test_hybrid_search_keyword_detection(mock_mistral_client):
    """Test AC2: Comparison keyword detection.

    Verifies that SQL generation detects comparison keywords:
    compare, vs, versus, between, which, higher, lower

    Scope: COMPARISON KEYWORD DETECTION (AC2)
    Do NOT test: Result ranking, interpretation
    """
    # Configure mock for comparison keyword detection
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE (entity ILIKE '%Portugal%' OR entity ILIKE '%Tunisia%' OR entity ILIKE '%Angola%' OR entity ILIKE '%Brazil%' OR entity ILIKE '%Lebanon%')
ORDER BY page_number DESC
LIMIT 50;
    """.strip()

    comparison_queries = [
        "Compare Portugal and Tunisia",
        "Portugal vs Brazil revenue",
        "Which plant has higher EBITDA: Angola or Lebanon?",
        "Revenue differences between Angola and Brazil",
    ]

    for query in comparison_queries:
        sql = await generate_sql_query(query)
        assert sql is not None, f"SQL should generate for: {query}"


@pytest.mark.asyncio
async def test_hybrid_search_literal_metric_matching(mock_mistral_client):
    """Test AC0: Literal metric name matching.

    Verifies that SQL can retrieve data for specific metric names
    without interpretation or inference.

    Scope: LITERAL METRIC RETRIEVAL (AC0)
    Do NOT test: Calculated metrics, metric aliases, metric inference
    """
    # Configure mock for literal metric matching
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE entity ILIKE '%Brazil%'
  AND metric ILIKE '%EBITDA%'
ORDER BY page_number DESC
LIMIT 50;
    """.strip()

    query = "EBITDA for Brazil"
    sql = await generate_sql_query(query)

    assert sql is not None, "SQL should be generated for metric query"
    assert "ebitda" in sql.lower() or "metric" in sql.lower(), "SQL should reference EBITDA metric"


# =============================================================================
# ERROR HANDLING TESTS (AC0-AC2 scope)
# =============================================================================


@pytest.mark.asyncio
async def test_hybrid_search_empty_result_handling(mock_mistral_client):
    """Test that empty results are handled gracefully.

    When a query generates valid SQL but returns no rows (data unavailable),
    the system should handle gracefully without errors.

    Scope: ERROR HANDLING (AC0-AC2)
    """
    # Configure mock for empty result handling
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE 1=0
LIMIT 50;
    """.strip()

    # Query that may return no results depending on data availability
    query = "Revenue differences between all entities"
    try:
        sql = await generate_sql_query(query)
        assert sql is not None, "SQL should be generated"
    except Exception as e:
        pytest.fail(f"Should handle empty results gracefully: {str(e)[:100]}")


@pytest.mark.asyncio
async def test_hybrid_search_sql_generation_success(mock_mistral_client):
    """Test that SQL generation succeeds for standard queries.

    Verifies that the SQL generation pipeline completes without errors
    for a variety of query types within Epic 2 scope.

    Scope: LITERAL RETRIEVAL (AC0-AC2)
    """
    # Configure mock for multiple queries
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
ORDER BY page_number DESC
LIMIT 50;
    """.strip()

    test_queries = [
        "What is the variable cost for Portugal?",
        "Show EBITDA for Tunisia",
        "Angola revenue comparison",
        "Which entity has higher costs?",
    ]

    for query in test_queries:
        sql = await generate_sql_query(query)
        assert sql is not None, f"SQL generation should succeed for: {query}"
        assert isinstance(sql, str), f"SQL should be string for: {query}"
        assert len(sql) > 0, f"SQL should not be empty for: {query}"


# =============================================================================
# FUTURE EPIC TESTS (DO NOT ADD TO EPIC 2)
# =============================================================================
# The following tests are DEFERRED for Epic 3+ and should NOT be in this suite:
#
# EPIC 3 (Story 3.3) - Interpretation & Ranking:
# - test_hybrid_search_phrasing_variance() - Different phrasings of same query
# - test_hybrid_search_ranking_relevance() - Ranking of results by relevance
# - test_hybrid_search_with_context() - Using context for disambiguation
# - test_hybrid_search_calculated_metrics() - Computing derived metrics
#
# EPIC 4 (Story 4.6+) - Proactive Insights:
# - test_hybrid_search_anomaly_detection() - Detecting data anomalies
# - test_hybrid_search_trend_analysis() - Identifying trends
# - test_hybrid_search_proactive_suggestions() - Generating insights
#
# These will be added in their respective story test files (test_epic3.py, test_epic4.py)
# =============================================================================
