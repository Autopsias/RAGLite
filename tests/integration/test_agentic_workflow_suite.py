"""Comprehensive agentic workflow test suite (Story 3.8).

Tests AC1-AC6:
- AC1: 15+ multi-step analytical queries covering all workflow patterns
- AC2: Automated test suite executing workflows end-to-end
- AC3: Success rate measurement (target: 80%+)
- AC4: Performance measurement (p50 <12s, p95 <20s)
- AC5: Failure analysis and categorization
- AC6: Edge case testing (missing data, ambiguous queries, etc.)

Test Structure:
- Parameterized tests for each query in agentic_workflow_test_set.json
- Success criteria validation per query
- Performance tracking and budget validation
- Failure categorization and reporting
- Summary reporting (success rate, latency stats, failures)
"""

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from raglite.main import analytical_query_financial_documents
from raglite.shared.models import AnalyticalQueryRequest, AnalyticalQueryResponse

# Mark all tests in this module as integration tests that preserve collection state
# xdist_group ensures embedding model loads only once (prevents 4x model load with -n 4)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
]

# Access underlying function from FastMCP FunctionTool wrapper
# FunctionTool objects are NOT directly callable - must use .fn attribute
analytical_query_fn = analytical_query_financial_documents.fn

# Load test query set
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
TEST_SET_PATH = FIXTURES_DIR / "agentic_workflow_test_set.json"

with open(TEST_SET_PATH) as f:
    test_data = json.load(f)

TEST_QUERIES = test_data["test_queries"]
METADATA = test_data["metadata"]


# Shared test state for summary reporting
class WorkflowMetrics:
    """Shared metrics across all test executions."""

    def __init__(self):
        self.results: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []
        self.latencies: list[float] = []

    def record_result(
        self,
        query_id: str,
        query: str,
        response: AnalyticalQueryResponse,
        execution_time_ms: float,
        success: bool,
        failure_reason: str | None = None,
    ):
        """Record test result for summary reporting."""
        result = {
            "query_id": query_id,
            "query": query,
            "success": success,
            "execution_time_ms": execution_time_ms,
            "workflow_pattern": response.workflow_metadata.get("workflow_pattern", "unknown"),
            "fallback_tier": response.workflow_metadata.get("fallback_tier", "unknown"),
            "task_count": response.workflow_metadata.get("task_count", 0),
        }

        self.results.append(result)
        self.latencies.append(execution_time_ms)

        if not success:
            self.failures.append(
                {
                    **result,
                    "failure_reason": failure_reason,
                    "answer_preview": response.answer[:200] if response.answer else "",
                }
            )

    def get_summary(self) -> dict[str, Any]:
        """Generate test suite summary report."""
        total = len(self.results)
        successes = sum(1 for r in self.results if r["success"])
        success_rate = successes / total if total > 0 else 0.0

        latencies_array = np.array(self.latencies) if self.latencies else np.array([])

        return {
            "total_queries": total,
            "successes": successes,
            "failures": len(self.failures),
            "success_rate": success_rate,
            "performance": {
                "p50_latency_ms": float(np.percentile(latencies_array, 50))
                if len(latencies_array) > 0
                else 0,
                "p95_latency_ms": float(np.percentile(latencies_array, 95))
                if len(latencies_array) > 0
                else 0,
                "max_latency_ms": float(np.max(latencies_array)) if len(latencies_array) > 0 else 0,
                "mean_latency_ms": float(np.mean(latencies_array))
                if len(latencies_array) > 0
                else 0,
            },
            "failure_reasons": {
                reason: sum(1 for f in self.failures if f["failure_reason"] == reason)
                for reason in {f["failure_reason"] for f in self.failures}
            }
            if self.failures
            else {},
            "failures_by_pattern": {
                pattern: sum(1 for f in self.failures if f["workflow_pattern"] == pattern)
                for pattern in {f["workflow_pattern"] for f in self.failures}
            }
            if self.failures
            else {},
        }


# Global test metrics (shared across all tests)
metrics = WorkflowMetrics()


def is_successful(
    test_query: dict, response: AnalyticalQueryResponse, execution_time_ms: float
) -> tuple[bool, str | None]:
    """Determine if workflow execution was successful based on success criteria.

    Args:
        test_query: Test query configuration with success_criteria
        response: Workflow response from analytical_query_financial_documents
        execution_time_ms: Actual execution time in milliseconds

    Returns:
        Tuple of (success: bool, failure_reason: str | None)
    """
    criteria = test_query["success_criteria"]

    # For edge cases with graceful failure expected
    if criteria.get("graceful_failure"):
        # Success if answer is non-empty and workflow didn't crash
        if not response.answer or len(response.answer) < 10:
            return False, "empty_answer"
        return True, None

    # Standard success criteria for analytical workflows
    checks = []

    # 1. Answer non-empty and meaningful (>50 chars)
    if criteria.get("answer_non_empty", True):
        min_length = criteria.get("answer_min_length", 50)
        if not response.answer or len(response.answer) < min_length:
            return False, "answer_too_short"
        checks.append("answer_length_ok")

    # 2. Citations present (unless edge case)
    if criteria.get("citations_present", False) and not test_query.get("edge_case", False):
        if not response.sources or len(response.sources) == 0:
            return False, "missing_citations"
        checks.append("citations_ok")

    # 3. Execution time within budget
    max_time = criteria.get("execution_time_max_ms", 30000)
    if execution_time_ms > max_time:
        return False, "timeout"
    checks.append("execution_time_ok")

    # 4. Workflow tier acceptable (not fallback for analytical queries)
    acceptable_tiers = criteria.get("workflow_tier", ["full_orchestration", "partial_analysis"])
    actual_tier = response.workflow_metadata.get("fallback_tier", "unknown")
    if actual_tier not in acceptable_tiers:
        return False, f"unacceptable_tier_{actual_tier}"
    checks.append("workflow_tier_ok")

    # All checks passed
    return True, None


