#!/usr/bin/env python3
"""Epic 2 Progress Tracker - Incremental accuracy tracking across stories.

Tracks accuracy improvements from Epic 1 baseline (56% retrieval, 32% attribution)
through Epic 2 stories (2.1, 2.2, 2.3, etc.) toward target (90% retrieval, 95% attribution).

Usage:
    # Run after completing a story and log progress
    uv run python scripts/track-epic-2-progress.py --story 2.1 --save

    # View progress trend without running new tests
    uv run python scripts/track-epic-2-progress.py --show-only

    # Compare two checkpoints
    uv run python scripts/track-epic-2-progress.py --compare baseline story-2.1

Exit codes:
    0 - Progress tracked successfully
    1 - Error encountered
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from accuracy_utils import calculate_performance_metrics  # noqa: E402

from raglite.retrieval.attribution import generate_citations  # noqa: E402
from raglite.retrieval.search import search_documents  # noqa: E402
from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402

# Epic 1 baseline (from baseline-accuracy-report-FINAL.txt)
BASELINE_RETRIEVAL = 56.0
BASELINE_ATTRIBUTION = 32.0
BASELINE_P50_LATENCY = 33.20
BASELINE_P95_LATENCY = 63.34

# Epic 2 targets (from NFR6/NFR7)
TARGET_RETRIEVAL = 90.0
TARGET_ATTRIBUTION = 95.0

# Progress log file
PROGRESS_LOG_FILE = project_root / "docs" / "epic-2-progress.log"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Track Epic 2 accuracy progress across stories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--story",
        type=str,
        metavar="ID",
        help="Story ID (e.g., '2.1', '2.2') to log with this run",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to progress log file",
    )
    parser.add_argument(
        "--show-only",
        action="store_true",
        help="Show existing progress trend without running tests",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("CHECKPOINT1", "CHECKPOINT2"),
        help="Compare two checkpoints (e.g., 'baseline' 'story-2.1')",
    )
    return parser.parse_args()


async def run_accuracy_test() -> dict[str, Any]:
    """Run accuracy tests on all ground truth queries.

    Returns:
        Dict with performance metrics
    """
    results = []

    for qa in GROUND_TRUTH_QA:
        try:
            # Call search_documents
            query_results = await search_documents(query=qa["question"], top_k=5)

            # Generate citations
            query_results = await generate_citations(query_results)

            # Check retrieval accuracy
            all_text = " ".join([r.text.lower() for r in query_results])
            matched_kw = [kw for kw in qa["expected_keywords"] if kw.lower() in all_text]
            retrieval_pass = len(matched_kw) >= len(qa["expected_keywords"]) * 0.5

            # Check attribution accuracy
            attribution_pass = any(
                abs(r.page_number - qa["expected_page_number"]) <= 1
                for r in query_results
                if r.page_number is not None
            )

            results.append(
                {
                    "query_id": qa["id"],
                    "latency_ms": 0.0,  # Not measured in this script
                    "retrieval": {"pass_": retrieval_pass},
                    "attribution": {"pass_": attribution_pass},
                }
            )

        except Exception:
            results.append(
                {
                    "query_id": qa["id"],
                    "latency_ms": 0.0,
                    "retrieval": {"pass_": False},
                    "attribution": {"pass_": False},
                    "error": True,
                }
            )

    return calculate_performance_metrics(results)


def load_progress_log() -> list[dict[str, Any]]:
    """Load progress log from file.

    Returns:
        List of checkpoint dicts
    """
    if not PROGRESS_LOG_FILE.exists():
        return []

    with open(PROGRESS_LOG_FILE) as f:
        return [json.loads(line) for line in f if line.strip()]


def save_checkpoint(story_id: str, metrics: dict[str, Any]) -> None:
    """Save checkpoint to progress log.

    Args:
        story_id: Story identifier (e.g., 'baseline', 'story-2.1')
        metrics: Performance metrics dict
    """
    PROGRESS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "timestamp": datetime.now().isoformat(),
        "story_id": story_id,
        "retrieval_accuracy": metrics["retrieval_accuracy"],
        "attribution_accuracy": metrics["attribution_accuracy"],
        "p50_latency_ms": metrics.get("p50_latency_ms", 0.0),
        "p95_latency_ms": metrics.get("p95_latency_ms", 0.0),
    }

    with open(PROGRESS_LOG_FILE, "a") as f:
        f.write(json.dumps(checkpoint) + "\n")


def print_progress_summary(checkpoints: list[dict[str, Any]]) -> None:
    """Print progress summary with trend visualization.

    Args:
        checkpoints: List of checkpoint dicts
    """
    if not checkpoints:
        print("No progress checkpoints found.")
        return

    print("=" * 70)
    print("Epic 2 Progress Tracker")
    print("=" * 70)
    print(
        f"Baseline (Epic 1): {BASELINE_RETRIEVAL:.1f}% retrieval, {BASELINE_ATTRIBUTION:.1f}% attribution"
    )
    print(
        f"Target (NFR6/7):   {TARGET_RETRIEVAL:.1f}% retrieval, {TARGET_ATTRIBUTION:.1f}% attribution"
    )
    print()

    # Print each checkpoint
    for cp in checkpoints:
        delta_retrieval = cp["retrieval_accuracy"] - BASELINE_RETRIEVAL
        delta_attribution = cp["attribution_accuracy"] - BASELINE_ATTRIBUTION

        print(
            f"{cp['story_id']:15} {cp['retrieval_accuracy']:5.1f}% retrieval ({delta_retrieval:+5.1f}%), "
            f"{cp['attribution_accuracy']:5.1f}% attribution ({delta_attribution:+5.1f}%)"
        )

    print()
    print("-" * 70)

    # Calculate progress toward target
    latest = checkpoints[-1]
    retrieval_progress = (
        (latest["retrieval_accuracy"] - BASELINE_RETRIEVAL)
        / (TARGET_RETRIEVAL - BASELINE_RETRIEVAL)
        * 100
    )
    attribution_progress = (
        (latest["attribution_accuracy"] - BASELINE_ATTRIBUTION)
        / (TARGET_ATTRIBUTION - BASELINE_ATTRIBUTION)
        * 100
    )

    print(
        f"Progress toward retrieval goal:    {retrieval_progress:.0f}% ({latest['retrieval_accuracy']:.1f}% / {TARGET_RETRIEVAL:.1f}%)"
    )
    print(
        f"Progress toward attribution goal:  {attribution_progress:.0f}% ({latest['attribution_accuracy']:.1f}% / {TARGET_ATTRIBUTION:.1f}%)"
    )
    print("=" * 70)


def compare_checkpoints(cp1: dict[str, Any], cp2: dict[str, Any]) -> None:
    """Compare two checkpoints and show deltas.

    Args:
        cp1: First checkpoint
        cp2: Second checkpoint
    """
    print("=" * 70)
    print(f"Comparing: {cp1['story_id']} → {cp2['story_id']}")
    print("=" * 70)

    delta_retrieval = cp2["retrieval_accuracy"] - cp1["retrieval_accuracy"]
    delta_attribution = cp2["attribution_accuracy"] - cp1["attribution_accuracy"]

    print(
        f"Retrieval accuracy:    {cp1['retrieval_accuracy']:.1f}% → {cp2['retrieval_accuracy']:.1f}% ({delta_retrieval:+.1f}%)"
    )
    print(
        f"Attribution accuracy:  {cp1['attribution_accuracy']:.1f}% → {cp2['attribution_accuracy']:.1f}% ({delta_attribution:+.1f}%)"
    )

    if "p50_latency_ms" in cp1 and "p50_latency_ms" in cp2:
        delta_p50 = cp2["p50_latency_ms"] - cp1["p50_latency_ms"]
        print(
            f"p50 latency:           {cp1['p50_latency_ms']:.2f}ms → {cp2['p50_latency_ms']:.2f}ms ({delta_p50:+.2f}ms)"
        )

    print("=" * 70)


async def main() -> int:
    """Main function."""
    args = parse_args()

    # Load existing checkpoints
    checkpoints = load_progress_log()

    # Add baseline if not present
    if not checkpoints or checkpoints[0]["story_id"] != "baseline":
        baseline_checkpoint = {
            "timestamp": "2025-10-16T00:00:00",
            "story_id": "baseline",
            "retrieval_accuracy": BASELINE_RETRIEVAL,
            "attribution_accuracy": BASELINE_ATTRIBUTION,
            "p50_latency_ms": BASELINE_P50_LATENCY,
            "p95_latency_ms": BASELINE_P95_LATENCY,
        }
        checkpoints.insert(0, baseline_checkpoint)

    # Handle --show-only
    if args.show_only:
        print_progress_summary(checkpoints)
        return 0

    # Handle --compare
    if args.compare:
        cp1_id, cp2_id = args.compare
        cp1 = next((cp for cp in checkpoints if cp["story_id"] == cp1_id), None)
        cp2 = next((cp for cp in checkpoints if cp["story_id"] == cp2_id), None)

        if not cp1:
            print(f"Error: Checkpoint '{cp1_id}' not found")
            return 1
        if not cp2:
            print(f"Error: Checkpoint '{cp2_id}' not found")
            return 1

        compare_checkpoints(cp1, cp2)
        return 0

    # Run accuracy test
    print("Running accuracy tests on ground truth suite (50 queries)...")
    metrics = await run_accuracy_test()

    print(
        f"\nResults: {metrics['retrieval_accuracy']:.1f}% retrieval, {metrics['attribution_accuracy']:.1f}% attribution"
    )

    # Save if requested
    if args.save:
        if not args.story:
            print("Error: --save requires --story ID")
            return 1

        story_id = f"story-{args.story}" if not args.story.startswith("story-") else args.story
        save_checkpoint(story_id, metrics)
        print(f"Checkpoint saved: {story_id}")

        # Reload and print summary
        checkpoints = load_progress_log()
        if not checkpoints or checkpoints[0]["story_id"] != "baseline":
            checkpoints.insert(
                0,
                {
                    "timestamp": "2025-10-16T00:00:00",
                    "story_id": "baseline",
                    "retrieval_accuracy": BASELINE_RETRIEVAL,
                    "attribution_accuracy": BASELINE_ATTRIBUTION,
                    "p50_latency_ms": BASELINE_P50_LATENCY,
                    "p95_latency_ms": BASELINE_P95_LATENCY,
                },
            )
        print()
        print_progress_summary(checkpoints)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
