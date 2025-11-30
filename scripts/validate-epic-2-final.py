#!/usr/bin/env python3
"""Epic 2 Final Validation Script (Story 2.15).

Validates NFR6 (≥70% retrieval accuracy) and NFR7 (≥95% attribution accuracy)
using the normalized ground truth dataset (49 queries).

This script is designed for CI/CD use and outputs structured results.

Usage:
    python scripts/validate-epic-2-final.py
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.retrieval.attribution import generate_citations  # noqa: E402
from raglite.retrieval.multi_index_search import multi_index_search  # noqa: E402
from raglite.shared.models import QueryResult  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Ground truth file
GROUND_TRUTH_FILE = Path("tests/ground_truth_normalized.json")

# NFR Targets
NFR6_TARGET = 70.0  # ≥70% retrieval accuracy (Epic 2 Decision Gate)
NFR7_TARGET = 95.0  # ≥95% attribution accuracy

# Output file
OUTPUT_DIR = Path("docs/validation")
OUTPUT_FILE = OUTPUT_DIR / "epic-2-final-validation.json"


def load_ground_truth() -> list[dict]:
    """Load normalized ground truth questions."""
    if not GROUND_TRUTH_FILE.exists():
        logger.error(f"Ground truth file not found: {GROUND_TRUTH_FILE}")
        sys.exit(1)

    with open(GROUND_TRUTH_FILE) as f:
        data = json.load(f)

    questions = data.get("questions", [])
    logger.info(f"Loaded {len(questions)} ground truth questions")
    return questions


def check_retrieval_accuracy(question: dict, results: list[QueryResult]) -> dict:
    """Check if query results contain expected keywords.

    Args:
        question: Ground truth question with expected_keywords
        results: Search results from multi_index_search

    Returns:
        Dict with pass status and reason
    """
    if not results:
        return {"pass_": False, "reason": "No results returned"}

    expected_keywords = question.get("expected_keywords", [])
    if not expected_keywords:
        return {"pass_": True, "reason": "No keywords to check"}

    # Combine all result texts
    combined_text = " ".join(r.text.lower() for r in results)

    # Check for any matching keyword
    matches = []
    for kw in expected_keywords:
        if kw.lower() in combined_text:
            matches.append(kw)

    if matches:
        return {
            "pass_": True,
            "reason": f"Found keywords: {', '.join(matches[:3])}",
            "matched_keywords": matches,
        }
    else:
        return {
            "pass_": False,
            "reason": f"Missing keywords: {', '.join(expected_keywords[:3])}",
            "expected_keywords": expected_keywords,
        }


def check_attribution_accuracy(question: dict, results: list[QueryResult]) -> dict:
    """Check if citations point to valid source pages.

    Args:
        question: Ground truth question
        results: Search results with citations

    Returns:
        Dict with pass status and reason
    """
    if not results:
        return {"pass_": False, "reason": "No results to attribute"}

    # Check that results have valid page numbers
    valid_pages = [r for r in results if r.page_number and r.page_number > 0]

    if not valid_pages:
        return {"pass_": False, "reason": "No valid page numbers in results"}

    # Check that source documents are cited
    sources = [r for r in results if r.source_document]

    if sources:
        return {
            "pass_": True,
            "reason": f"Attributed to {len(valid_pages)} pages from {len({r.source_document for r in sources})} source(s)",
        }
    else:
        return {"pass_": False, "reason": "No source documents cited"}


async def run_single_query(question: dict, verbose: bool = False) -> dict:
    """Run a single ground truth query.

    Args:
        question: Ground truth question dict
        verbose: Print detailed output

    Returns:
        Dict with query results and metrics
    """
    query_id = question["id"]
    query_text = question["question"]

    start_time = time.perf_counter()

    try:
        # Execute multi-index search
        search_results = await multi_index_search(query=query_text, top_k=5)

        # Convert to QueryResult for compatibility
        query_results = [
            QueryResult(
                score=r.score,
                text=r.text,
                source_document=r.document_id,
                page_number=r.page_number if r.page_number is not None else 0,
                chunk_index=r.metadata.get("chunk_index", 0),
                word_count=r.metadata.get("word_count", len(r.text.split())),
            )
            for r in search_results
        ]

        # Generate citations
        query_results = await generate_citations(query_results)

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Check accuracy
        retrieval = check_retrieval_accuracy(question, query_results)
        attribution = check_attribution_accuracy(question, query_results)

        if verbose:
            status = "✓" if retrieval["pass_"] else "✗"
            logger.info(f"[{query_id}] {status} {query_text[:60]}...")

        return {
            "query_id": query_id,
            "question": query_text,
            "category": question.get("category", "unknown"),
            "difficulty": question.get("difficulty", "unknown"),
            "latency_ms": latency_ms,
            "retrieval": retrieval,
            "attribution": attribution,
            "num_results": len(query_results),
            "top_score": query_results[0].score if query_results else 0.0,
            "error": None,
        }

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        error_msg = f"{type(e).__name__}: {str(e)}"

        if verbose:
            logger.error(f"[{query_id}] ✗ ERROR: {error_msg}")

        return {
            "query_id": query_id,
            "question": query_text,
            "category": question.get("category", "unknown"),
            "difficulty": question.get("difficulty", "unknown"),
            "latency_ms": latency_ms,
            "retrieval": {"pass_": False, "reason": error_msg},
            "attribution": {"pass_": False, "reason": error_msg},
            "num_results": 0,
            "top_score": 0.0,
            "error": error_msg,
        }


async def run_validation() -> dict:
    """Run full Epic 2 validation suite.

    Returns:
        Dict with validation results and metrics
    """
    questions = load_ground_truth()

    logger.info("")
    logger.info("=" * 60)
    logger.info("EPIC 2 FINAL VALIDATION (Story 2.15)")
    logger.info("=" * 60)
    logger.info(f"Ground Truth: {GROUND_TRUTH_FILE}")
    logger.info(f"Total Queries: {len(questions)}")
    logger.info(f"NFR6 Target: ≥{NFR6_TARGET}% retrieval accuracy")
    logger.info(f"NFR7 Target: ≥{NFR7_TARGET}% attribution accuracy")
    logger.info("")
    logger.info("Running queries...")

    # Run all queries
    results = []
    for question in questions:
        result = await run_single_query(question, verbose=True)
        results.append(result)

    # Calculate metrics
    total = len(results)
    retrieval_pass = sum(1 for r in results if r["retrieval"]["pass_"])
    attribution_pass = sum(1 for r in results if r["attribution"]["pass_"])
    errors = sum(1 for r in results if r["error"])

    retrieval_accuracy = (retrieval_pass / total) * 100 if total > 0 else 0
    attribution_accuracy = (attribution_pass / total) * 100 if total > 0 else 0

    # Calculate latency percentiles
    latencies = [r["latency_ms"] for r in results if r["error"] is None]
    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0

    # Determine pass/fail
    nfr6_pass = retrieval_accuracy >= NFR6_TARGET
    nfr7_pass = attribution_accuracy >= NFR7_TARGET

    metrics = {
        "total_queries": total,
        "retrieval_pass": retrieval_pass,
        "retrieval_accuracy": round(retrieval_accuracy, 1),
        "attribution_pass": attribution_pass,
        "attribution_accuracy": round(attribution_accuracy, 1),
        "errors": errors,
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "nfr6_pass": nfr6_pass,
        "nfr7_pass": nfr7_pass,
        "overall_pass": nfr6_pass and nfr7_pass and errors == 0,
        "overall_accuracy": round(retrieval_accuracy, 1),
    }

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("VALIDATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total Queries:         {total}")
    logger.info(f"Retrieval Accuracy:    {retrieval_accuracy:.1f}% ({retrieval_pass}/{total})")
    logger.info(f"Attribution Accuracy:  {attribution_accuracy:.1f}% ({attribution_pass}/{total})")
    logger.info(f"p50 Latency:           {p50:.0f}ms")
    logger.info(f"p95 Latency:           {p95:.0f}ms")
    logger.info(f"Errors:                {errors}")
    logger.info("")
    logger.info("-" * 60)
    logger.info("NFR VALIDATION")
    logger.info("-" * 60)
    logger.info(f"NFR6 (≥{NFR6_TARGET}% retrieval):    {'✓ PASS' if nfr6_pass else '✗ FAIL'}")
    logger.info(f"NFR7 (≥{NFR7_TARGET}% attribution):  {'✓ PASS' if nfr7_pass else '✗ FAIL'}")
    logger.info("")

    if metrics["overall_pass"]:
        logger.info("✅ EPIC 2 DECISION GATE: PASSED")
    else:
        logger.info("❌ EPIC 2 DECISION GATE: FAILED")

    return {
        "metrics": metrics,
        "results": results,
        "timestamp": datetime.now().isoformat(),
        "ground_truth_file": str(GROUND_TRUTH_FILE),
    }


def save_results(validation_results: dict) -> None:
    """Save validation results to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(validation_results, f, indent=2)

    logger.info(f"Results saved to: {OUTPUT_FILE}")


def main() -> int:
    """Main entry point."""
    try:
        validation_results = asyncio.run(run_validation())
        save_results(validation_results)

        # Return appropriate exit code
        if validation_results["metrics"]["overall_pass"]:
            return 0
        else:
            return 1

    except KeyboardInterrupt:
        logger.warning("Validation interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
