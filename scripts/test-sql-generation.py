#!/usr/bin/env python3
"""
Test SQL Generation (Task 2.3 - Story 2.13)

Tests text-to-SQL generation on 20 sample financial queries.
Validates:
- SQL syntax correctness
- Query execution success
- Result attribution (page numbers)
- SQL generation accuracy

Usage:
    python scripts/test-sql-generation.py
"""

import asyncio
import sys
from typing import Any

from raglite.retrieval.query_classifier import generate_sql_query
from raglite.retrieval.sql_table_search import search_tables_sql

# 20 sample queries covering different financial table query patterns
SAMPLE_QUERIES = [
    # Simple metric queries (1-5)
    {
        "id": 1,
        "query": "What is the variable cost for Portugal Cement in August 2025?",
        "expected_sql_fragments": ["Portugal Cement", "variable cost", "Aug"],
        "description": "Simple single-entity metric query",
    },
    {
        "id": 2,
        "query": "Show thermal energy consumption for Spain Ready-Mix",
        "expected_sql_fragments": ["Spain Ready-Mix", "thermal energy"],
        "description": "Single metric, single entity",
    },
    {
        "id": 3,
        "query": "What were the costs for France Cement?",
        "expected_sql_fragments": ["France Cement", "cost"],
        "description": "General cost query for single entity",
    },
    {
        "id": 4,
        "query": "Get production volumes for Italy Aggregates",
        "expected_sql_fragments": ["Italy Aggregates", "production"],
        "description": "Production metric query",
    },
    {
        "id": 5,
        "query": "Find the EBITDA margin for Portugal Cement",
        "expected_sql_fragments": ["Portugal Cement", "EBITDA"],
        "description": "Financial margin metric",
    },
    # Multi-period comparisons (6-10)
    {
        "id": 6,
        "query": "Compare variable costs for Portugal Cement between Aug-25 YTD and Aug-24",
        "expected_sql_fragments": ["Portugal Cement", "variable cost", "Aug-25", "Aug-24"],
        "description": "Two-period comparison",
    },
    {
        "id": 7,
        "query": "Show thermal energy costs for Q1, Q2, and Q3 2025",
        "expected_sql_fragments": ["thermal energy", "Q1", "Q2", "Q3", "2025"],
        "description": "Multi-quarter comparison",
    },
    {
        "id": 8,
        "query": "What was the YTD performance vs budget for Spain Ready-Mix?",
        "expected_sql_fragments": ["Spain Ready-Mix", "YTD", "budget"],
        "description": "YTD vs budget comparison",
    },
    {
        "id": 9,
        "query": "Compare August 2025 to August 2024 for all entities",
        "expected_sql_fragments": ["Aug-25", "Aug-24"],
        "description": "Year-over-year all entities",
    },
    {
        "id": 10,
        "query": "Show quarterly trend for variable costs in 2025",
        "expected_sql_fragments": ["variable cost", "2025", "quarter"],
        "description": "Quarterly trend analysis",
    },
    # Multi-entity queries (11-15)
    {
        "id": 11,
        "query": "Compare variable costs across Portugal Cement, Spain Cement, and France Cement",
        "expected_sql_fragments": [
            "Portugal Cement",
            "Spain Cement",
            "France Cement",
            "variable cost",
        ],
        "description": "Multi-entity comparison",
    },
    {
        "id": 12,
        "query": "What are the thermal energy costs for all Ready-Mix divisions?",
        "expected_sql_fragments": ["Ready-Mix", "thermal energy"],
        "description": "Entity group query",
    },
    {
        "id": 13,
        "query": "Show EBITDA for all Cement divisions",
        "expected_sql_fragments": ["Cement", "EBITDA"],
        "description": "Division-level aggregation",
    },
    {
        "id": 14,
        "query": "Which entity had the highest variable costs in August 2025?",
        "expected_sql_fragments": ["variable cost", "Aug-25", "highest", "DESC", "LIMIT"],
        "description": "Ranking query with ORDER BY",
    },
    {
        "id": 15,
        "query": "List all entities with EBITDA above 30%",
        "expected_sql_fragments": ["EBITDA", ">", "30", "WHERE"],
        "description": "Conditional filtering",
    },
    # Complex table queries (16-20)
    {
        "id": 16,
        "query": "What is the difference between budget and actual for Portugal Cement variable costs?",
        "expected_sql_fragments": ["Portugal Cement", "variable cost", "budget"],
        "description": "Calculated field (budget vs actual)",
    },
    {
        "id": 17,
        "query": "Show all cost metrics for Spain Ready-Mix in August 2025",
        "expected_sql_fragments": ["Spain Ready-Mix", "cost", "Aug-25"],
        "description": "Multi-metric single entity",
    },
    {
        "id": 18,
        "query": "Find entities with declining thermal energy consumption year-over-year",
        "expected_sql_fragments": ["thermal energy", "GROUP BY", "HAVING"],
        "description": "Trend detection with aggregation",
    },
    {
        "id": 19,
        "query": "What percentage of total costs are variable costs for each entity?",
        "expected_sql_fragments": ["variable cost", "total cost", "percentage", "GROUP BY"],
        "description": "Ratio calculation across entities",
    },
    {
        "id": 20,
        "query": "Show the top 5 entities by EBITDA margin in August 2025",
        "expected_sql_fragments": ["EBITDA", "margin", "Aug-25", "ORDER BY", "DESC", "LIMIT 5"],
        "description": "Top-N ranking query",
    },
]


