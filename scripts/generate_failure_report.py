#!/usr/bin/env python3
"""Generate failure analysis report from agentic workflow test results (Story 3.8 AC5).

This script parses pytest JSON output from test_agentic_workflow_suite.py and generates
a comprehensive failure analysis report with actionable insights.

Usage:
    uv run pytest tests/integration/test_agentic_workflow_suite.py \
        --json-report --json-report-file=test-reports/agentic_workflow_results.json

    python scripts/generate_failure_report.py \
        test-reports/agentic_workflow_results.json \
        test-reports/agentic_workflow_failures.json

Output:
    JSON report with:
    - Test run metadata (timestamp, total queries, success rate)
    - Detailed failure analysis (query, pattern, reason, stack trace)
    - Failure categorization (timeout, LLM error, retrieval failure, accuracy issue)
    - Actionable insights per failure type
    - Trend analysis capabilities
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def categorize_failure(failure_reason: str) -> str:
    """Categorize failure reason into standard categories.

    Args:
        failure_reason: Raw failure reason from test

    Returns:
        Standardized failure category
    """
    reason_lower = failure_reason.lower()

    if "timeout" in reason_lower or "time" in reason_lower:
        return "timeout"
    elif "llm" in reason_lower or "api" in reason_lower or "claude" in reason_lower:
        return "llm_api_error"
    elif "retrieval" in reason_lower or "qdrant" in reason_lower or "postgres" in reason_lower:
        return "retrieval_failure"
    elif "accuracy" in reason_lower or "answer" in reason_lower or "citations" in reason_lower:
        return "accuracy_issue"
    else:
        return "other"


def get_actionable_insight(failure_category: str, failure_reason: str) -> str:
    """Generate actionable insight for failure category.

    Args:
        failure_category: Standardized failure category
        failure_reason: Original failure reason

    Returns:
        Actionable recommendation for addressing the failure
    """
    insights = {
        "timeout": (
            "Optimize agent latency. Consider: (1) Parallel retrieval for independent tasks, "
            "(2) Use Claude Haiku for analysis agent (faster), (3) Reduce retrieval top_k, "
            "(4) Profile workflow execution to identify bottleneck agent."
        ),
        "llm_api_error": (
            "Handle LLM API failures gracefully. Consider: (1) Retry logic with exponential backoff, "
            "(2) Fallback to simpler prompts, (3) Monitor Claude API status, "
            "(4) Implement circuit breaker for repeated failures."
        ),
        "retrieval_failure": (
            "Improve retrieval reliability. Consider: (1) Connection pooling for Qdrant/PostgreSQL, "
            "(2) Retry transient errors, (3) Validate database health, "
            "(4) Fallback to vector-only search if hybrid fails."
        ),
        "accuracy_issue": (
            "Improve workflow accuracy. Consider: (1) Refine agent prompts for better reasoning, "
            "(2) Increase retrieval top_k for better context, (3) Add cross-encoder re-ranking, "
            "(4) Review ground truth expectations for realism."
        ),
        "other": (
            "Review error logs and stack trace for root cause. Consider filing bug report "
            "if issue is unexpected or reproducible."
        ),
    }

    return insights.get(failure_category, insights["other"])


def generate_failure_report(
    pytest_results_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Generate comprehensive failure analysis report.

    Args:
        pytest_results_path: Path to pytest JSON report
        output_path: Path to write failure report JSON

    Returns:
        Failure report dictionary
    """
    # Load pytest results
    with open(pytest_results_path) as f:
        pytest_data = json.load(f)

    # Parse test results
    tests = pytest_data.get("tests", [])
    total_queries = len(
        [t for t in tests if "test_analytical_workflow_query" in t.get("nodeid", "")]
    )

    failures = []
    for test in tests:
        if test.get("outcome") == "failed" and "test_analytical_workflow_query" in test.get(
            "nodeid", ""
        ):
            # Extract query ID from nodeid
            # Example: "tests/integration/test_agentic_workflow_suite.py::test_analytical_workflow_query[yoy_growth_1]"
            nodeid = test.get("nodeid", "")
            query_id = nodeid.split("[")[-1].rstrip("]") if "[" in nodeid else "unknown"

            # Parse failure info
            call = test.get("call", {})
            longrepr = call.get("longrepr", "")
            failure_reason = "unknown"

            # Extract failure reason from assertion message
            if "assert" in longrepr.lower():
                lines = longrepr.split("\n")
                for line in lines:
                    if "failed:" in line.lower():
                        failure_reason = line.split("failed:")[-1].strip()
                        break

            # Extract workflow metadata from test output
            setup = test.get("setup", {})
            test_output = setup.get("stdout", "") + call.get("stdout", "")

            workflow_pattern = "unknown"
            fallback_tier = "unknown"
            execution_time_ms = 0

            for line in test_output.split("\n"):
                if "Workflow Pattern:" in line:
                    workflow_pattern = line.split(":")[-1].strip()
                elif "Fallback Tier:" in line:
                    fallback_tier = line.split(":")[-1].strip()
                elif "Execution Time:" in line:
                    time_str = line.split(":")[-1].strip().replace("ms", "")
                    try:
                        execution_time_ms = float(time_str)
                    except ValueError:
                        pass

            # Categorize and add insight
            failure_category = categorize_failure(failure_reason)
            actionable_insight = get_actionable_insight(failure_category, failure_reason)

            failures.append(
                {
                    "query_id": query_id,
                    "failure_reason": failure_reason,
                    "failure_category": failure_category,
                    "workflow_pattern": workflow_pattern,
                    "fallback_tier": fallback_tier,
                    "execution_time_ms": execution_time_ms,
                    "stack_trace": longrepr,
                    "actionable_insight": actionable_insight,
                }
            )

    # Calculate success rate
    successes = total_queries - len(failures)
    success_rate = successes / total_queries if total_queries > 0 else 0.0

    # Categorize failures by type
    failure_categories = {}
    for failure in failures:
        category = failure["failure_category"]
        failure_categories[category] = failure_categories.get(category, 0) + 1

    # Build report
    report = {
        "test_run_id": datetime.now().isoformat(),
        "total_queries": total_queries,
        "successes": successes,
        "failures": len(failures),
        "success_rate": success_rate,
        "failure_categories": failure_categories,
        "failed_queries": failures,
        "summary": {
            "most_common_failure": max(failure_categories.items(), key=lambda x: x[1])[0]
            if failure_categories
            else "none",
            "recommendation": (
                get_actionable_insight(max(failure_categories.items(), key=lambda x: x[1])[0], "")
                if failure_categories
                else "All tests passed!"
            ),
        },
    }

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"✅ Failure report generated: {output_path}")
    print("\nSummary:")
    print(f"  Total Queries: {report['total_queries']}")
    print(f"  Successes: {report['successes']}")
    print(f"  Failures: {report['failures']}")
    print(f"  Success Rate: {report['success_rate']:.1%}")
    print("\nFailure Categories:")
    for category, count in report["failure_categories"].items():
        print(f"  {category}: {count}")
    print(f"\nTop Recommendation: {report['summary']['recommendation'][:100]}...")

    return report


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate failure analysis report from agentic workflow test results"
    )
    parser.add_argument(
        "pytest_results",
        type=Path,
        help="Path to pytest JSON report (e.g., test-reports/agentic_workflow_results.json)",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Path to write failure report (e.g., test-reports/agentic_workflow_failures.json)",
    )

    args = parser.parse_args()

    if not args.pytest_results.exists():
        print(f"❌ Error: pytest results file not found: {args.pytest_results}")
        print("\nRun tests first:")
        print("  uv run pytest tests/integration/test_agentic_workflow_suite.py \\")
        print("      --json-report --json-report-file=test-reports/agentic_workflow_results.json")
        return 1

    generate_failure_report(args.pytest_results, args.output)
    return 0


if __name__ == "__main__":
    exit(main())
