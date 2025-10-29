#!/usr/bin/env python3
"""
Quick validation of SQL routing integration (Story 2.13 AC3)

Tests three query types:
- TABLE: Routes to SQL-only search
- TEXT: Routes to vector+BM25 search
- HYBRID: Routes to SQL+Vector fusion
"""

import asyncio

from raglite.retrieval.search import hybrid_search


async def test_sql_routing():
    """Test SQL routing with different query types."""

    # Test 1: TABLE query (should route to SQL-only)
    print("\n" + "=" * 80)
    print("TEST 1: TABLE Query - SQL-Only Routing")
    print("=" * 80)
    table_query = "What is the variable cost for Portugal Cement in August 2025?"
    print(f"Query: {table_query}\n")

    results = await hybrid_search(table_query, top_k=5, enable_sql_tables=True)

    print(f"Results count: {len(results)}")
    if results:
        print(f"Top result: {results[0].text[:200]}...")
        print(f"Score: {results[0].score}")
        print(f"Page: {results[0].page_number}")

    # Test 2: TEXT query (should route to vector+BM25)
    print("\n" + "=" * 80)
    print("TEST 2: TEXT Query - Vector+BM25 Routing")
    print("=" * 80)
    text_query = "What are the main sustainability initiatives mentioned?"
    print(f"Query: {text_query}\n")

    results = await hybrid_search(text_query, top_k=5, enable_sql_tables=True)

    print(f"Results count: {len(results)}")
    if results:
        print(f"Top result: {results[0].text[:200]}...")
        print(f"Score: {results[0].score}")
        print(f"Page: {results[0].page_number}")

    # Test 3: HYBRID query (should route to SQL+Vector fusion)
    print("\n" + "=" * 80)
    print("TEST 3: HYBRID Query - SQL+Vector Fusion")
    print("=" * 80)
    hybrid_query = "Compare EBITDA margins between Portugal and Spain cement divisions"
    print(f"Query: {hybrid_query}\n")

    results = await hybrid_search(hybrid_query, top_k=5, enable_sql_tables=True)

    print(f"Results count: {len(results)}")
    if results:
        print(f"Top result: {results[0].text[:200]}...")
        print(f"Score: {results[0].score}")
        print(f"Page: {results[0].page_number}")

    # Test 4: Disabled SQL routing (fallback to vector+BM25)
    print("\n" + "=" * 80)
    print("TEST 4: SQL Routing Disabled - Vector+BM25 Fallback")
    print("=" * 80)
    print(f"Query: {table_query} (same as Test 1)\n")

    results = await hybrid_search(table_query, top_k=5, enable_sql_tables=False)

    print(f"Results count: {len(results)}")
    if results:
        print(f"Top result: {results[0].text[:200]}...")
        print(f"Score: {results[0].score}")
        print(f"Page: {results[0].page_number}")

    print("\n" + "=" * 80)
    print("✅ SQL ROUTING TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_sql_routing())
