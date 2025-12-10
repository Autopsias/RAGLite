# Test Development Guidelines

This document provides guidelines for creating and categorizing tests in RAGLite. Follow these rules to ensure tests are properly labeled and the test suite remains performant.

## Test Categorization Philosophy

We follow industry best practices inspired by Google's small/medium/large test categories and common pytest patterns from Django, FastAPI, and other major Python projects.

**Goal**: Keep the default "fast" test suite under 5 minutes locally, while ensuring comprehensive coverage in CI.

## Test Size Categories

| Category | Duration | Characteristics | Marker |
|----------|----------|-----------------|--------|
| **Small** | < 100ms | Pure unit tests, no I/O, mocked dependencies | None (default) |
| **Medium** | 100ms - 1s | Light I/O, mocked DB/network, test fixtures | None (default) |
| **Large** | > 1s | Real I/O, actual DB, external systems, ingestion | `@pytest.mark.slow` |

**Rule of thumb**: If a test consistently takes **>1 second**, it should be marked as `@pytest.mark.slow`.

## When to Use `@pytest.mark.slow`

### Mandatory Criteria (mark as slow if ANY apply):

1. **Test duration > 1 second** (measured via `pytest --durations=0`)
   - Run `pytest path/to/test.py --durations=0` to check
   - Any test consistently >1s needs the marker

2. **Performs actual document ingestion** (PDF, Excel, etc.)
   ```python
   @pytest.mark.slow  # Actual PDF ingestion (~20-60s)
   @pytest.mark.asyncio
   async def test_ingest_document():
       await ingest_pdf("document.pdf")
   ```

3. **Uses real sleep/delay** (total delay > 1s)
   ```python
   @pytest.mark.slow  # Real delays for timeout testing
   @pytest.mark.asyncio
   async def test_timeout_handling():
       await asyncio.sleep(5)
   ```

4. **Tests retry logic with actual backoff waits**
   ```python
   @pytest.mark.slow  # Exponential backoff with real delays
   async def test_retry_with_backoff():
       # Waits for actual retry intervals (1s, 2s, 4s...)
   ```

5. **Runs subprocess scripts** that take >1s
   ```python
   @pytest.mark.slow  # Subprocess execution
   def test_run_accuracy_script():
       subprocess.run(["python", "scripts/run-accuracy-tests.py"])
   ```

6. **Hits real external systems** (APIs, databases without mocks)
   ```python
   @pytest.mark.slow
   @pytest.mark.external_api
   async def test_real_api_call():
       response = await client.get("https://api.example.com/data")
   ```

### NOT slow (keep unmarked):

- Tests with mocked I/O (even if testing I/O logic)
- Tests with `asyncio.sleep(0)` or very short delays (<100ms)
- Tests using in-memory fixtures or test doubles
- Validation/error-handling tests that fail fast

### Quick Reference Table

| Test Characteristic | Marker Required | Rationale |
|---------------------|-----------------|-----------|
| Duration > 1s | `@pytest.mark.slow` | Industry standard threshold |
| PDF/document ingestion | `@pytest.mark.slow` | Always >1s |
| Real `asyncio.sleep()` > 1s | `@pytest.mark.slow` | Actual wait time |
| Exponential backoff (real) | `@pytest.mark.slow` | Cumulative delays |
| Subprocess execution | `@pytest.mark.slow` | If >1s total |
| Real external API calls | `@pytest.mark.slow` + `@pytest.mark.external_api` | Network latency |
| Health checks | `@pytest.mark.health_check` | Run separately (daily CI) |
| Mocked everything | No marker | Fast by design |

## Other Important Markers

```python
# Integration tests (require Qdrant/PostgreSQL)
@pytest.mark.integration

# Tests that modify Qdrant collection state
@pytest.mark.manages_collection_state

# Read-only tests (skip cleanup overhead)
@pytest.mark.preserve_collection

# Health checks (run daily, excluded from regular runs)
@pytest.mark.health_check

# External API tests (may be flaky/rate-limited)
@pytest.mark.external_api
```

## Test Performance Budget

Based on Google's small/medium/large test philosophy and common Python project practices:

| Test Type | Target Time | Action if Exceeded |
|-----------|-------------|-------------------|
| Unit test (small) | < 100ms | Ideal - pure logic, no I/O |
| Unit test (medium) | < 1s | Acceptable with mocked I/O |
| Integration test | < 1s | If >1s, add `@pytest.mark.slow` |
| Any test > 1s | N/A | **MUST have `@pytest.mark.slow`** |

### Discovering Slow Tests

Run periodically to identify tests that need markers:

```bash
# Show 20 slowest tests
pytest tests/ --durations=20

# Show ALL test durations (for thorough review)
pytest tests/ --durations=0

# Find tests >1s that might need @pytest.mark.slow
pytest tests/ --durations=0 2>&1 | grep -E "^[0-9]+\.[0-9]+s" | awk '$1 > 1.0'
```

## Module-Level Markers

For files where **ALL tests** are slow, use `pytestmark`:

```python
# All tests in this file involve PDF ingestion
pytestmark = [
    pytest.mark.integration,
    pytest.mark.manages_collection_state,
    pytest.mark.slow,  # All tests are slow
]
```

## Examples

### Correct: Slow test properly marked

```python
@pytest.mark.slow  # Takes ~25s for actual PDF ingestion
@pytest.mark.integration
@pytest.mark.manages_collection_state
@pytest.mark.asyncio
async def test_parallel_ingestion_three_documents():
    """Test parallel ingestion with 3 documents."""
    result = await ingest_documents_parallel(file_paths)
    assert result.successful == 3
```

### Correct: Fast test (no slow marker needed)

```python
@pytest.mark.asyncio
async def test_validation_error_on_empty_list():
    """Test error handling for empty file list."""
    with pytest.raises(ValueError, match="file_paths cannot be empty"):
        await ingest_documents_parallel([])
```

### Incorrect: Missing slow marker

```python
# BAD: This test takes 15s but has no slow marker!
@pytest.mark.asyncio
async def test_workflow_timeout_handling():
    await asyncio.sleep(20)  # Exceeds 15s timeout
```

### Correct: Fixed version

```python
# GOOD: Slow marker added
@pytest.mark.slow  # Tests actual timeout with 15s wait
@pytest.mark.asyncio
async def test_workflow_timeout_handling():
    await asyncio.sleep(20)  # Exceeds 15s timeout
```

## Validation

Before committing new tests, verify:

1. **Run with durations**: `pytest tests/path/to/new_test.py --durations=0`
2. **Check if >5s**: Any test taking >5s needs `@pytest.mark.slow`
3. **Verify exclusion**: `pytest --collect-only -m "not slow"` should exclude your slow tests

## CI vs Local Runs

| Environment | Command | Slow Tests |
|-------------|---------|------------|
| VS Code Test Explorer | Default settings | **Excluded** |
| Local CLI (fast) | `pytest tests/` | **Excluded** |
| Local CLI (full) | `pytest tests/ -m ""` | Included |
| CI Pipeline | `pytest tests/ -m ""` | Included |

The default `pytest.ini` has `-m "not slow and not health_check"`, so slow tests are excluded unless explicitly requested.
