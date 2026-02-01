"""Test helper utilities for common testing operations.

This module provides utility functions for async operations, retries, polling,
and custom assertions used across the test suite.

Best Practices:
- Keep helpers pure and composable
- Use explicit timeouts (no infinite loops)
- Provide clear error messages on failures
- Follow pytest assertion conventions
"""

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


async def wait_for(
    condition: Callable[[], bool] | Callable[[], Any],
    timeout: float = 5.0,
    interval: float = 0.1,
    error_message: str = "Condition not met within timeout",
) -> None:
    """Wait for a condition to become true with timeout.

    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds (default: 5.0)
        interval: Time between checks in seconds (default: 0.1)
        error_message: Custom error message on timeout

    Raises:
        TimeoutError: If condition not met within timeout

    Example:
        # Wait for Qdrant count
        async def check_count():
            count = qdrant.count(collection_name).count
            return count > 0

        await wait_for(check_count, timeout=10.0)

        # Wait for specific value
        await wait_for(lambda: result.status == "completed")
    """
    start_time = asyncio.get_event_loop().time()
    end_time = start_time + timeout

    while asyncio.get_event_loop().time() < end_time:
        try:
            result = condition()
            if asyncio.iscoroutine(result):
                result = await result
            if result:
                return
        except Exception:
            # Condition raised exception - continue waiting
            pass

        await asyncio.sleep(interval)

    raise TimeoutError(f"{error_message} (waited {timeout}s)")


