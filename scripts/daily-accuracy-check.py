#!/usr/bin/env python3
"""Daily accuracy spot check for RAGLite Phase 1 tracking.

Runs a subset of 10-15 representative queries for quick daily validation.
Tracks accuracy trends over time and provides early warning for regressions.

Usage:
    # Run daily check with default 15 queries
    uv run python scripts/daily-accuracy-check.py

    # Run with custom subset size
    uv run python scripts/daily-accuracy-check.py --subset 10

    # Show trend analysis
    uv run python scripts/daily-accuracy-check.py --show-trend

Exit codes:
    0 - Daily check complete (results logged)
    1 - Critical regression detected (accuracy <70%)
"""

import argparse
import asyncio
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from accuracy_utils import (  # noqa: E402
    EARLY_WARNING_THRESHOLD,
    KEYWORD_MATCH_THRESHOLD,
    PAGE_TOLERANCE,
)

from raglite.retrieval.attribution import generate_citations  # noqa: E402
from raglite.retrieval.search import search_documents  # noqa: E402
from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402

# Tracking log location
TRACKING_LOG = project_root / "docs" / "accuracy-tracking-log.jsonl"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run daily RAGLite accuracy spot check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--subset",
        type=int,
        default=15,
        metavar="N",
        help="Number of queries to run (default: 15)",
    )
    parser.add_argument(
        "--show-trend",
        action="store_true",
        help="Show historical trend analysis",
    )
    return parser.parse_args()


async def run_single_query(qa: dict) -> dict:
    """Run a single query and return metrics.

    Args:
        qa: Ground truth question dict

    Returns:
        Dict with pass/fail status and latency
    """
    start_time = time.perf_counter()
    try:
        # Execute query
        results = await search_documents(query=qa["question"], top_k=5)
        results = await generate_citations(results)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Check retrieval accuracy (uses KEYWORD_MATCH_THRESHOLD constant)
        all_text = " ".join([r.text.lower() for r in results])
        matched_keywords = [kw for kw in qa["expected_keywords"] if kw.lower() in all_text]
        retrieval_pass = (
            len(matched_keywords) >= len(qa["expected_keywords"]) * KEYWORD_MATCH_THRESHOLD
        )

        # Check attribution accuracy (uses PAGE_TOLERANCE constant)
        expected_page = qa["expected_page_number"]
        attribution_pass = any(
            r.page_number is not None and abs(r.page_number - expected_page) <= PAGE_TOLERANCE
            for r in results
        )

        return {
            "query_id": qa["id"],
            "retrieval_pass": retrieval_pass,
            "attribution_pass": attribution_pass,
            "latency_ms": latency_ms,
            "error": None,
        }

    except Exception as e:
        return {
            "query_id": qa["id"],
            "retrieval_pass": False,
            "attribution_pass": False,
            "latency_ms": 0,
            "error": str(e),
        }


async def run_daily_check(subset_size: int) -> dict:
    """Run daily accuracy check with subset of queries.

    Args:
        subset_size: Number of queries to run

    Returns:
        Dict with metrics
    """
    # Select diverse subset (mix of difficulties and categories)
    easy = [q for q in GROUND_TRUTH_QA if q["difficulty"] == "easy"]
    medium = [q for q in GROUND_TRUTH_QA if q["difficulty"] == "medium"]
    hard = [q for q in GROUND_TRUTH_QA if q["difficulty"] == "hard"]

    # Proportional sampling (60% easy, 30% medium, 10% hard)
    n_easy = int(subset_size * 0.6)
    n_medium = int(subset_size * 0.3)
    n_hard = subset_size - n_easy - n_medium

    subset = (
        random.sample(easy, min(n_easy, len(easy)))
        + random.sample(medium, min(n_medium, len(medium)))
        + random.sample(hard, min(n_hard, len(hard)))
    )

    print(f"Running daily check with {len(subset)} queries...")
    print(f"Subset: {n_easy} easy, {n_medium} medium, {n_hard} hard\n")

    # Run queries
    results = []
    for qa in subset:
        result = await run_single_query(qa)
        results.append(result)

    # Calculate metrics
    total = len(results)
    retrieval_pass = sum(1 for r in results if r["retrieval_pass"])
    attribution_pass = sum(1 for r in results if r["attribution_pass"])
    errors = sum(1 for r in results if r["error"] is not None)
    latencies = [r["latency_ms"] for r in results if r["error"] is None]

    retrieval_accuracy = (retrieval_pass / total) * 100 if total > 0 else 0
    attribution_accuracy = (attribution_pass / total) * 100 if total > 0 else 0
    p50_latency = sorted(latencies)[int(len(latencies) * 0.5)] if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    return {
        "timestamp": datetime.now().isoformat(),
        "subset_size": total,
        "retrieval_accuracy": retrieval_accuracy,
        "attribution_accuracy": attribution_accuracy,
        "p50_latency_ms": p50_latency,
        "p95_latency_ms": p95_latency,
        "errors": errors,
        "query_ids": [r["query_id"] for r in results],
    }


