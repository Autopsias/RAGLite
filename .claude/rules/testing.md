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
