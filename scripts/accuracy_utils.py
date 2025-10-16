"""Shared accuracy calculation utilities for RAGLite validation scripts.

This module provides reusable functions for retrieval accuracy, attribution accuracy,
and performance metrics calculations used across multiple validation scripts.
"""

import re
from typing import Any, TypedDict


class RetrievalResult(TypedDict):
    """Result of retrieval accuracy check."""

    pass_: bool
    reason: str
    matched_keywords: list[str]
    expected_keywords: list[str]


class AttributionResult(TypedDict):
    """Result of attribution accuracy check."""

    pass_: bool
    reason: str
    expected_page: int
    pages_checked: list[dict[str, Any]]


class PerformanceMetrics(TypedDict):
    """Performance metrics for query execution."""

    total_queries: int
    retrieval_accuracy: float
    attribution_accuracy: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    avg_latency_ms: float
    errors: int
    retrieval_pass: int
    attribution_pass: int


# Configuration constants
KEYWORD_MATCH_THRESHOLD = 0.5  # 50% of keywords must match
PAGE_TOLERANCE = 1  # ±1 page tolerance for attribution
NFR6_RETRIEVAL_TARGET = 90.0  # NFR6: 90%+ retrieval accuracy
NFR7_ATTRIBUTION_TARGET = 95.0  # NFR7: 95%+ attribution accuracy
NFR13_P50_TARGET_MS = 5000.0  # NFR13: p50 <5s
NFR13_P95_TARGET_MS = 15000.0  # NFR13: p95 <15s
EARLY_WARNING_THRESHOLD = 70.0  # Trigger investigation if <70%


def normalize_numbers(text: str) -> str:
    """Normalize numbers to handle both American and European formatting.

    Makes keyword matching format-agnostic by converting both formats to canonical form:
    - American: 23.2, 1,234.56 → 23.2, 1234.56
    - European: 23,2, 1 234,56 → 23.2, 1234.56

    This allows ground truth with American format (23.2) to match PDF with European format (23,2).

    Args:
        text: Text containing numbers in any format

    Returns:
        Text with normalized numbers
    """
    # Pattern 1: European decimals (23,2 or 23,25) → American format (23.2 or 23.25)
    # Match: digit(s), comma, 1-2 digits, word boundary
    # This catches European decimal notation
    text = re.sub(r"(\d+),(\d{1,2})\b", r"\1.\2", text)

    # Pattern 2: European thousands separator (1 234 567) → remove spaces
    # Match: digit(s), space(s), 3 digits (repeat as needed)
    text = re.sub(r"(\d)\s+(\d{3})", r"\1\2", text)

    # Pattern 3: American thousands separator (1,234,567) → remove commas
    # Match: digit(s), comma, 3 digits (repeat as needed)
    # After pattern 1, remaining commas are thousands separators
    text = re.sub(r"(\d+),(\d{3})", r"\1\2", text)

    return text


def check_retrieval_accuracy(qa: dict[str, Any], results: list[Any]) -> RetrievalResult:
    """Check if retrieved chunks contain expected answer.

    Args:
        qa: Ground truth question dict with expected_keywords
        results: List of QueryResult objects from query

    Returns:
        Dict with pass/fail status and details
    """
    if not results:
        return {
            "pass_": False,
            "reason": "No results returned",
            "matched_keywords": [],
            "expected_keywords": qa["expected_keywords"],
        }

    # Check if any expected keywords appear in returned chunks
    all_text = " ".join([r.text.lower() for r in results])

    # Normalize numbers in text to handle both American (23.2) and European (23,2) formats
    normalized_text = normalize_numbers(all_text)

    # Check each keyword with normalization
    matched_keywords = []
    for kw in qa["expected_keywords"]:
        normalized_kw = normalize_numbers(kw.lower())
        if normalized_kw in normalized_text:
            matched_keywords.append(kw)

    # Pass if at least KEYWORD_MATCH_THRESHOLD of expected keywords found
    threshold = len(qa["expected_keywords"]) * KEYWORD_MATCH_THRESHOLD
    passed = len(matched_keywords) >= threshold

    return {
        "pass_": passed,
        "reason": (
            f"Found {len(matched_keywords)}/{len(qa['expected_keywords'])} keywords"
            if passed
            else f"Only {len(matched_keywords)}/{len(qa['expected_keywords'])} keywords found (need ≥{threshold:.0f})"
        ),
        "matched_keywords": matched_keywords,
        "expected_keywords": qa["expected_keywords"],
    }


