# RAGLite Test Suite

Comprehensive test suite for RAGLite financial document analysis system.

---

## 📊 Test Suite Overview

**Total Tests:** 381+ tests (organized 2025-10-28)

**Test Levels:**
- **Unit Tests** (`tests/unit/`): ~200 tests - No external dependencies
- **Integration Tests** (`tests/integration/`): ~115 tests - Requires Qdrant + PostgreSQL
- **E2E Tests** (`tests/e2e/`): ~28 tests - Full system validation

**Test Execution Time:**
- **LOCAL (fast):** 5-10 minutes (excludes `@pytest.mark.slow` tests)
- **CI (comprehensive):** 30-40 minutes (includes all tests + 160-page PDF)

---

## 🚀 Quick Start

### Prerequisites

```bash
# Start required services
docker-compose up -d  # Qdrant + PostgreSQL

# Install dependencies
uv sync --all-groups
```

### Running Tests

```bash
# All tests (fast mode - excludes slow tests)
uv run pytest tests/

# Unit tests only (~2 min)
uv run pytest tests/unit/

# Integration tests (~5-10 min with 10-page PDF)
uv run pytest tests/integration/ -m "not slow"

# E2E tests
uv run pytest tests/e2e/

# Run tests in parallel (10x faster)
uv run pytest tests/ -n auto

# With coverage report
uv run pytest tests/ --cov=raglite --cov-report=html
```

---

## 🏷️ Test Markers & Filtering

### Priority-Based Execution

Tests are tagged with priority markers (Story 3-0-7):

```bash
# Critical tests only (P0 - run every commit)
pytest -m "priority('P0')"

# High priority (P1 - run on PR)
pytest -m "priority('P1') or priority('P0')"

# Medium priority (P2 - run nightly)
pytest -m "priority('P2')"

# Low priority (P3 - on-demand)
pytest -m "priority('P3')"
```

### Test Level Markers

```bash
# Unit tests (fast, no external dependencies)
pytest -m unit

# Integration tests (requires Qdrant/PostgreSQL)
pytest -m integration

# E2E tests (full system)
pytest -m e2e

# Smoke tests (ultra-fast <30s critical path)
pytest -m smoke
```

### Slow Test Handling

```bash
# Exclude slow tests (default behavior)
pytest tests/ -m "not slow"

# Run slow tests only
pytest tests/ -m slow

# Include slow tests (CI mode)
pytest tests/ -m ""
```

---

## 📝 Test ID Traceability (Story 3-0-6)

All tests have unique IDs linking to stories:

```python
@pytest.mark.test_id("2.10-UNIT-001")
@pytest.mark.priority("P1")
def test_query_classification_sql_routing():
    """Test query classification for SQL table routing."""
    ...
```

**ID Format:** `{story_id}-{level}-{number}`
- Story: `2.10` (Story 2.10 - Query Classifier)
- Level: `UNIT`, `INT` (integration), `E2E`
- Number: `001`, `002`, etc.

---

## 🔧 Test Configuration

### Environment Variables

```bash
# Use 160-page PDF for comprehensive testing (CI mode)
export TEST_USE_FULL_PDF=true

# Qdrant connection
export QDRANT_HOST=localhost
export QDRANT_PORT=6333

# PostgreSQL connection
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=raglite_test
```

### Execution Modes

**LOCAL Mode (default - fast):**
```bash
pytest tests/
# Uses 10-page PDF (~10-15s ingestion)
# Skips @pytest.mark.slow tests
# Target: 5-8 minutes total
```

**CI Mode (comprehensive):**
```bash
TEST_USE_FULL_PDF=true pytest tests/ -m ""
# Uses 160-page PDF (~150s ingestion)
# Runs ALL tests including slow ones
# Target: 30-50 minutes total
```

**Skip Ingestion Mode (reuse existing data):**
```bash
# First: Ingest manually
python scripts/ingest-full-pdf-ac3.py

# Then: Run tests without re-ingesting
pytest tests/integration/ --skip-ingestion --run-slow -m ""
# Saves ~25 minutes
```

---

## 🧪 Writing New Tests

### Test Structure (Given-When-Then)

