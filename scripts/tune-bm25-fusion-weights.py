"""Tune BM25 fusion alpha parameter for optimal accuracy.

Story 2.11 AC2: Test multiple alpha values and select the one with highest
retrieval accuracy on ground truth test set.

Alpha parameter controls the fusion weight:
- alpha=0.7: 70% semantic, 30% BM25 (current default)
- alpha=0.85: 85% semantic, 15% BM25 (reduces BM25 influence)
- alpha=0.9: 90% semantic, 10% BM25 (minimal BM25)

Usage:
    python scripts/tune-bm25-fusion-weights.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from raglite.retrieval.search import hybrid_search
from tests.fixtures.ground_truth import GROUND_TRUTH_QA


async def tune_bm25_fusion_weights():
    """Tune BM25 fusion alpha parameter for optimal accuracy.

    Tests multiple alpha values and selects the one with highest
    retrieval accuracy on ground truth test set.
    """
    alpha_values = [0.7, 0.75, 0.8, 0.85, 0.9]
    results = {}

    print("=" * 80)
    print("BM25 FUSION WEIGHT TUNING")
    print("=" * 80)
    print(
        f"\nTesting {len(alpha_values)} alpha values on {len(GROUND_TRUTH_QA)} ground truth queries"
    )
    print("\nAlpha Parameter:")
    print("  - Controls semantic vs BM25 weight in hybrid search")
    print("  - alpha = 0.7 → 70% semantic, 30% BM25 (current default)")
    print("  - Higher alpha → More semantic weight, less BM25 influence")
    print("\n" + "=" * 80)

    for alpha in alpha_values:
        print(
            f"\nTesting alpha={alpha} (semantic={alpha * 100:.0f}%, BM25={(1 - alpha) * 100:.0f}%)..."
        )

        correct_count = 0
        total_count = 0

        for qa in GROUND_TRUTH_QA:
            query = qa["question"]
            expected_page = qa.get("expected_page_number")

            if not expected_page:
                continue  # Skip queries without page references

            total_count += 1

            # Run hybrid search with current alpha
            try:
                search_results = await hybrid_search(
                    query,
                    top_k=5,
                    alpha=alpha,
                    auto_classify=False,  # Disable auto-classification for clean testing
                )

                # Check if expected page in top-5 results
                retrieved_pages = [r.page_number for r in search_results]
                if expected_page in retrieved_pages:
                    correct_count += 1

            except Exception as e:
                print(f"  Error on query '{query[:50]}...': {e}")
                continue

        accuracy = (correct_count / total_count) * 100 if total_count > 0 else 0.0
        results[alpha] = {
            "accuracy": accuracy,
            "correct": correct_count,
            "total": total_count,
        }

        print(f"  Accuracy: {accuracy:.1f}% ({correct_count}/{total_count})")

    # Find best alpha
    if not results:
        print("\n❌ ERROR: No results collected")
        return None

    best_alpha, best_result = max(results.items(), key=lambda x: x[1]["accuracy"])

    print("\n" + "=" * 80)
    print("\nTUNING RESULTS:")
    print("=" * 80)
    print(f"\nBest alpha: {best_alpha} (accuracy: {best_result['accuracy']:.1f}%)")
    print(f"  → Semantic weight: {best_alpha * 100:.0f}%")
    print(f"  → BM25 weight: {(1 - best_alpha) * 100:.0f}%")

    # Show all results sorted by accuracy
    print("\nAll Results (sorted by accuracy):")
    for alpha, result in sorted(results.items(), key=lambda x: x[1]["accuracy"], reverse=True):
        print(f"  alpha={alpha}: {result['accuracy']:.1f}% ({result['correct']}/{result['total']})")

    # Recommendations
    print("\n" + "=" * 80)
    print("\nRECOMMENDATIONS:")
    print("=" * 80)

    if best_alpha >= 0.85:
        print("\n✓ High semantic weight recommended")
        print(f"  • Best alpha: {best_alpha} (reduces BM25 influence)")
        print("  • BM25 may be upranking wrong chunks (keyword matches over semantics)")
        print(f"  • Update hybrid_search() default: alpha={best_alpha}")
    elif best_alpha <= 0.75:
        print("\n✓ Balanced fusion recommended")
        print(f"  • Best alpha: {best_alpha}")
        print("  • BM25 is helpful for keyword matching in financial domain")
        print("  • Current balance is appropriate")
    else:
        print("\n✓ Moderate semantic emphasis recommended")
        print(f"  • Best alpha: {best_alpha}")
        print("  • Slightly reduce BM25 influence from current default")
        print(f"  • Update hybrid_search() default: alpha={best_alpha}")

    # Calculate improvement over current default (0.7)
    default_accuracy = results.get(0.7, {}).get("accuracy", 0.0)
    improvement = best_result["accuracy"] - default_accuracy

    print("\nAccuracy Improvement:")
    print(f"  Current default (alpha=0.7): {default_accuracy:.1f}%")
    print(f"  Best tuned (alpha={best_alpha}): {best_result['accuracy']:.1f}%")
    print(f"  Improvement: {improvement:+.1f}pp")

    # Save results
    output_path = project_root / "docs" / "validation" / "story-2.11-bm25-tuning.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "alpha_values_tested": alpha_values,
        "results": {
            str(k): v for k, v in results.items()
        },  # Convert float keys to strings for JSON
        "best_alpha": best_alpha,
        "best_accuracy": best_result["accuracy"],
        "default_accuracy": default_accuracy,
        "improvement_pp": improvement,
        "recommendation": f"Update hybrid_search() default alpha to {best_alpha}",
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nResults saved to: {output_path}")
    print("\n" + "=" * 80)

    return best_alpha


if __name__ == "__main__":
    print("\n")
    best_alpha = asyncio.run(tune_bm25_fusion_weights())
    if best_alpha is not None:
        print(f"\n✅ Recommended alpha for production: {best_alpha}")
        print("   Update in: raglite/retrieval/search.py")
        print("   Function: hybrid_search()")
        print(f"   Parameter: alpha: float = {best_alpha}")
    else:
        print("\n❌ Tuning failed - check error messages above")
    print("\n")
