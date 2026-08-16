"""Shared data models for AC3 ground truth validation.

This module contains the dataclasses used across all AC3 validation tests.
"""

from dataclasses import dataclass


@dataclass
class QueryValidationResult:
    """Result of validating a single ground truth query.

    Attributes:
        query_id: Ground truth question ID (1-50)
        question: Natural language query text
        retrieval_success: True if correct chunk found in top-5 results
        attribution_success: True if correct document + page in top-5
        top_5_chunks: List of (source_document, page_number, chunk_index) tuples
        latency_ms: Query execution time in milliseconds
        top_score: Highest relevance score in results
        expected_page: Expected page number from ground truth
        expected_document: Expected document name from ground truth
    """

    query_id: int
    question: str
    retrieval_success: bool
    attribution_success: bool
    top_5_chunks: list[tuple[str, int | None, int]]
    latency_ms: float
    top_score: float
    expected_page: int
    expected_document: str


@dataclass
class AccuracyMetrics:
    """Aggregated accuracy metrics for all ground truth queries.

    Attributes:
        retrieval_accuracy: Percentage of queries with correct chunk in top-5
        attribution_accuracy: Percentage of queries with correct document + page
        total_queries: Total number of queries executed (should be 50)
        successful_queries: Count of retrieval successes
        failed_queries: List of QueryValidationResult objects for failures
        average_latency_ms: Mean query execution time
        p50_latency_ms: Median query execution time (p50)
        p95_latency_ms: 95th percentile query execution time (NFR13 target: <15s)
        p99_latency_ms: 99th percentile query execution time
    """

    retrieval_accuracy: float
    attribution_accuracy: float
    total_queries: int
    successful_queries: int
    failed_queries: list[QueryValidationResult]
    average_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
