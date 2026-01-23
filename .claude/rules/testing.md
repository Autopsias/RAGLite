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

### CRITICAL: Fixture Definition Rule (Story 8 Strategic Fix)

**When copying tests from other files, ALWAYS copy fixture definitions too.**

Root cause from Story 8 analysis: 78 tests failed because fixture references were copied
without copying the fixture definitions from conftest.py files.

```python
# WRONG: Copying test that uses db_session without copying the fixture
def test_something(db_session):  # NameError: fixture 'db_session' not found
    ...

# CORRECT: When copying tests, also add the required fixture to conftest.py
# In tests/integration/your_module/conftest.py:
@pytest.fixture
def db_session():
    """Database session for tests."""
    engine = create_engine(TEST_DATABASE_URL)
    with Session(engine) as session:
        yield session
```

**Prevention:** Pre-commit hook `validate-pytest-fixtures` runs `pytest --collect-only`
to catch missing fixtures before commit.

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
2. **Integration tests**: `-n 4 --dist loadgroup` (xdist_group isolates embedding tests)
3. **E2E tests**: `-n 0` (sequential, full isolation)

**Integration Test Parallelization (2025-01-11):**
- Tests using embedding model have `@pytest.mark.xdist_group(name="embedding_model")`
- These tests run on a SINGLE worker (avoids 60s model load per worker)
- Other integration tests distribute across remaining workers
- Result: ~1000 tests in ~10 min (was 28 min with `-n 1`)

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

## xdist_group Marker Requirements for Heavy Resources (CRITICAL)

### Problem: Session Fixtures are Per-Worker, Not Global

pytest-xdist creates separate Python processes per worker. Session-scoped fixtures execute ONCE PER WORKER, not once globally.

**Impact with 4 workers and 60s embedding model load:**
- Expected: 60s total (one load)
- Actual: 240s total (4 loads, one per worker)

This causes test suite slowdown of 4-5x when session-scoped fixtures with heavy initialization are used without proper grouping.

### Solution: xdist_group Markers

ALL tests that use heavy shared resources (embedding model, PDF ingestion) MUST have:

```python
import pytest

pytestmark = [
    pytest.mark.xdist_group(name="embedding_model"),
    # ... other markers
]
```

This ensures all such tests run on the SAME worker, preventing redundant resource loads.

### Which Tests Need This Marker?

Add `xdist_group(name="embedding_model")` if your test:
1. Uses `get_embedding_model()` directly
2. Uses `session_ingested_collection` fixture (depends on embedding model)
3. Uses `warmup_embedding_model` fixture
4. Imports from `raglite.shared.embedding_utils` or embedding-related modules
5. Depends on any session-scoped fixture that loads the 2GB embedding model

### How It Works

When `xdist_group(name="embedding_model")` is applied:
1. All tests with that group marker run on the same worker
2. Session fixtures execute once for that group, not per worker
3. Other tests distribute across remaining workers
4. Result: 60s embedding load × 1 worker instead of × N workers

### Validation

Run before committing integration tests:
```bash
# Check which tests need xdist_group markers
python scripts/validate-xdist-markers.py

# Run tests with parallelization
pytest tests/integration/ -n 4 --dist loadgroup
```

CI will fail if embedding-dependent tests lack the xdist_group marker when running with `-n auto`.

### Common Pattern

```python
# tests/integration/retrieval/test_semantic_search.py
import pytest
from raglite.shared.embedding_utils import get_embedding_model

pytestmark = [
    pytest.mark.integration,
    pytest.mark.xdist_group(name="embedding_model"),  # Required!
]

async def test_search_with_semantic_model(session_ingested_collection):
    """Test semantic search uses embedding model."""
    model = get_embedding_model()  # Heavy load (60s)
    # Test implementation...
```

### Current Metrics (as of 2025-01-11)

| Metric | Value |
|--------|-------|
| Integration test files | 144 |
| Files with xdist_group marker | 33 (23%) |
| Embedding model load time | 60s |
| Model size | 2GB |
| Default worker count | 4 (auto mode) |
| Expected slowdown without marker | 4-5x |
| Actual test suite time | ~10 min (optimized) |

---

## isinstance Checks with pytest-xdist (CRITICAL)

