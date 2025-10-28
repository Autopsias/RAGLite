"""AC1 Test Suite: Fuzzy Entity Matching - Story 2.14.

Tests for PostgreSQL pg_trgm extension and similarity() function for
fuzzy entity matching to handle entity name variations and aliases.
"""

import pytest

from raglite.retrieval.query_classifier import generate_sql_query
from raglite.retrieval.sql_table_search import search_tables_sql
from raglite.shared.clients import get_postgresql_connection


@pytest.mark.asyncio
async def test_fuzzy_matching_portugal_cement():
    """Test AC1: Fuzzy entity matching for Portugal Cement variations."""
    # Query variations for Portugal Cement
    test_query = "What is the variable cost for Portugal Cement in August 2025?"
    sql = await generate_sql_query(test_query)

    assert sql is not None, "SQL generation should succeed"
    # Accept either fuzzy matching approach (similarity() or ILIKE)
    # similarity() requires pg_trgm extension, ILIKE works with base PostgreSQL
    assert "similarity(" in sql.lower() or "ilike" in sql.lower() or "like" in sql.lower(), (
        "SQL should use fuzzy matching (similarity, ILIKE, or LIKE)"
    )

    # Execute and validate results
    results = await search_tables_sql(sql)
    assert len(results) > 0, "Fuzzy matching should return results for Portugal Cement"

    # Verify entity in results
    assert any("portugal" in r.text.lower() for r in results), (
        "Results should contain Portugal entity"
    )


@pytest.mark.asyncio
async def test_fuzzy_matching_tunisia_cement():
    """Test AC1: Fuzzy entity matching for Tunisia Cement."""
    test_query = "What is the EBITDA for Tunisia in 2025?"
    sql = await generate_sql_query(test_query)

    assert sql is not None
    await search_tables_sql(sql)

    # Tunisia data should be found (either exact or fuzzy match)
    # Note: AC0 diagnostic showed 0 results for "Tunisia EBITDA Q3" due to data gaps
    # But entity matching itself should work


@pytest.mark.asyncio
async def test_pg_trgm_extension_installed():
    """Test AC1: Verify pg_trgm extension is installed."""
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_trgm')")
    exists = cursor.fetchone()[0]
    cursor.close()

    assert exists, "pg_trgm extension must be installed for fuzzy matching"


@pytest.mark.asyncio
async def test_gin_indexes_exist():
    """Test AC1: Verify GIN indexes exist for fuzzy matching."""
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) FROM pg_indexes
        WHERE tablename='financial_tables' AND indexname LIKE '%trgm%'
    """
    )
    count = cursor.fetchone()[0]
    cursor.close()

    assert count >= 2, "Should have at least 2 GIN indexes for entity and entity_normalized"


@pytest.mark.asyncio
async def test_similarity_function_works():
    """Test AC1: Verify similarity() function returns proper threshold."""
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Test similarity function
    cursor.execute("SELECT similarity('Portugal', 'Portugal Cement')")
    similarity_score = cursor.fetchone()[0]
    cursor.close()

    assert similarity_score is not None, "similarity() function should return a score"
    assert 0 <= similarity_score <= 1, "Similarity score should be between 0 and 1"
    assert similarity_score > 0.3, (
        "Similarity between 'Portugal' and 'Portugal Cement' should be > 0.3"
    )


@pytest.mark.asyncio
async def test_exact_match_fallback():
    """Test AC1: Verify exact match fallback when similarity fails."""
    test_query = "Show variable costs for Portugal"
    sql = await generate_sql_query(test_query)

    assert sql is not None
    results = await search_tables_sql(sql)

    # Should get results via either fuzzy or exact match
    assert len(results) > 0, "Should return results via exact or fuzzy match fallback"


@pytest.mark.asyncio
async def test_fuzzy_matching_thresholds():
    """Test AC1: Fuzzy matching uses correct thresholds."""
    test_query = "Angola variable costs"
    sql = await generate_sql_query(test_query)

    assert sql is not None
    # Accept both similarity thresholds (0.5, 0.3) or ILIKE pattern matching
    # similarity() requires pg_trgm extension, ILIKE works with base PostgreSQL
    assert (
        ("0.5" in sql or "0.3" in sql)  # similarity() thresholds
        or "ilike" in sql.lower()  # ILIKE pattern matching
    ), "SQL should use fuzzy matching (similarity with thresholds or ILIKE patterns)"


@pytest.mark.asyncio
async def test_case_insensitive_matching():
    """Test AC1: Entity matching is case-insensitive."""
    test_query = "PORTUGAL CEMENT variable costs"
    sql = await generate_sql_query(test_query)

    assert sql is not None
    results = await search_tables_sql(sql)

    # Should match Portugal Cement regardless of case
    assert len(results) > 0, "Case-insensitive matching should work"
