---
paths: tests/**/*.py
---
# Test Infrastructure Rules

**MANDATORY:** These rules prevent recurring test performance regressions. Follow them for ALL test changes.

---

## Test Marker Requirements

| Test Type | Required Markers | Purpose |
|-----------|-----------------|---------|
| **Read-only integration tests** | `@pytest.mark.preserve_collection` | Skip cleanup overhead |
| **Tests that modify Qdrant** | `@pytest.mark.manages_collection_state` | Enable lazy restoration |
| **Slow tests (>30s)** | `@pytest.mark.slow` | Excluded from default runs |
| **Tests requiring 160-page PDF** | `@pytest.mark.slow` + skipif | CI-only execution |

**ENFORCEMENT:** `--strict-markers` is enabled in pytest.ini. Unknown markers fail the build.

---

## Test Isolation Contract

```python
# CORRECT: Read-only test (uses existing data)
@pytest.mark.preserve_collection
async def test_search_returns_results(session_ingested_collection):
    results = await search_documents("revenue")
    assert len(results) > 0

# CORRECT: Test that modifies collection
@pytest.mark.manages_collection_state
async def test_ingest_new_document(session_ingested_collection):
    await ingest_pdf("new_doc.pdf", clear_existing=True)
    # Lazy restoration happens automatically BEFORE next clean-state test

# WRONG: Modifying test without marker (causes state pollution)
async def test_bad_example(session_ingested_collection):
    await ingest_pdf("doc.pdf", clear_existing=True)  # No marker!
```

---

## Performance Budget

| Test Suite | Time Budget | Action if Exceeded |
|------------|-------------|-------------------|
| Unit tests | <2 minutes | Investigate slow tests |
| Integration (--skip-ingestion) | <10 minutes | Check lazy restoration |
| Integration (fresh ingestion) | <15 minutes | Expected (includes 60s ingestion) |
| Full suite (CI) | <30 minutes | Review parallelization |

**Baseline file:** `tests/performance_baseline.json` - CI fails if budget exceeded by >25%

---

## When Adding/Modifying Tests

### BEFORE writing a new test:
1. Determine if test is read-only or modifies state
2. Choose appropriate marker (`preserve_collection` or `manages_collection_state`)
3. Add `@pytest.mark.slow` if test takes >30 seconds

### AFTER modifying tests:
1. Run: `pytest tests/integration/ --skip-ingestion -v --durations=20`
2. Verify total time is within budget (<10 minutes)
3. If time increased significantly (>20%), investigate:
   - Missing `preserve_collection` marker on read-only tests?
   - Over-aggressive restoration in fixture?
   - New test triggering unnecessary re-ingestion?

---

## Test Fixture Architecture

```
Session Fixture (session_ingested_collection)
├── Ingests PDF once (~60s)
├── Creates Qdrant snapshot for fast restoration
└── Sets baseline chunk count (_session_sample_pdf_chunk_count)

Per-Test Fixture (ensure_qdrant_test_isolation)
├── preserve_collection tests: Skip all cleanup (fastest)
├── manages_collection_state tests: Mark dirty, defer restoration (lazy)
└── Other tests: Restore BEFORE if dirty, check AFTER for unexpected changes
```

**Key Optimization:** Lazy restoration reduces O(N) restorations to O(transitions).

---

## Red Flags (Test Performance Regression)

- Test suite time increased >20% without new tests -> Check fixture restoration
- Individual test >60s without `@pytest.mark.slow` -> Add marker or optimize
- `manages_collection_state` tests running back-to-back -> Ensure lazy restoration active
- Chunk count validation failing -> Check for state pollution between tests

---

## Import Organization Rules (CRITICAL)

### pytestmark Placement (E402 Violations)

**pytestmark MUST be placed AFTER all imports, never before or between imports.**

```python
# WRONG: pytestmark before imports (violates ruff E402)
pytestmark = [pytest.mark.integration, pytest.mark.slow]

import pytest
from raglite.ingestion import ingest_pdf

# WRONG: pytestmark between imports (violates ruff E402)
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

from raglite.ingestion import ingest_pdf

# CORRECT: All imports first, then pytestmark
import pytest
from raglite.ingestion import ingest_pdf

pytestmark = [pytest.mark.integration, pytest.mark.slow]
```