**Problem:** When using pytest-xdist (`-n auto`), each worker runs in a separate process.
This causes `isinstance(obj, SomeClass)` to fail because `SomeClass` in each worker
is a different object, even if it has the same name.

### Prevention Rules

1. **NEVER use isinstance() for class identity checks in tests**
   ```python
   # WRONG - fails with xdist
   assert isinstance(result, TrendAnalysisResult)

   # CORRECT - use duck-typing
   assert result.__class__.__name__ == 'TrendAnalysisResult'
   assert hasattr(result, 'trends')
   assert hasattr(result, 'metrics_analyzed')
   ```

2. **NEVER use `in Enum` checks for enum membership**
   ```python
   # WRONG - fails with xdist
   assert trend.direction in TrendDirection

   # CORRECT - check enum value
   assert trend.direction.name in ['INCREASING', 'DECREASING', 'STABLE']
   # OR
   assert trend.direction.value in ['increasing', 'decreasing', 'stable']
   ```

3. **For dataclasses, use attribute checks**
   ```python
   # WRONG
   assert isinstance(result, ModelSelectionResult)

   # CORRECT
   assert result.__class__.__name__ == 'ModelSelectionResult'
   assert hasattr(result, 'best_model')
   assert hasattr(result, 'best_mape')
   ```

### When isinstance() IS Safe