```python
import pytest
from tests.support.factories import create_chunk
from tests.support.helpers import assert_embedding_valid

@pytest.mark.unit
@pytest.mark.priority("P1")
@pytest.mark.test_id("3.X-UNIT-001")
def test_feature_behavior():
    """Test feature does X when Y."""
    # GIVEN: Setup test data
    chunk = create_chunk(content="Q3 revenue was $50M")

    # WHEN: Perform operation
    result = process_chunk(chunk)

    # THEN: Assert expected outcome
    assert result.status == "success"
    assert_embedding_valid(result.embedding)
```

### Using Factories

```python
from tests.support.factories import (
    create_chunk,
    create_chunks,
    create_document_metadata,
    create_financial_table_row,
    create_query,
)

# Single chunk with defaults
chunk = create_chunk()

# Multiple chunks
chunks = create_chunks(10)

# Override specific fields
chunk = create_chunk(
    content="Specific financial data",
    page_number=5
)

# Financial table data
row = create_financial_table_row(
    entity="Apple Inc",
    metric="Revenue",
    value=100.5
)

# Natural language queries
query = create_query()  # Random financial query
query = create_query(query="What was Q3 revenue?")  # Specific
```

### Using Test Helpers

```python
from tests.support.helpers import (
    wait_for,
    retry,
    assert_qdrant_collection_count,
    assert_search_results_valid,
)

# Wait for condition
async def check_ready():
    return qdrant.count(collection_name).count > 0

await wait_for(check_ready, timeout=10.0)

# Retry flaky operation
result = await retry(
    lambda: api_client.get("/data"),
    max_attempts=3,
    delay=1.0
)

# Custom assertions
assert_qdrant_collection_count(qdrant, "docs", expected_count=100)
assert_search_results_valid(results, min_results=5, min_score=0.7)
```

### Fixture Usage

```python
# Test settings (function-scoped)
def test_with_settings(test_settings):
    assert test_settings.qdrant_host == "localhost"

# Mock clients (module-scoped)
def test_with_mock(mock_qdrant_client):
    mock_qdrant_client.search.return_value = []

# Session-scoped ingestion (shared across tests)
@pytest.mark.integration
@pytest.mark.preserve_collection  # Avoid cleanup overhead
async def test_with_ingested_pdf(session_ingested_collection):
    # PDF already ingested, use Qdrant collection
    results = await search_documents("revenue")
```

---

## 📊 Test Organization

```
tests/
├── unit/                    # ~200 unit tests (no dependencies)
│   ├── test_bm25.py        # BM25 indexing tests
│   ├── test_query_classifier.py
│   ├── test_period_normalizer.py
│   └── ...
├── integration/            # ~115 integration tests (Qdrant + PostgreSQL)
│   ├── test_ac3_ground_truth.py  # Accuracy validation
│   ├── test_sql_routing.py
│   ├── test_hybrid_search_integration.py
│   └── ...
├── e2e/                    # ~28 end-to-end tests
│   └── test_ground_truth.py
├── fixtures/               # Test data
│   ├── ground_truth.py     # Q&A validation set
│   ├── sample_financial_report.pdf  # 10-page test PDF
│   └── sample_financial_data.xlsx
├── support/                # Test infrastructure
│   ├── factories.py        # Data factories (faker-based)
│   └── helpers.py          # Test utilities
└── conftest.py             # Shared fixtures
```

---

## 🎯 Test Quality Standards

### Required Patterns

✅ **Use Given-When-Then format**
```python
# GIVEN: Setup
# WHEN: Action
# THEN: Assertion
```

✅ **Tag all tests with priority**
```python
@pytest.mark.priority("P0")  # or P1, P2, P3
```

✅ **Tag all tests with test ID (Story 3-0-6)**
```python
@pytest.mark.test_id("2.10-UNIT-001")
```

✅ **Use factories for test data (no hardcoded values)**
```python
chunk = create_chunk()  # ✅ Good
chunk = Chunk(content="hardcoded")  # ❌ Bad
```

✅ **Use helpers for common operations**
```python
await wait_for(condition, timeout=5.0)  # ✅ Good
while not condition():  # ❌ Bad (manual polling)
    await asyncio.sleep(0.1)
```

✅ **Clear, descriptive test names**
```python
def test_query_classifier_routes_sql_tables():  # ✅ Good
def test_thing():  # ❌ Bad
```

