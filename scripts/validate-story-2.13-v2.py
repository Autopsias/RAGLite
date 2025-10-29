#!/usr/bin/env python3
"""
Story 2.13 AC4 Validation Script V2 - Answer Quality Testing

This is the NEW validation script that tests RAG answer quality, not just page retrieval.

Key Differences from V1:
- V1: Tests if correct pages are retrieved and keywords are present
- V2: Tests if correct ANSWER is generated with accurate values

Usage:
    python scripts/validate-story-2.13-v2.py [--queries N] [--verbose]

Options:
    --queries N    Run only first N queries (default: all)
    --verbose     Show detailed validation results for each query

Story 2.13 Phase 2A - Ground Truth Redesign
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import ground truth
# Import RAG system components
from mistralai import Mistral

from raglite.retrieval.multi_index_search import multi_index_search
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from scripts.ground_truth_v2_master import GROUND_TRUTH_V2, validate_query_answer

logger = get_logger(__name__)


async def run_validation(queries_limit: int = None, verbose: bool = False) -> dict:
    """Run validation on ground truth queries using actual RAG system.

    Args:
        queries_limit: Maximum number of queries to run (None = all)
        verbose: Show detailed results for each query

    Returns:
        dict: Validation results with accuracy metrics
    """
    print("=" * 80)
    print("STORY 2.13 AC4 VALIDATION V2 - ANSWER QUALITY TESTING")
    print("=" * 80)
    print()
    print("Ground Truth Version:", GROUND_TRUTH_V2["metadata"]["version"])
    print("Total Queries Available:", GROUND_TRUTH_V2["metadata"]["total_queries"])
    print("Validation Type:", GROUND_TRUTH_V2["metadata"]["validation_type"])
    print()

    # Select queries to run
    queries = GROUND_TRUTH_V2["queries"]
    if queries_limit:
        queries = queries[:queries_limit]
        print(f"Running first {queries_limit} queries")
    else:
        print(f"Running all {len(queries)} queries")
    print()

    # Initialize results
    results = {
        "total_queries": len(queries),
        "correct": 0,
        "incorrect": 0,
        "by_category": {},
        "by_difficulty": {},
        "by_section": {},
        "errors": [],
        "query_results": [],
    }

    # Run each query
    for idx, query in enumerate(queries, 1):
        query_id = query["id"]
        query_text = query["query"]
        category = query["category"]
        difficulty = query["difficulty"]
        section = query["source_section"]

        print(f"[{idx}/{len(queries)}] {query_id}: {query_text[:80]}...")

        # Get answer from actual RAG system
        system_answer = await get_rag_answer(query)

        if verbose:
            print(f"  RAG Answer: {system_answer[:200]}...")

        # Validate answer
        validation_result = validate_query_answer(query, system_answer)

        # Update results
        is_correct = validation_result["correct"]
        results["query_results"].append(
            {
                "query_id": query_id,
                "query_text": query_text,
                "expected": query["expected_answer"],
                "system_answer": system_answer,
                "validation": validation_result,
                "correct": is_correct,
            }
        )

        if is_correct:
            results["correct"] += 1
            print(f"  ✅ PASS (score: {validation_result['score']:.2f})")
        else:
            results["incorrect"] += 1
            print(f"  ❌ FAIL (score: {validation_result['score']:.2f})")
            if verbose:
                print(f"  Errors: {', '.join(validation_result['errors'])}")

        # Update category stats
        if category not in results["by_category"]:
            results["by_category"][category] = {"total": 0, "correct": 0}
        results["by_category"][category]["total"] += 1
        if is_correct:
            results["by_category"][category]["correct"] += 1

        # Update difficulty stats
        if difficulty not in results["by_difficulty"]:
            results["by_difficulty"][difficulty] = {"total": 0, "correct": 0}
        results["by_difficulty"][difficulty]["total"] += 1
        if is_correct:
            results["by_difficulty"][difficulty]["correct"] += 1

        # Update section stats
        if section not in results["by_section"]:
            results["by_section"][section] = {"total": 0, "correct": 0}
        results["by_section"][section]["total"] += 1
        if is_correct:
            results["by_section"][section]["correct"] += 1

        print()

    # Calculate overall accuracy
    results["accuracy"] = (results["correct"] / results["total_queries"]) * 100

    return results


async def get_rag_answer(query: dict) -> str:
    """Get RAG system answer with retrieval + synthesis.

    Performs full RAG pipeline:
    1. Retrieve relevant chunks using multi-index search
    2. Synthesize answer using Claude API
    3. Return synthesized answer text

    Args:
        query: Query dict from ground truth

    Returns:
        str: Synthesized answer from RAG system

    Raises:
        Exception: If retrieval or synthesis fails
    """
    query_text = query["query"]

    logger.info("RAG query started", extra={"query": query_text, "query_id": query["id"]})

    try:
        # Step 1: Retrieve relevant chunks using multi-index search
        search_results = await multi_index_search(query_text, top_k=5)

        if not search_results:
            logger.warning("No search results", extra={"query": query_text})
            return "No relevant information found in the database."

        logger.info(
            "Search completed",
            extra={
                "query": query_text,
                "results_count": len(search_results),
                "top_score": search_results[0].score if search_results else 0,
            },
        )

        # Step 2: Build context from retrieved chunks
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(f"[Chunk {i}] {result.text}")

        context = "\n\n".join(context_parts)

        # Step 3: Synthesize answer using Mistral
        # Validate Mistral API key
        if not settings.mistral_api_key:
            error_msg = "Mistral API key not configured. Set MISTRAL_API_KEY environment variable."
            logger.error(error_msg)
            return f"ERROR: {error_msg}"

        mistral_client = Mistral(api_key=settings.mistral_api_key)

        from mistralai.models import SystemMessage, UserMessage

        messages = [
            SystemMessage(
                content=(
                    "You are a precise financial data analyst. Answer questions based ONLY on the provided context. "
                    "Extract exact numeric values, units, entities, and periods. Be precise with numbers, including signs (positive/negative). "
                    "If the information is not in the context, say so directly."
                )
            ),
            UserMessage(
                content=(
                    f"Context from financial documents:\n\n{context}\n\n"
                    f"Question: {query_text}\n\n"
                    f"Provide a direct, factual answer. Include:\n"
                    f"- Exact numeric values with correct signs\n"
                    f"- Units of measurement (EUR, EUR/ton, %, etc.)\n"
                    f"- Entity names (Portugal Cement, Tunisia, etc.)\n"
                    f"- Time periods (August 2025, YTD, etc.)\n\n"
                    f"Answer:"
                )
            ),
        ]

        response = mistral_client.chat.complete(
            model=settings.metadata_extraction_model,  # mistral-small-latest
            messages=messages,
            max_tokens=500,
            temperature=0.0,  # Deterministic for factual extraction
        )

        answer = response.choices[0].message.content.strip()

        logger.info(
            "Answer synthesized",
            extra={
                "query": query_text,
                "answer_length": len(answer),
                "chunks_used": len(search_results),
            },
        )

        return answer

    except Exception as e:
        logger.error(
            "RAG query failed",
            extra={"query": query_text, "error": str(e)},
            exc_info=True,
        )
        return f"ERROR: RAG system failed - {str(e)}"


def print_summary(results: dict):
    """Print validation summary report.

    Args:
        results: Validation results dict
    """
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()

    # Overall accuracy
    print(f"Overall Accuracy: {results['accuracy']:.1f}%")
    print(f"Correct: {results['correct']}/{results['total_queries']}")
    print(f"Incorrect: {results['incorrect']}/{results['total_queries']}")
    print()

    # By category
    print("Accuracy by Category:")
    for category, stats in sorted(results["by_category"].items()):
        accuracy = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  {category:20s}: {accuracy:5.1f}% ({stats['correct']}/{stats['total']})")
    print()

    # By difficulty
    print("Accuracy by Difficulty:")
    for difficulty, stats in sorted(results["by_difficulty"].items()):
        accuracy = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  {difficulty:10s}: {accuracy:5.1f}% ({stats['correct']}/{stats['total']})")
    print()

    # By section
    print("Accuracy by Section:")
    for section, stats in sorted(results["by_section"].items()):
        accuracy = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  Section {section}: {accuracy:5.1f}% ({stats['correct']}/{stats['total']})")
    print()

    # Common error patterns
    print("Common Error Patterns:")
    error_counts = {}
    for query_result in results["query_results"]:
        if not query_result["correct"]:
            for error in query_result["validation"]["errors"]:
                error_type = error.split(":")[0] if ":" in error else error
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

    for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {error_type}: {count} occurrences")
    print()

    # Assessment
    print("Assessment:")
    if results["accuracy"] >= 80:
        print("  ✅ EXCELLENT - System is production ready")
    elif results["accuracy"] >= 70:
        print("  ✅ GOOD - Meets AC4 threshold (≥70%)")
    elif results["accuracy"] >= 60:
        print("  ⚠️  ACCEPTABLE - Close to threshold, needs minor improvements")
    elif results["accuracy"] >= 40:
        print("  ⚠️  FAIR - Needs significant improvements")
    else:
        print("  ❌ POOR - Major issues detected, requires investigation")
    print()

    # Recommendations
    print("Recommendations:")
    if results["accuracy"] < 70:
        print("  1. Review common error patterns above")
        print("  2. Check SQL generation for query types with low accuracy")
        print("  3. Verify transposed table detection is working (Phase 2.7)")
        print("  4. Validate value extraction and unit handling")
        print("  5. Check entity disambiguation logic")
    else:
        print("  ✅ System is meeting AC4 requirements")
        print("  Consider expanding to 50 queries for comprehensive validation")
    print()


def save_results(results: dict, output_file: str = "validation-results-v2.json"):
    """Save validation results to JSON file.

    Args:
        results: Validation results dict
        output_file: Output filename
    """
    import json
    from datetime import datetime

    output_path = Path("docs") / "validation" / output_file

    # Add metadata
    results["metadata"] = {
        "timestamp": datetime.now().isoformat(),
        "ground_truth_version": GROUND_TRUTH_V2["metadata"]["version"],
        "validation_type": "answer_quality",
    }

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {output_path}")
    print()


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Story 2.13 AC4 Validation V2 - Answer Quality Testing"
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=None,
        help="Run only first N queries (default: all)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed validation results for each query",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to JSON file",
    )

    args = parser.parse_args()

    # Run validation with actual RAG system
    results = await run_validation(queries_limit=args.queries, verbose=args.verbose)

    # Print summary
    print_summary(results)

    # Save results if requested
    if args.save:
        save_results(results)

    # Exit code based on AC4 threshold
    if results["accuracy"] >= 70:
        print("✅ AC4 PASSED (≥70% accuracy)")
        sys.exit(0)
    else:
        print(f"❌ AC4 FAILED ({results['accuracy']:.1f}% < 70%)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
