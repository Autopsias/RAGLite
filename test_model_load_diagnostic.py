"""Diagnostic script to detect embedding model reload behavior.

This script helps diagnose why Test Explorer is slow by tracking model loads.
"""

import sys
import time

# Add instrumentation to track model loads
original_model_load = None
load_count = 0
load_times = []


def instrument_model_loading():
    """Monkey patch SentenceTransformer to track loads."""
    global original_model_load, load_count

    from sentence_transformers import SentenceTransformer

    original_init = SentenceTransformer.__init__

    def tracked_init(self, *args, **kwargs):
        global load_count
        load_count += 1
        start = time.time()
        result = original_init(self, *args, **kwargs)
        elapsed = time.time() - start
        load_times.append(elapsed)
        print(f"[DIAGNOSTIC] Model load #{load_count}: {elapsed:.2f}s", file=sys.stderr)
        return result

    SentenceTransformer.__init__ = tracked_init


# Install instrumentation before any imports
instrument_model_loading()

# Now import the test module (must be after instrumentation)
from tests.integration.test_hybrid_search_integration import (  # noqa: E402
    TestHybridSearchIntegration,
)


def test_single_query_model_loads():
    """Test how many times model is loaded for a single test."""
    global load_count
    load_count = 0

    print("\n[DIAGNOSTIC] Starting single query test...")
    test_instance = TestHybridSearchIntegration()

    # This should load model once
    import asyncio

    asyncio.run(test_instance.test_hybrid_search_exact_numbers())

    print("[DIAGNOSTIC] Single query test completed")
    print(f"[DIAGNOSTIC] Model loaded {load_count} times")
    print(f"[DIAGNOSTIC] Load times: {[f'{t:.2f}s' for t in load_times]}")

    assert load_count <= 1, f"Model should load at most once, but loaded {load_count} times!"


def test_multiple_queries_model_loads():
    """Test how many times model is loaded for multiple queries."""
    global load_count, load_times
    load_count = 0
    load_times = []

    print("\n[DIAGNOSTIC] Starting full ground truth test (50 queries)...")
    test_instance = TestHybridSearchIntegration()

    # This runs 50 queries - model should still only load once
    import asyncio

    try:
        asyncio.run(test_instance.test_hybrid_search_full_ground_truth())
    except AssertionError:
        # Ignore accuracy failures, we're only testing model loads
        print("[DIAGNOSTIC] Test failed (expected), but we got the diagnostic data")

    print("[DIAGNOSTIC] Full ground truth test completed")
    print(f"[DIAGNOSTIC] Model loaded {load_count} times for 50 queries")
    print(f"[DIAGNOSTIC] Load times: {[f'{t:.2f}s' for t in load_times]}")

    assert load_count <= 1, (
        f"Model should load at most once for 50 queries, but loaded {load_count} times!"
    )


if __name__ == "__main__":
    print("=" * 80)
    print("EMBEDDING MODEL LOAD DIAGNOSTIC")
    print("=" * 80)

    test_single_query_model_loads()
    test_multiple_queries_model_loads()

    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"Total model loads: {load_count}")
    print(f"Total load time: {sum(load_times):.2f}s")
    print("=" * 80)