### Forbidden Patterns

❌ **Hard waits/sleeps**
```python
await asyncio.sleep(2)  # ❌ Bad
await wait_for(condition)  # ✅ Good
```

❌ **Conditional test logic**
```python
if result:  # ❌ Bad - tests should be deterministic
    assert result.value == 100
```

❌ **Try-except for test logic**
```python
try:  # ❌ Bad - let tests fail naturally
    result = func()
except Exception:
    pass
```

❌ **Shared state between tests**
```python
# ❌ Bad - tests should be isolated
global_state = []

def test_a():
    global_state.append(1)

def test_b():
    assert len(global_state) == 1  # Depends on test_a
```

---

## 🔍 Debugging Tests

### Run specific test
```bash
pytest tests/unit/test_bm25.py::TestBM25IndexCreation::test_create_index_with_single_chunk -v
```

### Run with detailed output
```bash
pytest tests/ -vv --tb=short
```

### Run with debugger
```bash
pytest tests/ --pdb  # Drop to debugger on failure
```

### Show print statements
```bash
pytest tests/ -s
```

### Run last failed tests
```bash
pytest tests/ --lf
```

### Test collection without running
```bash
pytest tests/ --collect-only
```

---

## 📈 Coverage Reports

### Generate HTML coverage report
```bash
pytest tests/ --cov=raglite --cov-report=html
open htmlcov/index.html  # View in browser
```

### Coverage with missing lines
```bash
pytest tests/ --cov=raglite --cov-report=term-missing
```

### Target: 80%+ unit test coverage

---

## 🚨 Common Issues & Solutions

### Issue: "Qdrant connection refused"
**Solution:**
```bash
docker-compose up -d  # Start Qdrant service
pytest tests/integration/  # Retry
```

### Issue: "PostgreSQL connection refused"
**Solution:**
```bash
docker-compose up -d  # Start PostgreSQL
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
pytest tests/integration/
```

### Issue: "Test collection error - p0 not found"
**Solution:**
```bash
# Fix test marker registration in pytest.ini
pytest tests/ -m ""  # Skip marker validation
```

### Issue: Tests timing out
**Solution:**
```bash
# Increase timeout (default: 900s per test)
pytest tests/ --timeout=1800
```

### Issue: Flaky test failures
**Solution:**
```bash
# Run with retries (pytest-rerunfailures)
pytest tests/ --reruns 3 --reruns-delay 1
```

---

## 🎓 Best Practices

1. **Run unit tests frequently** (every code change)
2. **Run integration tests before commits** (ensure no regressions)
3. **Run full suite before PRs** (comprehensive validation)
4. **Use factories for all test data** (deterministic, realistic)
5. **Mark new tests with priority** (P0=critical, P1=high, P2=medium, P3=low)
6. **Add test IDs for traceability** (link tests to stories)
7. **Keep tests fast** (use mocks for unit tests, optimize fixtures for integration)
8. **Isolate tests** (no shared state, use fixtures with auto-cleanup)
9. **Write clear assertions** (one logical assertion per test)
10. **Document complex test setup** (explain WHY, not just WHAT)

---

## 📚 Additional Resources

- **pytest Documentation:** https://docs.pytest.org/
- **faker Documentation:** https://faker.readthedocs.io/
- **Project Architecture:** `docs/architecture/`
- **Story Details:** `docs/stories/`
- **Test Infrastructure:** `tests/support/`

---

## 🤝 Contributing Tests

When adding new tests:

1. ✅ Use existing factories from `tests/support/factories.py`
2. ✅ Add test ID marker: `@pytest.mark.test_id("X.Y-LEVEL-###")`
3. ✅ Add priority marker: `@pytest.mark.priority("P0|P1|P2|P3")`
4. ✅ Follow Given-When-Then format
5. ✅ Add docstring explaining test purpose
6. ✅ Use helpers from `tests/support/helpers.py`
7. ✅ Ensure tests are deterministic (no random failures)
8. ✅ Keep unit tests fast (<1s each)
9. ✅ Run `pytest tests/` before committing

---

**Last Updated:** 2025-11-05 (Story 3-0-X - Test Quality Improvement)