**Why this matters:**
- ruff E402 rule bans module-level code before imports
- pytestmark is module-level code (assigns to module variable)
- Placing it before/between imports causes CI linting failures
- This is the #1 cause of E402 violations in test files

**Quick fix:**
1. Move ALL `import` and `from` statements to top of file
2. Place `pytestmark` after ALL imports
3. Run `ruff check --fix` to auto-fix remaining issues

---

## Mock Patching Rules (CRITICAL)

### Patch Where Used, Not Where Defined

**ALWAYS patch at the module where the function is IMPORTED and USED, not where it's defined.**

```python
# WRONG: Patches a non-existent attribute (causes silent pollution)
patch("raglite.main.extract_timeseries", ...)  # Function doesn't exist in raglite.main!

# CORRECT: Patch where the function is imported and used
patch("raglite.mcp.tools.forecast.extract_timeseries", ...)

# BEST: Use patch.object for type safety
from raglite.mcp.tools import forecast
patch.object(forecast, "extract_timeseries", new_callable=AsyncMock)
```

### Common Patch Target Mappings

| Function | Wrong Target | Correct Target |
|----------|--------------|----------------|
| `extract_historical_data_by_type` | `raglite.main.*` | `raglite.mcp.tools.forecast.extract_historical_data_by_type` |
| `extract_timeseries` | `raglite.main.*` | `raglite.mcp.tools.forecast.extract_timeseries` |
| `generate_forecast` | `raglite.main.*` | `raglite.mcp.tools.forecast.generate_forecast` |
| `get_mistral_client` | `raglite.shared.clients.*` | Where function is imported (e.g., `raglite.retrieval.query_classifier.get_mistral_client`) |

### Why This Matters

When you patch a non-existent module attribute:
1. Python's `patch` creates the attribute temporarily
2. After the test, it removes the attribute
3. **BUT** other tests may have cached module references
4. This causes **test pollution** where tests pass in isolation but fail in suite

### Test Classification Rule

**If a test mocks ALL external dependencies (database, API, etc.), it should be a UNIT test, not an integration test.**

---

## pytest-xdist Parallel Execution Rules (CRITICAL)

### Worker Isolation Requirements

**Tests using pytest-xdist (-n > 0) must ensure state isolation between workers.**

```python
# WRONG: Shared state causes race conditions
@pytest.fixture(scope="session")
def shared_counter():
    return 0  # All workers share this - DATA RACE!

# CORRECT: Worker-scoped or use xdist_group
@pytest.fixture(scope="function")
def worker_isolated_counter():
    return 0  # Each worker gets its own

# CORRECT: Use xdist_group to force single-worker execution
@pytest.mark.xdist_group(name="qdrant_session")
@pytest.fixture(scope="session")
def session_collection():
    # Only ONE worker runs this, others wait
    return create_collection()
```

### Container State Pollution Prevention

When using xdist with Docker containers:

1. **Each worker needs unique container names** (not yet implemented - use `-n 0` or `-n 1` for now)
2. **Test fixtures must detect worker ID** and adjust ports/names accordingly
3. **Session fixtures must use xdist_group** to prevent concurrent initialization

```python
# Current workaround: Use single worker or sequential
pytest tests/integration/ -n 0  # Sequential (safe but slow)
pytest tests/integration/ -n 1  # Single worker (fast but no parallelism)

# Future implementation (requires container naming changes):
@pytest.fixture
def worker_containers(worker_id):
    port = 6335 + hash(worker_id) % 100  # Unique port per worker
    return start_test_container(port)
```

### Current Best Practices

1. **Unit tests**: `-n auto` safe (no shared state)
2. **Integration tests**: `-n 1` (session fixture, single worker)
3. **E2E tests**: `-n 0` (sequential, full isolation)
4. **Avoid**: `-n 4` on integration tests (container state pollution)

```python
# This belongs in tests/unit/, NOT tests/integration/
# All dependencies are mocked, no real infrastructure needed
@pytest.mark.asyncio
async def test_cache_hit_uses_cached_model():
    with (
        patch("raglite.mcp.tools.forecast.get_cached_model_selection", ...),
        patch("raglite.mcp.tools.forecast.extract_historical_data_by_type", ...),
        patch("raglite.mcp.tools.forecast.generate_forecast", ...),
    ):
        # Test logic here
```

---

## Test Organization

