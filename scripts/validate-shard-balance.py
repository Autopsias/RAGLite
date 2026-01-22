#!/usr/bin/env python3
"""
Validate CI shard balance to ensure tests are distributed evenly.

This script counts tests per shard based on the CI matrix configuration
and reports distribution percentage. It fails if imbalance exceeds threshold.

Usage:
    python scripts/validate-shard-balance.py [--threshold 30]
"""

import subprocess
import sys
from pathlib import Path

# Shard configuration matching ci-linux.yml
SHARDS = {
    "postgresql": {
        "pytest_paths": [
            "tests/integration/forecasting/",
            "tests/integration/model_selection/",
            "tests/integration/external_data/",
            "tests/integration/insights/",
            "tests/integration/test_adaptive_catboost_weights.py",
            "tests/integration/test_auto_forecast_update.py",
            "tests/integration/test_catboost_core.py",
            "tests/integration/test_chronos_ensemble.py",
            "tests/integration/test_demand_regressors.py",
            "tests/integration/test_ensemble_real_data.py",
            "tests/integration/test_epic6_core.py",
            "tests/integration/test_forecast_external.py",
            "tests/integration/test_external_data_core.py",
            "tests/integration/test_external_data_schema.py",
            "tests/integration/test_ecb_macro_core.py",
        ],
    },
    "retrieval": {
        "pytest_paths": [
            "tests/integration/chunking/",
            "tests/integration/ingestion/",
            "tests/integration/retrieval/",
            "tests/integration/story_2_14/",
            "tests/integration/ac3_ground_truth/",
            "tests/integration/parallel_ingestion/",
            "tests/integration/test_analytical_core.py",
            "tests/integration/test_chunking_consistency.py",
            "tests/integration/test_chunking_core.py",
            "tests/integration/test_metadata_core.py",
            "tests/integration/test_hybrid_search_integration.py",
            "tests/integration/test_main_integration.py",
            "tests/integration/test_retrieval_core.py",
            "tests/integration/test_pypdfium_ingestion.py",
            "tests/integration/test_e2e_query_validation.py",
            "tests/integration/test_sql_routing.py",
            "tests/integration/test_multi_index_integration.py",
            "tests/integration/test_document_segregation.py",
            "tests/integration/test_excerpt_validation_core.py",
            "tests/integration/test_parallel_ingestion.py",
            "tests/integration/test_page_parallelism.py",
        ],
    },
    "mcp": {
        "pytest_paths": [
            "tests/integration/mcp/",
            "tests/integration/story_6_23/",
            "tests/integration/external_data_mcp/",
            "tests/integration/epic6/",
            "tests/integration/helpers/",
            "tests/integration/test_agentic_framework.py",
            "tests/integration/test_agentic_workflow_suite.py",
            "tests/integration/test_analysis_agent_workflow.py",
            "tests/integration/test_mcp_server.py",
            "tests/integration/test_mcp_validation_integration.py",
            "tests/integration/test_story_6_23_mcp_tools.py",
            "tests/integration/test_external_data_mcp_core.py",
            "tests/integration/test_mcp_async_ingestion.py",
            "tests/integration/test_mcp_response_validation.py",
        ],
    },
}


def count_tests_in_path(path: str) -> int:
    """Count tests using pytest --collect-only."""
    path_obj = Path(path)
    if not path_obj.exists():
        return 0

    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "--collect-only", "-q", path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Count lines that look like test names (contain ::)
        test_lines = [
            line for line in result.stdout.split("\n") if "::" in line and "test" in line.lower()
        ]
        return len(test_lines)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate CI shard balance")
    parser.add_argument(
        "--threshold",
        type=int,
        default=30,
        help="Max imbalance percentage before failing (default: 30)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    print("=== CI Shard Balance Validation ===\n")

    shard_counts = {}
    total_tests = 0

    for shard_name, config in SHARDS.items():
        count = 0
        for path in config["pytest_paths"]:
            path_count = count_tests_in_path(path)
            count += path_count
            if args.verbose:
                print(f"  {path}: {path_count} tests")
        shard_counts[shard_name] = count
        total_tests += count
        print(f"{shard_name}: {count} tests")

    print(f"\nTotal: {total_tests} tests across {len(SHARDS)} shards")

    if total_tests == 0:
        print("\nWARNING: No tests found. Check pytest configuration.")
        sys.exit(1)

    # Calculate distribution
    avg_tests = total_tests / len(SHARDS)
    print(f"Average per shard: {avg_tests:.1f} tests")
    print("\n=== Distribution Analysis ===")

    max_deviation = 0
    for shard_name, count in shard_counts.items():
        deviation = abs(count - avg_tests) / avg_tests * 100 if avg_tests > 0 else 0
        max_deviation = max(max_deviation, deviation)
        pct = count / total_tests * 100
        status = "OK" if deviation <= args.threshold else "IMBALANCED"
        print(f"{shard_name}: {pct:.1f}% ({deviation:+.1f}% from avg) - {status}")

    print(f"\nMax deviation: {max_deviation:.1f}%")
    print(f"Threshold: {args.threshold}%")

    if max_deviation > args.threshold:
        print(f"\nFAIL: Shard imbalance exceeds {args.threshold}% threshold")
        print("Consider rebalancing tests across shards in ci-linux.yml")
        sys.exit(1)
    else:
        print("\nPASS: Shard balance is within acceptable threshold")
        sys.exit(0)


if __name__ == "__main__":
    main()