def append_to_log(metrics: dict) -> None:
    """Append metrics to tracking log (JSONL format).

    Args:
        metrics: Daily check metrics dict
    """
    # Create docs directory if it doesn't exist
    TRACKING_LOG.parent.mkdir(exist_ok=True)

    # Append to JSONL file
    with open(TRACKING_LOG, "a") as f:
        f.write(json.dumps(metrics) + "\n")

    print(f"✓ Results logged to: {TRACKING_LOG}")


def load_historical_data() -> list[dict]:
    """Load historical accuracy data from log file.

    Returns:
        List of metrics dicts sorted by timestamp (oldest first)
    """
    if not TRACKING_LOG.exists():
        return []

    entries = []
    with open(TRACKING_LOG) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    return sorted(entries, key=lambda x: x["timestamp"])


def show_trend_analysis(history: list[dict]) -> None:
    """Display trend analysis from historical data.

    Args:
        history: List of historical metrics dicts
    """
    if len(history) < 2:
        print("\n⚠ Not enough historical data for trend analysis (need ≥2 entries)")
        return

    print("\n" + "=" * 60)
    print("TREND ANALYSIS")
    print("=" * 60)

    # Show last 10 entries
    recent = history[-10:]
    print(f"\nLast {len(recent)} daily checks:\n")
    print(f"{'Date':<12} {'Retrieval':<12} {'Attribution':<12} {'p50 (ms)':<10}")
    print("-" * 60)

    for entry in recent:
        date = entry["timestamp"][:10]
        retrieval = f"{entry['retrieval_accuracy']:.1f}%"
        attribution = f"{entry['attribution_accuracy']:.1f}%"
        p50 = f"{entry['p50_latency_ms']:.1f}"
        print(f"{date:<12} {retrieval:<12} {attribution:<12} {p50:<10}")

    # Calculate improvement rate
    first = history[0]
    last = history[-1]
    retrieval_delta = last["retrieval_accuracy"] - first["retrieval_accuracy"]
    attribution_delta = last["attribution_accuracy"] - first["attribution_accuracy"]
    days_elapsed = len(history)

    print("\n" + "-" * 60)
    print("Improvement Summary:")
    print(
        f"  Retrieval:    {first['retrieval_accuracy']:.1f}% → {last['retrieval_accuracy']:.1f}% ({retrieval_delta:+.1f}% over {days_elapsed} checks)"
    )
    print(
        f"  Attribution:  {first['attribution_accuracy']:.1f}% → {last['attribution_accuracy']:.1f}% ({attribution_delta:+.1f}% over {days_elapsed} checks)"
    )

    # Detect regression (>5% drop from previous)
    if len(history) >= 2:
        prev = history[-2]
        retrieval_regression = last["retrieval_accuracy"] - prev["retrieval_accuracy"]
        if retrieval_regression < -5:
            print(
                f"\n⚠ WARNING: Retrieval accuracy dropped {retrieval_regression:.1f}% since last check!"
            )


def check_early_warning(accuracy: float) -> bool:
    """Check if accuracy triggers early warning.

    Args:
        accuracy: Current retrieval accuracy percentage

    Returns:
        True if early warning triggered, False otherwise
    """
    if accuracy < EARLY_WARNING_THRESHOLD:
        print("\n" + "!" * 60)
        print("⚠ EARLY WARNING: ACCURACY BELOW 70% THRESHOLD")
        print("!" * 60)
        print("\n🛑 HALT FEATURE WORK - Investigate root cause immediately\n")
        print("Investigation Checklist:")
        print("  1. Verify Docling extraction quality (check page numbers)")
        print("  2. Review chunking boundaries (overlap, size)")
        print("  3. Test embedding quality (Fin-E5 model loaded correctly?)")
        print("  4. Check Qdrant search parameters (top_k, similarity threshold)")
        print("  5. Validate ground truth test set quality")
        print("  6. Review recent code changes for regressions\n")
        return True
    return False


async def main() -> int:
    """Main daily check function."""
    args = parse_args()

    print("=" * 60)
    print("RAGLite Daily Accuracy Check")
    print("=" * 60)
    print()

    # Show trend analysis if requested
    if args.show_trend:
        history = load_historical_data()
        show_trend_analysis(history)
        return 0

    # Run daily check
    metrics = await run_daily_check(args.subset)

    # Print summary
    print("\n" + "-" * 60)
    print("DAILY CHECK RESULTS")
    print("-" * 60)
    print(f"Retrieval Accuracy:    {metrics['retrieval_accuracy']:.1f}%")
    print(f"Attribution Accuracy:  {metrics['attribution_accuracy']:.1f}%")
    print(f"p50 Latency:           {metrics['p50_latency_ms']:.2f}ms")
    print(f"p95 Latency:           {metrics['p95_latency_ms']:.2f}ms")
    print(f"Errors:                {metrics['errors']}")
    print()

    # Append to log
    append_to_log(metrics)

    # Check for early warning
    warning_triggered = check_early_warning(metrics["retrieval_accuracy"])

    # Show trend if historical data available
    history = load_historical_data()
    if len(history) >= 2:
        show_trend_analysis(history)

    # Exit code
    return 1 if warning_triggered else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