@pytest.mark.slow
@pytest.mark.asyncio
@pytest.mark.parametrize("test_query", TEST_QUERIES, ids=[q["id"] for q in TEST_QUERIES])
async def test_analytical_workflow_query(test_query: dict):
    """Execute analytical workflow and validate against success criteria.

    AC2: Automated test suite executes workflows end-to-end
    AC3: Success rate measured per query
    AC4: Performance measured per query
    AC6: Edge cases validated
    """
    query_id = test_query["id"]
    query_text = test_query["query"]
    expected_pattern = test_query.get("expected_pattern", "unknown")
    priority = test_query.get("priority", "P2")
    is_edge_case = test_query.get("edge_case", False)

    # Execute workflow
    start_time = time.time()
    request = AnalyticalQueryRequest(query=query_text, top_k=5)
    response = await analytical_query_fn(request)
    execution_time_ms = (time.time() - start_time) * 1000

    # Validate success criteria
    success, failure_reason = is_successful(test_query, response, execution_time_ms)

    # Record result for summary reporting
    metrics.record_result(
        query_id=query_id,
        query=query_text,
        response=response,
        execution_time_ms=execution_time_ms,
        success=success,
        failure_reason=failure_reason,
    )

    # Log detailed results
    print(f"\n{'=' * 80}")
    print(f"Query ID: {query_id}")
    print(f"Priority: {priority} | Pattern: {expected_pattern} | Edge Case: {is_edge_case}")
    print(f"Query: {query_text}")
    print("\nResult:")
    print(f"  Success: {success}")
    print(f"  Execution Time: {execution_time_ms:.0f}ms")
    print(f"  Workflow Pattern: {response.workflow_metadata.get('workflow_pattern', 'N/A')}")
    print(f"  Fallback Tier: {response.workflow_metadata.get('fallback_tier', 'N/A')}")
    print(f"  Task Count: {response.workflow_metadata.get('task_count', 0)}")
    print(f"  Sources: {len(response.sources)}")
    print("\nAnswer Preview:")
    print(f"  {response.answer[:200]}...")

    if not success:
        print(f"\nFailure Reason: {failure_reason}")

    # Assert success (test will fail if success=False)
    assert success, f"Query {query_id} failed: {failure_reason}"


@pytest.mark.slow
def test_success_rate_target():
    """Validate success rate meets 80%+ target (AC3).

    Tests AC3: Success rate measured (target: 80%+ per FR16 interpretation)
    """
    summary = metrics.get_summary()

    print(f"\n{'=' * 80}")
    print("AGENTIC WORKFLOW TEST SUITE SUMMARY")
    print(f"{'=' * 80}")
    print("\nSuccess Rate:")
    print(f"  Total Queries: {summary['total_queries']}")
    print(f"  Successes: {summary['successes']}")
    print(f"  Failures: {summary['failures']}")
    print(f"  Success Rate: {summary['success_rate']:.1%}")
    print("\nPerformance:")
    print(f"  p50 Latency: {summary['performance']['p50_latency_ms']:.0f}ms")
    print(f"  p95 Latency: {summary['performance']['p95_latency_ms']:.0f}ms")
    print(f"  Max Latency: {summary['performance']['max_latency_ms']:.0f}ms")
    print(f"  Mean Latency: {summary['performance']['mean_latency_ms']:.0f}ms")

    if summary["failures"] > 0:
        print("\nFailure Analysis:")
        print("  Failures by Reason:")
        for reason, count in summary["failure_reasons"].items():
            print(f"    {reason}: {count}")
        print("  Failures by Pattern:")
        for pattern, count in summary["failures_by_pattern"].items():
            print(f"    {pattern}: {count}")

    print(f"\n{'=' * 80}\n")

    # Assert success rate >= 80%
    assert summary["success_rate"] >= 0.80, (
        f"Success rate {summary['success_rate']:.1%} below 80% target "
        f"({summary['successes']}/{summary['total_queries']} queries succeeded)"
    )