- Checking against built-in types: `isinstance(x, str)`, `isinstance(x, dict)`
- Checking against typing module types: `isinstance(x, list)`
- Checking against classes imported from external libraries (they're stable)

---

## Fixture Scope Conflicts (P1)

### Problem

Fixtures with different scopes can cause unexpected behavior when they depend on each other.

### Rules

1. **Function-scope fixtures cannot depend on session-scope fixtures with side effects**
   ```python
   # WRONG - state leaks between tests
   @pytest.fixture(scope="session")
   def db_connection():
       conn = create_connection()
       yield conn
       conn.close()

   @pytest.fixture(scope="function")
   def user(db_connection):  # Dangerous!
       # db_connection is shared across ALL tests
       return create_user(db_connection)
   ```

2. **Use explicit scope markers for shared state**
   ```python
   @pytest.fixture(scope="session")
   @pytest.mark.xdist_group(name="database")  # Force same worker
   def db_connection():
       ...
   ```

3. **Fixture location determines inheritance**
   - `tests/conftest.py` - Available to ALL tests
   - `tests/unit/conftest.py` - Available to unit tests only
   - `tests/unit/module/conftest.py` - Available to that module only

   If a test at `tests/unit/` uses a fixture from `tests/unit/module/conftest.py`,
   pytest will NOT find it!

### Common Fixture Scope Patterns

| Fixture Scope | Use Case | xdist Behavior |
|---------------|----------|----------------|
| function | Isolated test data | Safe with `-n auto` |
| class | Shared within test class | Safe with `-n auto` |
| module | Shared within file | Safe with `-n auto` |
| session | Global (e.g., DB connection) | MUST use xdist_group |

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

---

## Epic 8 Migration Guide

**See:** `docs/sprint-artifacts/epic-8-migration-notes.md` for comprehensive migration documentation.

### Key Breaking Changes (Epic 8)

| Story | Change | Impact |
|-------|--------|--------|
| 8.1 | `historical_data` now required in `generate_ensemble_forecast` | Update all callers to pass data explicitly |
| 8.2 | `get_cached_model_selection` now sync (was async) | Remove `await` and use `Mock` not `AsyncMock` |
| 8.3 | `document_ingestion.py` split into package | Update mock targets to new module paths |
| 8.4 | `db_session` fixture consolidated | Remove duplicate fixtures from subdirectories |

### Mock Target Validation

Run before committing test changes:

```bash
# Validate all mock targets exist
python scripts/validate-mock-targets.py --verbose --fix-suggestions
```

This hook is also included in pre-commit and will block commits with stale mock targets.

---

## CI Infrastructure Enhancements (2025-01-13)

### Colima Zombie State Detection (P0)

**Problem:** 80% of CI failures caused by Colima VM in zombie state - socket exists but daemon unresponsive.

**Enhanced Detection in docker-preflight action:**
```yaml
# Dual-level health check (socket + daemon responsiveness)
if [[ -S "$COLIMA_SOCKET" ]]; then
  if timeout 5 docker info &> /dev/null; then
    echo "✅ Docker daemon responsive"
  else
    echo "🧟 ZOMBIE STATE DETECTED"
    FORCE_CLEANUP=true
  fi
fi
```

**Prevention Mechanisms:**
1. **Socket check** - Verify `~/.colima/default/docker.sock` exists
2. **Daemon responsiveness check** - `timeout 5 docker info` must succeed
3. **Automatic cleanup** - Force delete and restart on zombie detection
4. **Lima network cleanup** - Remove stale network state: `rm -rf ~/.colima/_lima/_networks`

**See:** `docs/ci-failure-runbook.md` → Section 16 for full diagnostic guide.

### pytest Configuration Enhancements (P1)

**Timeout Configuration:**
- Default 120s timeout for unit tests (CI is 3-5x slower than local)
- Timeout applies to test functions only, not fixtures
- Individual tests override with `@pytest.mark.timeout(seconds)`

**xdist Best Practices:**
- Use `__class__.__name__` instead of `isinstance()` for custom classes
- Add `@pytest.mark.xdist_group()` for tests sharing state
- Use `hasattr()` for duck-typing validation
- Avoid `in Enum` checks - use `.name` or `.value` instead

**See:** `pytest.ini` for full configuration and comments.

### External API Test Patterns (P1)

**Problem:** External API tests (ECB, Eurostat, INE, OMIE, etc.) can be flaky due to network issues, rate limiting, and API availability.

**Solution Architecture:**

External API tests use embedded sample data with mock patches, NOT VCR cassette recording:

```python
# tests/integration/external_data/ecb/conftest.py
SAMPLE_GDP_CSV = """KEY,FREQ,REF_AREA,...
MNA.Q.Y.PT...,Q,PT,N,2020-Q1,0.6
..."""

# In test file - mock the HTTP client
with patch("httpx.AsyncClient") as mock_client:
    mock_client.return_value.__aenter__.return_value.get = AsyncMock(
        return_value=mock_response
    )
```

**Required Markers (ALL external API tests):**

```python
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.external_api,  # Required - enables CI exclusion
    pytest.mark.timeout(60),   # Required - prevents hanging
]
```

**CI Exclusion:**

External API tests are excluded from fast CI via:
```yaml
MARKER_EXPR="not health_check and not atdd and not external_api"
```

**VCR Infrastructure (Optional):**

VCR configuration exists in `tests/integration/external_data/conftest.py` for recording real HTTP interactions when needed:

```bash
# Record cassettes (requires network access)
VCR_RECORD_MODE=once uv run pytest tests/integration/external_data/ -m external_api --timeout=300
```

**Sample Data Locations:**

| API | Variable | File |
|-----|----------|------|
| ECB GDP | `SAMPLE_GDP_CSV` | `tests/integration/external_data/ecb/conftest.py` |
| ECB HICP | `SAMPLE_HICP_CSV` | `tests/integration/external_data/ecb/conftest.py` |
| INE | `SAMPLE_INE_RESPONSE` | `tests/integration/external_data/conftest.py` |
| OMIE | `SAMPLE_OMIE_RESPONSE` | `tests/integration/external_data/conftest.py` |

**Verification:**

```bash
# Run external API tests (uses mocks, no network required)
APP_ENV=test uv run pytest tests/integration/external_data/ -m external_api -v --timeout=120
```

---

### Mock Coverage Validation (P0)

**Problem:** 17+ modules import `get_mistral_client` but only 5 patched in mock fixtures.

**Enforcement:**
- Pre-commit hook: `validate-mock-coverage` blocks commits with gaps
- CI lint-gate job: Validates mock coverage on every PR
- Script: `scripts/validate-mock-coverage.py` for manual checks

**Prevention Pattern:**
```python
# When adding get_mistral_client import to new module:
# 1. Add module to raglite/module/new_feature.py
from raglite.shared.clients import get_mistral_client

# 2. Update tests/fixtures/mock_clients.py
@pytest.fixture(scope="session")
def mock_mistral_api_globally():
    with ExitStack() as stack:
        # ... existing patches ...
        mock_new_feature = stack.enter_context(
            patch("raglite.module.new_feature.get_mistral_client")
        )
        mock_new_feature.return_value = mock_client_instance
```

**See:** `scripts/validate-mock-coverage.py --verbose` for coverage report.
