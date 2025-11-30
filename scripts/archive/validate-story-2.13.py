#!/usr/bin/env python3
"""
Story 2.13 AC4: Accuracy Validation for SQL Table Search Integration

Validates SQL routing accuracy with 50+ ground truth queries:
- 20 SQL_ONLY queries (table data lookups)
- 15 VECTOR_ONLY queries (existing ground truth text queries)
- 15 HYBRID queries (combination of table + text)

Success Criteria (AC4):
- Overall retrieval accuracy ≥70%
- SQL_ONLY accuracy ≥75% (production baseline: 70-80%)
- VECTOR_ONLY accuracy maintained (≥60% baseline)
- HYBRID accuracy ≥65%
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from raglite.retrieval.query_classifier import classify_query
from raglite.retrieval.search import hybrid_search

# SQL_ONLY test queries (structured table lookups)
SQL_QUERIES = [
    {
        "id": "SQL-1",
        "query": "What is the variable cost for Portugal Cement in August 2025?",
        "expected_keywords": ["variable cost", "Portugal", "EUR/ton"],
        "expected_page": [20, 21],  # Cost per ton table
        "query_type": "SQL_ONLY",
        "difficulty": "easy",
    },
    {
        "id": "SQL-2",
        "query": "What is the EBITDA for Spain Ready-Mix?",
        "expected_keywords": ["EBITDA", "Spain Ready-Mix"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "SQL_ONLY",
        "difficulty": "easy",
    },
    {
        "id": "SQL-3",
        "query": "Show thermal energy consumption for Portugal Cement",
        "expected_keywords": ["thermal energy", "Portugal Cement"],
        "expected_page": [20, 21],  # Cost per ton table - Thermal Energy Eur/ton
        "query_type": "SQL_ONLY",
        "difficulty": "easy",
    },
    {
        "id": "SQL-4",
        "query": "What were the costs for France Cement in August 2025?",
        "expected_keywords": ["France Cement", "cost", "Aug"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "SQL_ONLY",
        "difficulty": "medium",
    },
    {
        "id": "SQL-5",
        "query": "Get production volumes for Italy Aggregates",
        "expected_keywords": ["production", "Italy Aggregates"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "SQL_ONLY",
        "difficulty": "medium",
    },
    {
        "id": "SQL-6",
        "query": "Compare variable costs for Portugal Cement between Aug-25 YTD and Aug-24",
        "expected_keywords": ["variable cost", "Portugal", "Aug-25", "Aug-24"],
        "expected_page": [20, 21],  # Cost per ton table - Variable Cost Eur/ton
        "query_type": "SQL_ONLY",
        "difficulty": "hard",
    },
    {
        "id": "SQL-7",
        "query": "Show thermal energy costs for Q1, Q2, and Q3 2025",
        "expected_keywords": ["thermal energy", "Q1", "Q2", "Q3"],
        "expected_page": [20, 21],  # Cost per ton table - Thermal Energy Eur/ton
        "query_type": "SQL_ONLY",
        "difficulty": "hard",
    },
    {
        "id": "SQL-8",
        "query": "What was the YTD performance vs budget for Spain Ready-Mix?",
        "expected_keywords": ["YTD", "budget", "Spain Ready-Mix"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "SQL_ONLY",
        "difficulty": "hard",
    },
    {
        "id": "SQL-9",
        "query": "Compare August 2025 to August 2024 for all entities",
        "expected_keywords": ["Aug-25", "Aug-24"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "SQL_ONLY",
        "difficulty": "hard",
    },
    {
        "id": "SQL-10",
        "query": "What are the variable costs across Portugal Cement, Spain Cement, and France Cement?",
        "expected_keywords": ["variable cost", "Portugal", "Spain", "France"],
        "expected_page": [20, 21],  # Cost per ton table - Variable Cost Eur/ton
        "query_type": "SQL_ONLY",
        "difficulty": "hard",
    },
    {
        "id": "SQL-11",
        "query": "Show EBITDA for all Cement divisions",
        "expected_keywords": ["EBITDA", "Cement"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "SQL_ONLY",
        "difficulty": "medium",
    },
    {
        "id": "SQL-12",
        "query": "Which entity had the highest variable costs in August 2025?",
        "expected_keywords": ["variable cost", "Aug-25", "highest"],
        "expected_page": [20, 21],  # Cost per ton table - Variable Cost Eur/ton
        "query_type": "SQL_ONLY",
        "difficulty": "hard",
    },
    {
        "id": "SQL-13",
        "query": "List all entities with EBITDA above 30%",
        "expected_keywords": ["EBITDA", "30"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "SQL_ONLY",
        "difficulty": "hard",
    },
    {
        "id": "SQL-14",
        "query": "What is the difference between budget and actual for Portugal Cement variable costs?",
        "expected_keywords": ["budget", "actual", "Portugal Cement", "variable cost"],
        "expected_page": [
            20,
            21,
        ],  # Cost per ton table - Variable Cost Eur/ton with Budget comparison
        "query_type": "SQL_ONLY",
        "difficulty": "hard",
    },
    {
        "id": "SQL-15",
        "query": "Show all cost metrics for Spain Ready-Mix in August 2025",
        "expected_keywords": ["cost", "Spain Ready-Mix", "Aug-25"],
        "expected_page": [20, 21],  # Cost per ton table - multiple cost metrics
        "query_type": "SQL_ONLY",
        "difficulty": "medium",
    },
    {
        "id": "SQL-16",
        "query": "What percentage of total costs are variable costs for each entity?",
        "expected_keywords": ["variable cost", "total cost", "percentage"],
        "expected_page": [20, 21],  # Cost per ton table - Variable Cost Eur/ton
        "query_type": "SQL_ONLY",
        "difficulty": "hard",
    },
    {
        "id": "SQL-17",
        "query": "Show the top 5 entities by EBITDA margin in August 2025",
        "expected_keywords": ["EBITDA", "margin", "Aug-25", "top 5"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "SQL_ONLY",
        "difficulty": "hard",
    },
    {
        "id": "SQL-18",
        "query": "What are the fixed costs per ton for Portugal Cement?",
        "expected_keywords": ["fixed cost", "Portugal Cement", "EUR/ton"],
        "expected_page": [20, 21],  # Cost per ton table - Fixed Costs Eur/ton
        "query_type": "SQL_ONLY",
        "difficulty": "easy",
    },
    {
        "id": "SQL-19",
        "query": "Compare production between Spain Cement and France Cement",
        "expected_keywords": ["production", "Spain Cement", "France Cement"],
        "expected_page": [20, 21],  # Cost per ton table - Sales Volumes kton (production data)
        "query_type": "SQL_ONLY",
        "difficulty": "medium",
    },
    {
        "id": "SQL-20",
        "query": "What is the distribution cost for Italy Aggregates?",
        "expected_keywords": ["distribution cost", "Italy Aggregates"],
        "expected_page": [20, 21],  # Cost per ton table - Sales&Distribution Fixed Costs Eur/ton
        "query_type": "SQL_ONLY",
        "difficulty": "easy",
    },
]

# HYBRID test queries (table + text context)
HYBRID_QUERIES = [
    {
        "id": "HYB-1",
        "query": "Compare EBITDA margins between Portugal and Spain cement divisions and explain the drivers",
        "expected_keywords": ["EBITDA", "Portugal", "Spain", "cement", "margin"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-2",
        "query": "What are the variable costs for Portugal Cement and what factors influence them?",
        "expected_keywords": ["variable cost", "Portugal Cement", "factors"],
        "expected_page": [20, 21],  # Cost per ton table - Variable Cost Eur/ton
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-3",
        "query": "Show thermal energy consumption trends and sustainability initiatives",
        "expected_keywords": ["thermal energy", "sustainability", "trends"],
        "expected_page": [20, 21],  # Cost per ton table - Thermal Energy Eur/ton
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-4",
        "query": "How do production volumes relate to operational efficiency across entities?",
        "expected_keywords": ["production", "efficiency", "operational"],
        "expected_page": [20, 21],  # Cost per ton table - Sales Volumes kton (production data)
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-5",
        "query": "What are the cost trends for cement operations and key cost drivers?",
        "expected_keywords": ["cost", "cement", "trends", "drivers"],
        "expected_page": [20, 21],  # Cost per ton table - multiple cost metrics
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-6",
        "query": "Compare YTD performance to budget across entities and explain variances",
        "expected_keywords": ["YTD", "budget", "variance", "performance"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-7",
        "query": "What are the EBITDA figures for Ready-Mix divisions and profitability analysis?",
        "expected_keywords": ["EBITDA", "Ready-Mix", "profitability"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-8",
        "query": "Show variable cost trends over quarters with seasonal analysis",
        "expected_keywords": ["variable cost", "quarter", "seasonal", "trends"],
        "expected_page": [20, 21],  # Cost per ton table - Variable Cost Eur/ton
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-9",
        "query": "Compare fixed costs across entities and explain operational differences",
        "expected_keywords": ["fixed cost", "operational", "differences"],
        "expected_page": [20, 21],  # Cost per ton table - Fixed Costs Eur/ton
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-10",
        "query": "What are the thermal energy costs and energy efficiency initiatives?",
        "expected_keywords": ["thermal energy", "cost", "efficiency", "initiatives"],
        "expected_page": [20, 21],  # Cost per ton table - Thermal Energy Eur/ton
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-11",
        "query": "Show production metrics for Aggregates and market analysis",
        "expected_keywords": ["production", "Aggregates", "market"],
        "expected_page": [20, 21],  # Cost per ton table - Sales Volumes kton (production data)
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-12",
        "query": "Compare distribution costs across divisions with logistics insights",
        "expected_keywords": ["distribution", "cost", "logistics"],
        "expected_page": [20, 21],  # Cost per ton table - Sales&Distribution Fixed Costs Eur/ton
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-13",
        "query": "What are the employee cost metrics and workforce trends?",
        "expected_keywords": ["employee", "cost", "workforce", "trends"],
        "expected_page": [20, 21],  # Cost per ton table - Employee Eur/ton
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-14",
        "query": "Show EBITDA margins for top performing entities with success factors",
        "expected_keywords": ["EBITDA", "margin", "top", "success"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
    {
        "id": "HYB-15",
        "query": "Compare budget vs actual performance with strategic implications",
        "expected_keywords": ["budget", "actual", "strategic", "performance"],
        "expected_page": [6, 7, 8, 9],
        "query_type": "HYBRID",
        "difficulty": "hard",
    },
]


async def load_ground_truth_queries() -> list[dict[str, Any]]:
    """Load existing ground truth queries (VECTOR_ONLY type)."""
    gt_path = Path("tests/ground_truth.json")
    if not gt_path.exists():
        print(f"Warning: Ground truth file not found at {gt_path}")
        return []

    with open(gt_path) as f:
        data = json.load(f)

    # Mark existing queries as VECTOR_ONLY
    questions = data.get("questions", [])
    for q in questions:
        q["query_type"] = "VECTOR_ONLY"
        q["id"] = f"VEC-{q['id']}"
        q["query"] = q["question"]

    return questions[:15]  # Use first 15 vector queries


async def validate_query(query_data: dict[str, Any]) -> dict[str, Any]:
    """Validate a single query and measure accuracy.

    Args:
        query_data: Query test case with id, query, expected_keywords, etc.

    Returns:
        Validation result with success/failure and accuracy metrics
    """
    query_id = query_data["id"]
    query = query_data["query"]
    expected_keywords = query_data.get("expected_keywords", [])
    expected_page = query_data.get("expected_page", [])
    expected_type = query_data["query_type"]

    print(f"\n{'=' * 80}")
    print(f"Query {query_id}: {query_data.get('difficulty', 'unknown')}")
    print(f"{'=' * 80}")
    print(f"Query: {query}")
    print(f"Expected Type: {expected_type}")

    try:
        # Classify query type
        actual_type = classify_query(query)
        type_correct = actual_type.value == expected_type.lower().replace("_", "_")

        print(f"Classified Type: {actual_type.value}")
        print(f"Type Classification: {'✅ CORRECT' if type_correct else '❌ INCORRECT'}")

        # Execute search with SQL routing
        results = await hybrid_search(query, top_k=5, enable_sql_tables=True)

        if not results:
            return {
                "id": query_id,
                "query": query,
                "success": False,
                "accuracy": 0.0,
                "error": "No results returned",
                "query_type": expected_type,
                "type_correct": type_correct,
            }

        # Check keyword matches in top result
        top_result_text = results[0].text.lower()
        keyword_matches = sum(1 for kw in expected_keywords if kw.lower() in top_result_text)
        keyword_accuracy = keyword_matches / len(expected_keywords) if expected_keywords else 1.0

        # Check page number accuracy
        page_correct = results[0].page_number in expected_page if expected_page else True

        # Overall accuracy: weighted combination
        accuracy = (keyword_accuracy * 0.7) + (1.0 if page_correct else 0.0) * 0.3

        print(f"\nResults: {len(results)} returned")
        print(f"Top Result Score: {results[0].score:.4f}")
        print(f"Page: {results[0].page_number} (Expected: {expected_page})")
        print(
            f"Keyword Matches: {keyword_matches}/{len(expected_keywords)} ({keyword_accuracy * 100:.1f}%)"
        )
        print(f"Overall Accuracy: {accuracy * 100:.1f}%")

        return {
            "id": query_id,
            "query": query,
            "success": accuracy >= 0.5,  # 50% threshold for individual query
            "accuracy": accuracy,
            "keyword_matches": keyword_matches,
            "total_keywords": len(expected_keywords),
            "page_correct": page_correct,
            "query_type": expected_type,
            "type_correct": type_correct,
            "top_score": results[0].score,
        }

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {
            "id": query_id,
            "query": query,
            "success": False,
            "accuracy": 0.0,
            "error": str(e),
            "query_type": expected_type,
            "type_correct": False,
        }


async def main() -> None:
    """Run Story 2.13 AC4 validation with 50+ queries."""
    print("=" * 80)
    print("STORY 2.13 AC4: SQL TABLE SEARCH ACCURACY VALIDATION")
    print("=" * 80)

    # Load all query sets
    vector_queries = await load_ground_truth_queries()
    all_queries = SQL_QUERIES + HYBRID_QUERIES + vector_queries

    print(f"\nTotal Queries: {len(all_queries)}")
    print(f"  - SQL_ONLY: {len(SQL_QUERIES)}")
    print(f"  - HYBRID: {len(HYBRID_QUERIES)}")
    print(f"  - VECTOR_ONLY: {len(vector_queries)}")

    # Validate all queries
    results = []
    for query_data in all_queries:
        result = await validate_query(query_data)
        results.append(result)

    # Compute metrics by query type
    print("\n" + "=" * 80)
    print("RESULTS BY QUERY TYPE")
    print("=" * 80)

    for query_type in ["SQL_ONLY", "HYBRID", "VECTOR_ONLY"]:
        type_results = [r for r in results if r["query_type"] == query_type]
        if not type_results:
            continue

        successful = [r for r in type_results if r["success"]]
        avg_accuracy = sum(r["accuracy"] for r in type_results) / len(type_results)
        type_correct = sum(1 for r in type_results if r.get("type_correct", False))

        print(f"\n{query_type}:")
        print(f"  Queries: {len(type_results)}")
        print(
            f"  Successful: {len(successful)}/{len(type_results)} ({len(successful) / len(type_results) * 100:.1f}%)"
        )
        print(f"  Avg Accuracy: {avg_accuracy * 100:.1f}%")
        print(
            f"  Type Classification: {type_correct}/{len(type_results)} ({type_correct / len(type_results) * 100:.1f}%)"
        )

    # Overall metrics
    print("\n" + "=" * 80)
    print("OVERALL RESULTS")
    print("=" * 80)

    successful = [r for r in results if r["success"]]
    overall_accuracy = sum(r["accuracy"] for r in results) / len(results)

    print(
        f"\nSuccessful Queries: {len(successful)}/{len(results)} ({len(successful) / len(results) * 100:.1f}%)"
    )
    print(f"Overall Accuracy: {overall_accuracy * 100:.1f}%")

    # AC4 Success Criteria
    print("\n" + "=" * 80)
    print("AC4 SUCCESS CRITERIA")
    print("=" * 80)

    sql_results = [r for r in results if r["query_type"] == "SQL_ONLY"]
    vector_results = [r for r in results if r["query_type"] == "VECTOR_ONLY"]
    hybrid_results = [r for r in results if r["query_type"] == "HYBRID"]

    sql_accuracy = sum(r["accuracy"] for r in sql_results) / len(sql_results) if sql_results else 0
    vector_accuracy = (
        sum(r["accuracy"] for r in vector_results) / len(vector_results) if vector_results else 0
    )
    hybrid_accuracy = (
        sum(r["accuracy"] for r in hybrid_results) / len(hybrid_results) if hybrid_results else 0
    )

    criteria_met = []

    print(
        f"\n1. Overall accuracy ≥70%: {overall_accuracy * 100:.1f}% {'✅' if overall_accuracy >= 0.70 else '❌'}"
    )
    criteria_met.append(overall_accuracy >= 0.70)

    print(
        f"2. SQL_ONLY accuracy ≥75%: {sql_accuracy * 100:.1f}% {'✅' if sql_accuracy >= 0.75 else '❌'}"
    )
    criteria_met.append(sql_accuracy >= 0.75)

    print(
        f"3. VECTOR_ONLY accuracy ≥60%: {vector_accuracy * 100:.1f}% {'✅' if vector_accuracy >= 0.60 else '❌'}"
    )
    criteria_met.append(vector_accuracy >= 0.60)

    print(
        f"4. HYBRID accuracy ≥65%: {hybrid_accuracy * 100:.1f}% {'✅' if hybrid_accuracy >= 0.65 else '❌'}"
    )
    criteria_met.append(hybrid_accuracy >= 0.65)

    # Decision gate
    if all(criteria_met):
        print("\n✅ AC4 VALIDATION PASSED - Story 2.13 COMPLETE")
        print("🎉 Epic 2 Phase 2A-REVISED: SQL Table Search integration successful!")
        sys.exit(0)
    else:
        print("\n❌ AC4 VALIDATION FAILED - Review accuracy improvements needed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