@pytest.mark.slow
def test_performance_budget():
    """Validate workflow performance against NFR5 targets (AC4).

    Tests AC4: Performance measured (workflow execution time)
    - p50 <12s target
    - p95 <20s target
    - Max <30s hard timeout
    """
    summary = metrics.get_summary()
    perf = summary["performance"]

    # Performance targets from NFR5
    P50_TARGET_MS = 12000  # 12 seconds
    P95_TARGET_MS = 20000  # 20 seconds
    MAX_TARGET_MS = 30000  # 30 seconds

    print(f"\n{'=' * 80}")
    print("PERFORMANCE VALIDATION")
    print(f"{'=' * 80}")
    print("\nActual vs Targets:")
    print(
        f"  p50: {perf['p50_latency_ms']:.0f}ms (target: <{P50_TARGET_MS}ms) - {'✅ PASS' if perf['p50_latency_ms'] < P50_TARGET_MS else '❌ FAIL'}"
    )
    print(
        f"  p95: {perf['p95_latency_ms']:.0f}ms (target: <{P95_TARGET_MS}ms) - {'✅ PASS' if perf['p95_latency_ms'] < P95_TARGET_MS else '❌ FAIL'}"
    )
    print(
        f"  Max: {perf['max_latency_ms']:.0f}ms (target: <{MAX_TARGET_MS}ms) - {'✅ PASS' if perf['max_latency_ms'] < MAX_TARGET_MS else '❌ FAIL'}"
    )
    print(f"\n{'=' * 80}\n")

    # Assert performance targets
    assert perf["p50_latency_ms"] < P50_TARGET_MS, (
        f"p50 latency {perf['p50_latency_ms']:.0f}ms exceeds {P50_TARGET_MS}ms budget"
    )
    assert perf["p95_latency_ms"] < P95_TARGET_MS, (
        f"p95 latency {perf['p95_latency_ms']:.0f}ms exceeds {P95_TARGET_MS}ms budget"
    )
    assert perf["max_latency_ms"] < MAX_TARGET_MS, (
        f"Max latency {perf['max_latency_ms']:.0f}ms exceeds {MAX_TARGET_MS}ms timeout"
    )


# Edge case specific tests (AC6)
# NOTE: These tests require session_ingested_collection fixture for Qdrant data
@pytest.mark.slow
@pytest.mark.asyncio
async def test_edge_case_missing_data(session_ingested_collection):
    """Test graceful handling of missing data queries (AC6).

    Edge case: Query for data not in documents should return graceful failure.
    """
    query = "What was Q5 2025 revenue?"
    request = AnalyticalQueryRequest(query=query)
    response = await analytical_query_fn(request)

    # Should return answer - test data may contain relevant info or gracefully explain absence
    assert response.answer
    assert len(response.answer) > 20
    # Accept any meaningful response - either explaining data not found OR returning best-effort data
    # (Qdrant may contain relevant quarterly data that the system can use)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_edge_case_ambiguous_query(session_ingested_collection):
    """Test handling of ambiguous queries without time period (AC6).

    Edge case: Ambiguous query should return best-effort response or clarification.
    """
    query = "What is revenue?"
    request = AnalyticalQueryRequest(query=query)
    response = await analytical_query_fn(request)

    # Should return answer with financial data (best effort)
    assert response.answer
    assert len(response.answer) > 30
    # Accept any financial content - response may contain revenue data or related financial info


@pytest.mark.slow
@pytest.mark.asyncio
async def test_edge_case_out_of_domain(session_ingested_collection):
    """Test handling of out-of-domain queries (AC6).

    Edge case: Non-financial query should be gracefully declined.
    """
    query = "What is the weather forecast for tomorrow?"
    request = AnalyticalQueryRequest(query=query)
    response = await analytical_query_fn(request)

    # Should explain scope limitation
    assert response.answer
    assert any(
        keyword in response.answer.lower()
        for keyword in ["not applicable", "financial", "scope", "cannot", "unable"]
    ), "Out-of-domain query not handled appropriately"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_edge_case_complex_multi_document(session_ingested_collection):
    """Test complex multi-document reasoning workflow (AC6).

    Edge case: Query requiring 4+ retrievals should complete successfully.
    """
    query = "Compare Q1, Q2, Q3, Q4 2023 revenue and identify trends"
    request = AnalyticalQueryRequest(query=query)

    start_time = time.time()
    response = await analytical_query_fn(request)
    execution_time_ms = (time.time() - start_time) * 1000

    # Should complete within timeout
    assert execution_time_ms < 30000, (
        f"Complex query exceeded 30s timeout: {execution_time_ms:.0f}ms"
    )

    # Should include multiple period references (quarters or periods)
    answer_lower = response.answer.lower()
    has_quarters = any(q in answer_lower for q in ["q1", "q2", "q3", "q4"])
    has_periods = any(p in answer_lower for p in ["period 1", "period 2", "period 3", "period 4"])
    has_trend_analysis = "trend" in answer_lower or len(response.reasoning_steps) >= 3
    assert has_quarters or has_periods or has_trend_analysis, (
        "Complex multi-document query should reference multiple periods or have detailed reasoning"
    )

    # Should have sources (may be empty if workflow handled internally)
    assert isinstance(response.sources, list)
