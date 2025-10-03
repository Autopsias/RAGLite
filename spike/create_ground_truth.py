"""Create ground truth test set for Week 0 Integration Spike.

This script generates 15 representative Q&A pairs from the test financial document
and validates them against the MCP server.
"""

import asyncio
import json
from typing import List, Dict, Any

from mcp_server import execute_query, QueryRequest


# Ground truth Q&A pairs based on Secil Group Performance Review document
GROUND_TRUTH_QA = [
    {
        "id": 1,
        "question": "What are the main health and safety KPIs tracked by Secil Group?",
        "expected_keywords": ["frequency ratio", "safety", "health", "KPI"],
        "category": "safety_metrics",
        "difficulty": "easy"
    },
    {
        "id": 2,
        "question": "What is the EBITDA IFRS for cement operations?",
        "expected_keywords": ["EBITDA", "IFRS", "cement", "4017", "4338", "4263"],
        "category": "financial_performance",
        "difficulty": "medium"
    },
    {
        "id": 3,
        "question": "How do variable costs per ton compare across periods?",
        "expected_keywords": ["variable costs", "EUR/ton", "54.5", "56.9"],
        "category": "cost_analysis",
        "difficulty": "medium"
    },
    {
        "id": 4,
        "question": "What are the fixed costs per ton for operations?",
        "expected_keywords": ["fixed costs", "EUR/ton", "26.8", "22.1", "20.5"],
        "category": "cost_analysis",
        "difficulty": "easy"
    },
    {
        "id": 5,
        "question": "What is the distribution cost per ton?",
        "expected_keywords": ["distribution costs", "EUR/ton", "13.3", "14.3"],
        "category": "cost_analysis",
        "difficulty": "easy"
    },
    {
        "id": 6,
        "question": "How many employees are mentioned in the financial metrics?",
        "expected_keywords": ["employees", "2992", "3143", "2646"],
        "category": "workforce",
        "difficulty": "medium"
    },
    {
        "id": 7,
        "question": "What are the employee costs per ton?",
        "expected_keywords": ["employees", "EUR/ton", "5.7", "5.1", "3.9"],
        "category": "workforce",
        "difficulty": "medium"
    },
    {
        "id": 8,
        "question": "What is the unit margin in EUR per ton?",
        "expected_keywords": ["unit margin", "EUR/ton", "56.9", "54.6", "53.5"],
        "category": "margins",
        "difficulty": "medium"
    },
    {
        "id": 9,
        "question": "What are the renting costs mentioned in the document?",
        "expected_keywords": ["renting", "591", "489", "460"],
        "category": "operating_expenses",
        "difficulty": "easy"
    },
    {
        "id": 10,
        "question": "What is the variable contribution in thousands of EUR?",
        "expected_keywords": ["variable contribution", "12860", "12983", "12001"],
        "category": "financial_performance",
        "difficulty": "hard"
    },
    {
        "id": 11,
        "question": "What are the net transport costs?",
        "expected_keywords": ["net transport costs", "3036", "2194", "2182"],
        "category": "operating_expenses",
        "difficulty": "medium"
    },
    {
        "id": 12,
        "question": "What are the other variable costs per ton?",
        "expected_keywords": ["other variable costs", "EUR/ton", "10.6", "9.7", "7.5"],
        "category": "cost_analysis",
        "difficulty": "medium"
    },
    {
        "id": 13,
        "question": "What percentage change is shown for frequency ratios?",
        "expected_keywords": ["frequency ratio", "7.0%", "24.7%", "15.1%"],
        "category": "safety_metrics",
        "difficulty": "hard"
    },
    {
        "id": 14,
        "question": "What is the EBITDA IFRS margin percentage?",
        "expected_keywords": ["EBITDA", "IFRS", "margin", "38.3", "35.4", "40.0"],
        "category": "margins",
        "difficulty": "hard"
    },
    {
        "id": 15,
        "question": "What are the fuel costs mentioned in the operating expenses?",
        "expected_keywords": ["fuel", "46.1", "76", "71"],
        "category": "operating_expenses",
        "difficulty": "easy"
    }
]