- **Unit Tests** (`tests/unit/`): ~200 tests, no external dependencies
- **Integration Tests** (`tests/integration/`): ~115 tests, requires Qdrant/PostgreSQL
- **E2E Tests** (`tests/e2e/`): ~28 tests, full system validation

---

## Test Commands

```bash
# All tests (fast - excludes slow tests)
uv run pytest tests/

# Unit tests only (~200 tests, <2 min)
uv run pytest tests/unit/

# Integration tests (~115 tests, 5-10 min with 10-page PDF)
uv run pytest tests/integration/ -m "not slow"

# E2E tests (~28 tests)
uv run pytest tests/e2e/

# Ground truth accuracy validation (NFR6/NFR7)
uv run python scripts/run-accuracy-tests.py

# With coverage
uv run pytest --cov=raglite --cov-report=html
```

---

## Container Lifecycle Management (2025-12-24)

**Strategic recommendation:** Test fixtures now auto-restart stopped containers to prevent infrastructure failures.

### Auto-Restart Behavior

When integration tests start, the fixture system:
1. Checks if test containers (`raglite-postgresql-test`, `raglite-qdrant-test`) are running
2. If containers are stopped, attempts automatic restart via `docker start`
3. If PostgreSQL was restarted, initializes database schema (ORM tables)
4. Only skips tests if restart fails

### Container Status Commands

```bash
# Check container status
docker ps -a --filter "name=raglite-postgresql-test" --format "{{.Names}}\t{{.Status}}"
docker ps -a --filter "name=raglite-qdrant-test" --format "{{.Names}}\t{{.Status}}"

# Manual restart if needed
docker start raglite-postgresql-test raglite-qdrant-test

# Initialize database schema after restart
APP_ENV=test uv run python scripts/init-test-postgresql.py
```

### Fixture: `ensure_test_infrastructure`

Use for explicit infrastructure validation:

```python
@pytest.mark.usefixtures("ensure_test_infrastructure")
class TestMyIntegration:
    def test_something(self):
        ...
```

---

## Configuration Testing Rules (2025-12-24)

**Strategic recommendation:** Prevent config-test drift where tests hardcode values that configuration changes.

### Config Change Detection

A CI workflow (`config-change-detection.yml`) monitors changes to:
- `raglite/forecasting/regressor_config.py`
- `raglite/forecasting/model_selection.py`
- `raglite/external_data/orm_models.py`
- `raglite/shared/config.py`

When these files change without related test updates, the workflow posts a review reminder.

### Best Practices for Config Tests

```python
# WRONG: Hardcoded expected values
def test_ebitda_has_euribor():
    regressors = get_default_regressors("ebitda")
    assert "euribor_3m" in regressors  # Breaks when config changes!

# CORRECT: Test behavior, not implementation
def test_ebitda_has_cost_side_regressors():
    """EBITDA should have cost-side regressors (energy prices)."""
    regressors = get_default_regressors("ebitda")
    cost_side = {"ttf_gas", "diesel", "api2_coal", "eurostat_electricity"}
    assert bool(set(regressors) & cost_side), "EBITDA needs cost-side regressors"

# CORRECT: Data-driven from source of truth
@pytest.mark.parametrize("metric,expected", [
    (m, r) for m, r in METRIC_REGRESSORS.items()
])
def test_metric_returns_configured_regressors(metric, expected):
    assert set(get_default_regressors(metric)) == set(expected)
```

### When Changing Configuration

1. **Review related tests** for hardcoded expectations
2. **Update tests** to match new configuration OR use data-driven patterns
3. **Add Story reference** in test docstrings explaining why values changed

---

## Database Schema Initialization

**Critical:** Test database must have ALL tables before running integration tests.

### Schema Initialization Script

```bash
# Initialize test database (creates all tables including ORM models)
APP_ENV=test uv run python scripts/init-test-postgresql.py
```

This script now creates:
- `financial_chunks` (core RAG table)
- `financial_tables` (structured data)
- `entity_mappings` (entity resolution)
- `model_selection` (Story 7b-4 cache)
- `model_weights` (Story 6.12 ensemble)
- `external_data_sources/points` (regressors)
- `model_registry` (model metadata)

### After Container Restart

The auto-restart fixture calls `initialize_test_database_schema()` which ensures ORM tables exist. However, for manual restarts:

```bash
docker start raglite-postgresql-test
APP_ENV=test uv run python scripts/init-test-postgresql.py
```
