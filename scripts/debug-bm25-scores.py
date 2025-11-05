#!/usr/bin/env python3
"""Debug BM25 scores to understand why hybrid search isn't improving accuracy."""

import sys
from pathlib import Path

import numpy as np

# Add project root to path (must happen before raglite imports)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from raglite.shared.bm25 import compute_bm25_scores, load_bm25_index  # noqa: E402
from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402


def analyze_bm25_scores():
    """Analyze BM25 scores for sample queries."""
    print("=" * 80)
    print("BM25 SCORE ANALYSIS - Story 2.1 Debug")
    print("=" * 80)
    print()

    # Load BM25 index
    try:
        bm25, tokenized_docs = load_bm25_index()
        print(f"✓ BM25 index loaded: {len(tokenized_docs)} documents")
        print()
    except Exception as e:
        print(f"✗ Failed to load BM25 index: {e}")
        return

    # Test with 5 sample queries
    test_queries = [
        GROUND_TRUTH_QA[8],  # Variable cost (23.2) - exact number query
        GROUND_TRUTH_QA[9],  # EBITDA margin - financial term query
        GROUND_TRUTH_QA[0],  # First query
        GROUND_TRUTH_QA[24],  # Mid query
        GROUND_TRUTH_QA[49],  # Last query
    ]

    for i, qa in enumerate(test_queries, start=1):
        query = qa["question"]
        expected_page = qa["expected_page_number"]

        print(f"[{i}/5] Query: {query[:70]}...")
        print(f"      Expected page: {expected_page}")

        # Compute BM25 scores
        bm25_scores = compute_bm25_scores(bm25, query)

        # Get statistics
        bm25_array = np.array(bm25_scores)
        non_zero = np.count_nonzero(bm25_array)

        print("      BM25 scores:")
        print(f"        - Total docs: {len(bm25_scores)}")
        print(f"        - Non-zero scores: {non_zero} ({non_zero / len(bm25_scores) * 100:.1f}%)")
        print(f"        - Max score: {bm25_array.max():.4f}")
        print(f"        - Mean score: {bm25_array.mean():.4f}")
        print(f"        - Median score: {np.median(bm25_array):.4f}")
        print(f"        - Std dev: {bm25_array.std():.4f}")

        # Top-5 BM25 matches
        top_5_indices = np.argsort(bm25_scores)[-5:][::-1]
        print("      Top-5 BM25 chunks:")
        for rank, idx in enumerate(top_5_indices, start=1):
            score = bm25_scores[idx]
            # Estimate page from chunk index (roughly 2 chunks per page)
            estimated_page = idx // 2 + 1
            print(f"        {rank}. Chunk {idx} (est. page {estimated_page}): score={score:.4f}")

        print()


if __name__ == "__main__":
    analyze_bm25_scores()
