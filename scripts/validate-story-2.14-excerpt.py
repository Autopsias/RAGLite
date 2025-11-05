#!/usr/bin/env python3
"""Story 2.14 Excerpt Ground Truth Validation - Pages 18-50 Only.

Validates SQL retrieval against queries specific to the 33-page excerpt PDF.
This is SEPARATE from 160-page PDF validation.

Target: 95%+ accuracy on 12 excerpt-specific queries
Expected: High accuracy since queries match excerpt content exactly
"""

import asyncio
import json
import sys
from dataclasses import dataclass

from raglite.retrieval.query_classifier import generate_sql_query
from raglite.retrieval.sql_table_search import search_tables_sql
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExcerptTestResult:
    """Result of excerpt ground truth query."""

    query_id: str
    category: str
    natural_query: str
    expected_min: int
    expected_max: int
    actual_results: int
    passed: bool
    error: str | None
    confidence: float


async def validate_excerpt_query(test_def: dict) -> ExcerptTestResult:
    """Validate a single excerpt ground truth query."""
    query_id = test_def["id"]
    category = test_def["category"]
    query = test_def["query"]
    expected_min = test_def["expected_result_min"]
    expected_max = test_def["expected_result_max"]

    logger.debug(f"Testing {query_id} ({category}): {query[:60]}...")

    try:
        # Generate SQL
        sql = await generate_sql_query(query)
        if not sql:
            return ExcerptTestResult(
                query_id=query_id,
                category=category,
                natural_query=query,
                expected_min=expected_min,
                expected_max=expected_max,
                actual_results=0,
                passed=False,
                error="SQL generation failed",
                confidence=0.0,
            )

        # Execute SQL
        results = await search_tables_sql(sql)
        actual_results = len(results)

        # Validation: Check if within expected range
        passed = expected_min <= actual_results <= expected_max

        # Calculate confidence
        if actual_results == 0:
            confidence = 0.0
        elif passed:
            # Calculate how close to middle of range
            range_mid = (expected_min + expected_max) / 2
            deviation = abs(actual_results - range_mid) / range_mid
            confidence = max(0.8, 1.0 - (deviation * 0.2))
        else:
            confidence = 0.2

        return ExcerptTestResult(
            query_id=query_id,
            category=category,
            natural_query=query,
            expected_min=expected_min,
            expected_max=expected_max,
            actual_results=actual_results,
            passed=passed,
            error=None,
            confidence=min(confidence, 1.0),
        )

    except Exception as e:
        return ExcerptTestResult(
            query_id=query_id,
            category=category,
            natural_query=query,
            expected_min=expected_min,
            expected_max=expected_max,
            actual_results=0,
            passed=False,
            error=str(e),
            confidence=0.0,
        )


async def main() -> int:
    """Run excerpt ground truth validation."""
    # Load excerpt ground truth
    with open(
        "/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/validation/story-2.14-excerpt-ground-truth.json"
    ) as f:
        ground_truth = json.load(f)

    logger.info("=" * 80)
    logger.info("🎯 STORY 2.14 EXCERPT GROUND TRUTH VALIDATION")
    logger.info("=" * 80)
    logger.info(f"PDF Source: {ground_truth['metadata']['pdf_source']}")
    logger.info(f"Pages: {ground_truth['metadata']['pdf_pages']}")
    logger.info(f"Total Queries: {len(ground_truth['test_queries'])}")
    logger.info(
        f"Target Accuracy: {ground_truth['validation_parameters']['target_overall_accuracy']}"
    )
    logger.info("=" * 80)

    # Run validations
    results = []
    for test_def in ground_truth["test_queries"]:
        result = await validate_excerpt_query(test_def)
        results.append(result)

        # Log result
        status = "✅" if result.passed else "❌"
        logger.info(
            f"{status} {result.query_id}: {result.actual_results} results "
            f"(expected {result.expected_min}-{result.expected_max}) "
            f"[confidence: {result.confidence:.2f}]"
        )

    # Summary by category
    logger.info("\n" + "=" * 80)
    logger.info("RESULTS BY CATEGORY")
    logger.info("=" * 80)

    categories = {}
    for result in results:
        cat = result.category
        if cat not in categories:
            categories[cat] = {"passed": 0, "total": 0}
        categories[cat]["total"] += 1
        if result.passed:
            categories[cat]["passed"] += 1

    for cat in sorted(categories.keys()):
        stats = categories[cat]
        pct = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "✅" if pct >= 90 else "⚠️" if pct >= 80 else "❌"
        logger.info(f"{status} {cat}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")

    # Overall accuracy
    total_passed = sum(1 for r in results if r.passed)
    total = len(results)
    overall_pct = (total_passed / total * 100) if total > 0 else 0
    avg_confidence = sum(r.confidence for r in results) / total if results else 0

    logger.info("\n" + "=" * 80)
    logger.info(f"OVERALL ACCURACY: {total_passed}/{total} ({overall_pct:.1f}%)")
    logger.info(f"Average Confidence: {avg_confidence:.3f}")
    logger.info("=" * 80)

    # Decision gate
    logger.info("\n" + "=" * 80)
    logger.info("DECISION GATE - EXCERPT GROUND TRUTH")
    logger.info("=" * 80)

    if overall_pct >= 92:
        logger.info(f"✅ PASS: {overall_pct:.1f}% >= 92% target")
        logger.info("🎉 Story 2.14 excerpt validation SUCCESSFUL")
        logger.info("✅ Excerpt-specific queries working perfectly")
        logger.info("✅ Ready for full PDF validation if needed")
        return 0

    elif overall_pct >= 83:
        logger.info(f"⚠️  INVESTIGATE: {overall_pct:.1f}% (83-92% range)")
        logger.info(f"Minor issues ({total - total_passed} failures) - investigate and retry")
        return 1

    else:
        logger.info(f"❌ FAIL: {overall_pct:.1f}% (<83%)")
        logger.info("Review failures and check excerpt content")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