async def validate_question(qa: Dict[str, Any], top_k: int = 5) -> Dict[str, Any]:
    """
    Validate a Q&A pair by running it through the query system.

    Args:
        qa: Q&A pair dictionary
        top_k: Number of results to retrieve

    Returns:
        Validation result with scores and matched keywords
    """
    request = QueryRequest(query=qa["question"], top_k=top_k)
    result = await execute_query(request)

    # Check if expected keywords appear in retrieved chunks
    all_text = " ".join([r.text.lower() for r in result.results])
    matched_keywords = [
        kw for kw in qa["expected_keywords"]
        if kw.lower() in all_text
    ]

    # Calculate match score
    match_score = len(matched_keywords) / len(qa["expected_keywords"]) if qa["expected_keywords"] else 0

    return {
        "question_id": qa["id"],
        "question": qa["question"],
        "category": qa["category"],
        "difficulty": qa["difficulty"],
        "results_count": result.results_count,
        "top_score": result.results[0].score if result.results else 0,
        "expected_keywords": qa["expected_keywords"],
        "matched_keywords": matched_keywords,
        "match_score": match_score,
        "success": match_score >= 0.3,  # At least 30% keywords matched
        "top_chunks": [
            {
                "score": r.score,
                "text_preview": r.text[:200],
                "chunk_index": r.chunk_index
            }
            for r in result.results[:2]  # Top 2 chunks
        ]
    }


async def create_ground_truth_set():
    """
    Create and validate the ground truth test set.
    """
    print("=" * 80)
    print("GROUND TRUTH TEST SET CREATION")
    print("=" * 80)
    print(f"\nTotal questions: {len(GROUND_TRUTH_QA)}\n")

    validation_results = []

    for i, qa in enumerate(GROUND_TRUTH_QA, 1):
        print(f"Validating Q{i}/{len(GROUND_TRUTH_QA)}: {qa['question'][:60]}...")
        result = await validate_question(qa)
        validation_results.append(result)

        status = "✓" if result["success"] else "✗"
        print(f"  {status} Score: {result['top_score']:.4f}, Match: {result['match_score']:.0%}")

    # Calculate statistics
    success_count = sum(1 for r in validation_results if r["success"])
    success_rate = success_count / len(validation_results) * 100
    avg_score = sum(r["top_score"] for r in validation_results) / len(validation_results)
    avg_match = sum(r["match_score"] for r in validation_results) / len(validation_results)

    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Success rate: {success_rate:.1f}% ({success_count}/{len(validation_results)})")
    print(f"Average retrieval score: {avg_score:.4f}")
    print(f"Average keyword match: {avg_match:.0%}")

    # Category breakdown
    categories = {}
    for r in validation_results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "success": 0}
        categories[cat]["total"] += 1
        if r["success"]:
            categories[cat]["success"] += 1

    print("\nBy category:")
    for cat, stats in sorted(categories.items()):
        rate = stats["success"] / stats["total"] * 100
        print(f"  {cat}: {rate:.0f}% ({stats['success']}/{stats['total']})")

    # Save ground truth set
    output = {
        "metadata": {
            "description": "Ground truth test set for RAGLite Week 0 Integration Spike",
            "document": "2025-08 Performance Review CONSO_v2.pdf",
            "total_questions": len(GROUND_TRUTH_QA),
            "validation_date": "2025-10-03",
            "success_rate": f"{success_rate:.1f}%",
            "avg_retrieval_score": f"{avg_score:.4f}",
            "avg_keyword_match": f"{avg_match:.0%}"
        },
        "questions": GROUND_TRUTH_QA,
        "validation_results": validation_results,
        "statistics": {
            "total": len(validation_results),
            "successful": success_count,
            "success_rate": success_rate,
            "average_score": avg_score,
            "average_match": avg_match,
            "by_category": categories
        }
    }

    with open("tests/ground_truth.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Ground truth set saved to: tests/ground_truth.json")

    return validation_results, success_rate


async def main():
    """Main entry point."""
    results, success_rate = await create_ground_truth_set()

    if success_rate >= 70:
        print(f"\n✓ SUCCESS: {success_rate:.1f}% ≥ 70% threshold - Ready for Phase 1!")
    elif success_rate >= 50:
        print(f"\n⚠️  REASSESS: {success_rate:.1f}% (50-69%) - Investigate before Phase 1")
    else:
        print(f"\n🛑 NO-GO: {success_rate:.1f}% < 50% - Technology stack unsuitable")


if __name__ == "__main__":
    asyncio.run(main())