async def retry(
    func: Callable[[], T],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> T:
    """Retry a function with exponential backoff.

    Args:
        func: Callable to retry (can be async or sync)
        max_attempts: Maximum number of attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff: Backoff multiplier for delay (default: 2.0)
        exceptions: Tuple of exceptions to catch (default: all exceptions)

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries failed

    Example:
        # Retry API call
        result = await retry(lambda: api_client.get("/data"))

        # Retry with custom params
        result = await retry(
            lambda: unstable_operation(),
            max_attempts=5,
            delay=0.5,
            exceptions=(ConnectionError, TimeoutError)
        )
    """
    last_exception = None
    current_delay = delay

    for attempt in range(max_attempts):
        try:
            result = func()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                raise last_exception from e

    # Should never reach here, but for type safety
    raise last_exception  # type: ignore


def assert_embedding_valid(embedding: list[float], expected_dim: int = 1024) -> None:
    """Assert that embedding vector is valid.

    Args:
        embedding: Embedding vector to validate
        expected_dim: Expected dimension (default: 1024 for Fin-E5)

    Raises:
        AssertionError: If embedding is invalid

    Example:
        chunk = await get_chunk()
        assert_embedding_valid(chunk.embedding)
    """
    assert embedding is not None, "Embedding is None"
    assert isinstance(embedding, list), f"Embedding is not a list: {type(embedding)}"
    assert len(embedding) == expected_dim, (
        f"Expected {expected_dim} dimensions, got {len(embedding)}"
    )
    assert all(isinstance(x, (int, float)) for x in embedding), (
        "Embedding contains non-numeric values"
    )


def assert_chunks_equal(chunk1: Any, chunk2: Any, ignore_fields: list[str] | None = None) -> None:
    """Assert that two chunks are equal, optionally ignoring specific fields.

    Args:
        chunk1: First chunk to compare
        chunk2: Second chunk to compare
        ignore_fields: List of field names to ignore (e.g., ["chunk_id", "embedding"])

    Raises:
        AssertionError: If chunks differ in non-ignored fields

    Example:
        assert_chunks_equal(chunk1, chunk2)
        assert_chunks_equal(chunk1, chunk2, ignore_fields=["embedding"])
    """
    ignore_fields = ignore_fields or []

    # Convert to dict for comparison
    dict1 = chunk1.model_dump() if hasattr(chunk1, "model_dump") else chunk1.__dict__
    dict2 = chunk2.model_dump() if hasattr(chunk2, "model_dump") else chunk2.__dict__

    # Remove ignored fields
    for field in ignore_fields:
        dict1.pop(field, None)
        dict2.pop(field, None)

    assert dict1 == dict2, f"Chunks differ:\n{dict1}\nvs\n{dict2}"


def assert_qdrant_collection_count(
    client: Any, collection_name: str, expected_count: int, tolerance: int = 0
) -> None:
    """Assert Qdrant collection has expected number of chunks.

    Args:
        client: Qdrant client instance
        collection_name: Name of collection to check
        expected_count: Expected number of chunks
        tolerance: Allowed variance (default: 0 for exact match)

    Raises:
        AssertionError: If count is outside tolerance

    Example:
        assert_qdrant_collection_count(qdrant, "docs", 100)
        assert_qdrant_collection_count(qdrant, "docs", 100, tolerance=5)  # 95-105 OK
    """
    actual_count = client.count(collection_name=collection_name).count
    min_count = expected_count - tolerance
    max_count = expected_count + tolerance

    assert min_count <= actual_count <= max_count, (
        f"Collection '{collection_name}' has {actual_count} chunks, "
        f"expected {expected_count} (±{tolerance})"
    )


def assert_search_results_valid(
    results: list[Any],
    min_results: int = 1,
    max_results: int | None = None,
    min_score: float = 0.0,
) -> None:
    """Assert search results are valid.

    Args:
        results: List of search results (Qdrant ScoredPoint or custom)
        min_results: Minimum expected results (default: 1)
        max_results: Maximum expected results (default: no limit)
        min_score: Minimum score threshold (default: 0.0)

    Raises:
        AssertionError: If results invalid

    Example:
        results = qdrant.search(...)
        assert_search_results_valid(results, min_results=5, min_score=0.7)
    """
    assert len(results) >= min_results, (
        f"Expected at least {min_results} results, got {len(results)}"
    )

    if max_results is not None:
        assert len(results) <= max_results, (
            f"Expected at most {max_results} results, got {len(results)}"
        )

    for idx, result in enumerate(results):
        score = result.score if hasattr(result, "score") else result.get("score")
        assert score >= min_score, f"Result {idx} has score {score} < minimum {min_score}"


def truncate_string(s: str, max_length: int = 100) -> str:
    """Truncate string for readable test output.

    Args:
        s: String to truncate
        max_length: Maximum length (default: 100)

    Returns:
        Truncated string with ellipsis if needed

    Example:
        print(f"Content: {truncate_string(chunk.content)}")
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - 3] + "..."


def normalize_whitespace(s: str) -> str:
    """Normalize whitespace for robust string comparison.

    Args:
        s: String to normalize

    Returns:
        String with normalized whitespace (single spaces, trimmed)

    Example:
        assert normalize_whitespace(result) == normalize_whitespace(expected)
    """
    return " ".join(s.split())


async def poll_until_stable(
    get_value: Callable[[], T],
    stable_duration: float = 1.0,
    check_interval: float = 0.2,
    timeout: float = 10.0,
) -> T:
    """Poll until value remains stable for specified duration.

    Useful for waiting for async operations to complete (Qdrant commits, etc.)

    Args:
        get_value: Callable that returns current value
        stable_duration: How long value must stay stable (default: 1.0s)
        check_interval: Time between checks (default: 0.2s)
        timeout: Maximum total wait time (default: 10.0s)

    Returns:
        Stable value

    Raises:
        TimeoutError: If value doesn't stabilize within timeout

    Example:
        # Wait for Qdrant count to stabilize
        stable_count = await poll_until_stable(
            lambda: qdrant.count(collection_name).count
        )
    """
    start_time = asyncio.get_event_loop().time()
    end_time = start_time + timeout

    last_value = None
    stable_since = None

    while asyncio.get_event_loop().time() < end_time:
        current_value = get_value()
        if asyncio.iscoroutine(current_value):
            current_value = await current_value

        if current_value == last_value:
            if stable_since is None:
                stable_since = asyncio.get_event_loop().time()
            elif asyncio.get_event_loop().time() - stable_since >= stable_duration:
                return current_value
        else:
            stable_since = None
            last_value = current_value

        await asyncio.sleep(check_interval)

    raise TimeoutError(f"Value did not stabilize within {timeout}s")