def check_attribution_accuracy(qa: dict[str, Any], results: list[Any]) -> AttributionResult:
    """Check if source attribution is correct (±PAGE_TOLERANCE).

    Args:
        qa: Ground truth question dict with expected_page_number
        results: List of QueryResult objects from query

    Returns:
        Dict with pass/fail status and details
    """
    if not results:
        return {
            "pass_": False,
            "reason": "No results returned",
            "expected_page": qa["expected_page_number"],
            "pages_checked": [],
        }

    expected_page = qa["expected_page_number"]
    pages_checked = []

    for result in results:
        if result.page_number is None:
            pages_checked.append({"page": None, "match": False, "reason": "Missing page metadata"})
            continue

        # ±PAGE_TOLERANCE for boundary chunks
        page_diff = abs(result.page_number - expected_page)
        is_match = page_diff <= PAGE_TOLERANCE

        pages_checked.append(
            {
                "page": result.page_number,
                "match": is_match,
                "diff": page_diff,
            }
        )

    # Pass if any result has correct page (±PAGE_TOLERANCE)
    any_correct = any(p["match"] for p in pages_checked)

    return {
        "pass_": any_correct,
        "reason": (
            f"Found correct page (±{PAGE_TOLERANCE}): {expected_page}"
            if any_correct
            else f"Expected page {expected_page} (±{PAGE_TOLERANCE}), got {[p['page'] for p in pages_checked]}"
        ),
        "expected_page": expected_page,
        "pages_checked": pages_checked,
    }


def calculate_performance_metrics(results: list[dict[str, Any]]) -> PerformanceMetrics:
    """Calculate aggregate performance metrics from query results.

    Args:
        results: List of query result dicts

    Returns:
        Dict with aggregate metrics
    """
    total_queries = len(results)
    if total_queries == 0:
        return {
            "total_queries": 0,
            "retrieval_accuracy": 0.0,
            "attribution_accuracy": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "min_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "avg_latency_ms": 0.0,
            "errors": 0,
            "retrieval_pass": 0,
            "attribution_pass": 0,
        }

    # Calculate accuracy metrics
    retrieval_pass = sum(
        1
        for r in results
        if r.get("retrieval", {}).get("pass_", False) or r.get("retrieval_pass", False)
    )
    attribution_pass = sum(
        1
        for r in results
        if r.get("attribution", {}).get("pass_", False) or r.get("attribution_pass", False)
    )
    errors = sum(1 for r in results if r.get("error") is not None)

    retrieval_accuracy = (retrieval_pass / total_queries) * 100
    attribution_accuracy = (attribution_pass / total_queries) * 100

    # Calculate latency percentiles
    latencies = sorted([r["latency_ms"] for r in results])
    p50_idx = int(len(latencies) * 0.50)
    p95_idx = int(len(latencies) * 0.95)
    p99_idx = int(len(latencies) * 0.99)

    p50_latency = latencies[p50_idx] if p50_idx < len(latencies) else latencies[-1]
    p95_latency = latencies[p95_idx] if p95_idx < len(latencies) else latencies[-1]
    p99_latency = latencies[p99_idx] if p99_idx < len(latencies) else latencies[-1]

    return {
        "total_queries": total_queries,
        "retrieval_accuracy": retrieval_accuracy,
        "attribution_accuracy": attribution_accuracy,
        "p50_latency_ms": p50_latency,
        "p95_latency_ms": p95_latency,
        "p99_latency_ms": p99_latency,
        "min_latency_ms": min(latencies),
        "max_latency_ms": max(latencies),
        "avg_latency_ms": sum(latencies) / len(latencies),
        "errors": errors,
        "retrieval_pass": retrieval_pass,
        "attribution_pass": attribution_pass,
    }


def check_nfr_compliance(metrics: PerformanceMetrics) -> dict[str, bool]:
    """Check if metrics meet NFR targets.

    Args:
        metrics: Performance metrics dict

    Returns:
        Dict with NFR compliance status
    """
    return {
        "nfr6_retrieval": metrics["retrieval_accuracy"] >= NFR6_RETRIEVAL_TARGET,
        "nfr7_attribution": metrics["attribution_accuracy"] >= NFR7_ATTRIBUTION_TARGET,
        "nfr13_p50": metrics["p50_latency_ms"] < NFR13_P50_TARGET_MS,
        "nfr13_p95": metrics["p95_latency_ms"] < NFR13_P95_TARGET_MS,
    }


def should_trigger_early_warning(accuracy: float) -> bool:
    """Check if accuracy triggers early warning.

    Args:
        accuracy: Current retrieval accuracy percentage

    Returns:
        True if early warning should be triggered
    """
    return accuracy < EARLY_WARNING_THRESHOLD