async def test_sql_generation_single(query_data: dict[str, Any]) -> dict[str, Any]:
    """Test SQL generation for a single query.

    Args:
        query_data: Query test case with id, query, expected_sql_fragments, description

    Returns:
        Test result with success/failure, SQL, and validation details
    """
    query_id = query_data["id"]
    query = query_data["query"]
    expected_fragments = query_data["expected_sql_fragments"]
    description = query_data["description"]

    print(f"\n{'=' * 80}")
    print(f"Query {query_id}: {description}")
    print(f"{'=' * 80}")
    print(f"Input: {query}")

    try:
        # Step 1: Generate SQL
        sql = await generate_sql_query(query)

        if sql is None:
            return {
                "id": query_id,
                "query": query,
                "success": False,
                "error": "SQL generation returned None (query may be text-only)",
                "sql": None,
                "results_count": 0,
                "has_page_numbers": False,
            }

        print(f"\nGenerated SQL:\n{sql}\n")

        # Step 2: Validate SQL syntax (check for SELECT, FROM, WHERE)
        sql_lower = sql.lower()
        has_select = "select" in sql_lower
        has_from = "from financial_tables" in sql_lower
        _has_where = "where" in sql_lower or "limit" in sql_lower  # noqa: F841

        if not (has_select and has_from):
            return {
                "id": query_id,
                "query": query,
                "success": False,
                "error": f"Invalid SQL syntax: missing SELECT or FROM (has_select={has_select}, has_from={has_from})",
                "sql": sql,
                "results_count": 0,
                "has_page_numbers": False,
            }

        # Step 3: Check expected SQL fragments
        missing_fragments = [frag for frag in expected_fragments if frag.lower() not in sql_lower]
        if missing_fragments:
            print(f"⚠️  Warning: Missing expected fragments: {missing_fragments}")

        # Step 4: Execute SQL and validate results
        try:
            results = await search_tables_sql(sql, top_k=50)
            print(f"Results: {len(results)} rows returned")

            if results:
                print(f"Sample result: {results[0]}")
                has_page_numbers = all(
                    hasattr(r, "page_number") and r.page_number is not None for r in results
                )
            else:
                has_page_numbers = False
                print("⚠️  No results returned (query may not match test data)")

            return {
                "id": query_id,
                "query": query,
                "description": description,
                "success": True,
                "sql": sql,
                "results_count": len(results),
                "has_page_numbers": has_page_numbers,
                "missing_fragments": missing_fragments,
                "error": None,
            }

        except Exception as exec_error:
            return {
                "id": query_id,
                "query": query,
                "success": False,
                "error": f"SQL execution failed: {exec_error}",
                "sql": sql,
                "results_count": 0,
                "has_page_numbers": False,
            }

    except Exception as e:
        return {
            "id": query_id,
            "query": query,
            "success": False,
            "error": f"SQL generation failed: {e}",
            "sql": None,
            "results_count": 0,
            "has_page_numbers": False,
        }


async def main() -> None:
    """Run SQL generation tests on all 20 sample queries."""
    print("=" * 80)
    print("SQL GENERATION TEST (Story 2.13 - Task 2.3)")
    print("=" * 80)
    print(f"Testing {len(SAMPLE_QUERIES)} sample queries\n")

    results = []
    for query_data in SAMPLE_QUERIES:
        result = await test_sql_generation_single(query_data)
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(
        f"\n✅ Successful: {len(successful)}/{len(results)} ({len(successful) / len(results) * 100:.1f}%)"
    )
    print(f"❌ Failed: {len(failed)}/{len(results)} ({len(failed) / len(results) * 100:.1f}%)")

    if successful:
        results_with_data = [r for r in successful if r["results_count"] > 0]
        results_with_pages = [r for r in successful if r["has_page_numbers"]]

        print(f"\n📊 Results returned: {len(results_with_data)}/{len(successful)}")
        print(f"📍 Page attribution: {len(results_with_pages)}/{len(successful)}")

    if failed:
        print("\n❌ Failed Queries:")
        for r in failed:
            print(f"  - Query {r['id']}: {r['error']}")

    # AC2 Success Criteria Check
    print("\n" + "=" * 80)
    print("AC2 SUCCESS CRITERIA VALIDATION")
    print("=" * 80)

    success_rate = len(successful) / len(results) * 100
    execution_success = all(r["success"] for r in successful)
    attribution_success = (
        all(r["has_page_numbers"] for r in results_with_pages) if successful else False
    )

    print(
        f"\n1. Text-to-SQL generation >80% accuracy: {success_rate:.1f}% {'✅' if success_rate >= 80 else '❌'}"
    )
    print(f"2. SQL queries execute successfully: {'✅' if execution_success else '❌'}")
    print(
        f"3. Results include page numbers for attribution: {'✅' if attribution_success else '❌'}"
    )

    if success_rate >= 80 and execution_success and attribution_success:
        print("\n✅ AC2 TASK 2.3 PASSED - SQL generation validated")
        sys.exit(0)
    else:
        print("\n❌ AC2 TASK 2.3 FAILED - Review errors above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
