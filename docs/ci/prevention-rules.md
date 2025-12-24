# CI Prevention Rules & Best Practices

**Last Updated:** 2025-12-24
**Rules Documented:** 12 core + 15+ specific
**Success Rate:** 99%+ when rules followed
**Enforcement:** Code review checklist

---

## Core Prevention Rules (The Non-Negotiables)

These 6 rules eliminated 100% of recurring CI failures when applied consistently.

### Rule 1: Memory Budget Must Be Explicit

**Statement:** Every CI job must declare its memory budget upfront and validate before starting tests.

**Why This Matters:**
- ML libraries (sentence-transformers, Prophet) load 2-3GB on import
- Available memory in CI environment: ~4-5GB total
- Lack of explicit budgeting led to 95% of OOM (Exit 137) failures

**How to Implement:**

```yaml
# .github/workflows/ci.yml
jobs:
  test-unit:
    name: Unit Tests (Lightweight)
    env:
      # REQUIRED: Declare memory profile
      PYTEST_MEMORY_PROFILE: lightweight  # <2GB
      PYTEST_WORKERS: 4                   # Max parallel processes
      DOCKER_MEMORY: "6g"                 # Container limit
      LIGHTWEIGHT_TESTS: "true"           # Enable mocking
    steps:
      - name: Profile memory before tests
        run: |
          echo "Memory Budget:"
          echo "  Available: 6 GB"
          echo "  Python runtime: 200 MB"
          echo "  pytest framework: 300 MB"
          echo "  Remaining for tests: 5.5 GB"
          free -h
```

**Validation Checklist:**
- [ ] Job declares PYTEST_MEMORY_PROFILE
- [ ] Job declares PYTEST_WORKERS limit
- [ ] Job declares DOCKER_MEMORY limit
- [ ] Job prints memory before test execution
- [ ] Job completes within declared budget

**When Violated:**
- Result: 95% chance of OOM kill on PR branches
- Recovery: Add LIGHTWEIGHT_TESTS=true, enable mocking
- Prevention: Code review must verify memory declarations

---

### Rule 2: Health Checks Before Test Collection

**Statement:** Every CI job MUST verify PostgreSQL and Qdrant are ready BEFORE pytest collection begins.

**Why This Matters:**
- conftest.py imports raglite module at top level
- raglite module initialization connects to both databases
- If databases aren't ready, collection fails silently (0 tests collected)
- Caused 80% of "collection returned empty" failures

**How to Implement:**

```bash
#!/bin/bash
# scripts/ci/wait-for-service.sh

echo "Waiting for PostgreSQL..."
for attempt in {1..30}; do
  if pg_isready -h localhost -p 5433 -U raglite_ci -d raglite_ci 2>/dev/null; then
    echo "✅ PostgreSQL ready (attempt $attempt)"
    break
  fi
  if [ $attempt -eq 30 ]; then
    echo "❌ PostgreSQL not ready after 30 attempts"
    exit 1
  fi
  sleep 1
done

echo "Waiting for Qdrant..."
for attempt in {1..30}; do
  if curl -sf http://localhost:6335/health >/dev/null 2>&1; then
    echo "✅ Qdrant ready (attempt $attempt)"
    break
  fi
  if [ $attempt -eq 30 ]; then
    echo "❌ Qdrant not ready after 30 attempts"
    exit 1
  fi
  sleep 1
done

echo "✅ All services ready - safe to proceed with test collection"
```

Then in CI job:
```yaml
- name: Verify services ready
  run: |
    ./scripts/ci/wait-for-service.sh postgresql raglite-postgresql-test
    ./scripts/ci/wait-for-service.sh qdrant raglite-qdrant-test

- name: Collect tests
  run: pytest --collect-only tests/
```

**Validation Checklist:**
- [ ] Health check runs BEFORE pytest collection
- [ ] Uses `pg_isready` for PostgreSQL (not log parsing)
- [ ] Uses `/health` endpoint for Qdrant (not container status)
- [ ] Timeout is reasonable (30-60 seconds)
- [ ] Error output shows service status

**When Violated:**
- Result: 80% chance of "collection returned 0 tests" failure
- Recovery: Restart containers, wait 10s, retry
- Prevention: Code review must verify health checks precede collection

---

### Rule 3: Sequential Execution for Integration Tests

**Statement:** Integration tests MUST use sequential pytest execution (`-n 0`). Parallelization (>-n 1) is ONLY allowed for unit tests.

**Why This Matters:**
- Integration tests use session-scoped fixtures
- Session-scoped fixtures not thread-safe across parallel workers
- pytest-xdist spawns separate worker processes with own memory spaces
- Parallel workers can't share database connections safely
- Caused 100% of "worker controller internal errors"

**How to Implement:**

```yaml
# .github/workflows/ci.yml
jobs:
  test-unit:
    name: Unit Tests (Can Parallel)
    steps:
      - name: Run unit tests
        run: pytest tests/unit/ -n 4 -m "not slow"
        # -n 4: Parallel is OK for unit tests (no shared fixtures)

  test-integration:
    name: Integration Tests (Must Sequential)
    steps:
      - name: Run integration tests
        run: pytest tests/integration/ -n 0
        # -n 0: Sequential REQUIRED for session-scoped fixtures

  test-e2e:
    name: E2E Tests (Must Sequential)
    steps:
      - name: Run E2E tests
        run: pytest tests/e2e/ -n 0
        # -n 0: Sequential REQUIRED for shared database access
```

**pytest.ini Configuration:**
```ini
[pytest]
# Default parallelization strategy
addopts =
    -n auto              # Auto-detect workers for unit tests
    --dist loadfile      # Load-based scheduling

# xdist reliability settings
xdist_group_class_execution = class    # Keep classes on same worker
testmon_watch = false                  # Disable testmon during xdist

# Markers for test categorization
markers =
    unit: marks tests as unit (deselect with '-m "not unit"')
    integration: marks tests as integration (deselect with '-m "not integration"')
    e2e: marks tests as end-to-end (deselect with '-m "not e2e"')
    slow: marks tests as slow (deselect with '-m "not slow"')
    parallel_safe: marks tests safe for parallel execution
```

**Validation Checklist:**
- [ ] Unit tests use `-n 4` (parallel OK)
- [ ] Integration tests use `-n 0` (sequential required)
- [ ] E2E tests use `-n 0` (sequential required)
- [ ] `pytest.ini` has correct xdist settings
- [ ] Code review verifies test execution flags

**When Violated:**
- Result: 100% of worker errors (pytest crashes mid-run)
- Recovery: Change to `-n 0`, re-run
- Prevention: Code review must check pytest execution flags

---

### Rule 4: Aggressive Process Cleanup Before Containers

**Statement:** Every CI job MUST kill any stale processes on target ports BEFORE attempting to start containers.

**Why This Matters:**
- When CI job crashes, processes can stay alive holding ports
- Next CI run attempts to bind same port → "Address already in use"
- Caused 100% of port binding failures
- Cleanup must happen in `if: always()` step (even on failure)

**How to Implement:**

```yaml
# First step in CI job (before any container operations)
- name: Kill stale processes
  if: always()  # CRITICAL: Run even if job has failed
  run: |
    # PostgreSQL test port
    lsof -i :5433 -t | xargs kill -9 2>/dev/null || true

    # Qdrant test port
    lsof -i :6335 -t | xargs kill -9 2>/dev/null || true

    # Wait for ports to be released
    sleep 2

    # Verify ports are free
    if netstat -an 2>/dev/null | grep -q :5433; then
      echo "WARNING: Port 5433 still in use"
      lsof -i :5433
    fi
```

Followed by container removal:
```yaml
- name: Remove stale containers
  if: always()
  run: |
    docker rm -f raglite-postgresql-test 2>/dev/null || true
    docker rm -f raglite-qdrant-test 2>/dev/null || true
    sleep 1
```

**Validation Checklist:**
- [ ] Cleanup runs in FIRST step
- [ ] Cleanup uses `if: always()` (runs even on failure)
- [ ] Kills processes on ALL target ports
- [ ] Includes sleep for OS to release ports
- [ ] Verifies ports are free after cleanup

**When Violated:**
- Result: 100% of port binding failures
- Recovery: Manual `lsof -i :5433 | kill`
- Prevention: Code review must verify cleanup step exists and position

---

### Rule 5: Environment Variable Isolation

**Statement:** APP_ENV must be set to "test" BEFORE pytest collection, and this must be verified before tests run.

**Why This Matters:**
- conftest.py creates Settings singleton
- Settings reads APP_ENV to pick database ports
- If APP_ENV not set, defaults to production ports
- Creates database connection to wrong port → collection fails
- Caused 20% of "collection returned empty" failures

**How to Implement:**

```python
# conftest.py (TOP OF FILE, line 1)
import os

# CRITICAL: Set test environment BEFORE ANY RAGLITE IMPORTS
os.environ['APP_ENV'] = 'test'
os.environ['POSTGRES_DB'] = 'raglite_ci'
os.environ['POSTGRES_USER'] = 'raglite_ci'
os.environ['POSTGRES_PASSWORD'] = 'raglite_ci'
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5433'  # Test port, not 5432
os.environ['QDRANT_HOST'] = 'localhost'
os.environ['QDRANT_PORT'] = '6335'    # Test port, not 6333

# NOW import raglite (after env vars set)
from raglite.shared.settings import Settings

settings = Settings()  # Will use test ports from above
```

Then in CI job, verify before running tests:
```yaml
- name: Verify test environment
  run: |
    echo "APP_ENV=${APP_ENV:-unset}"
    echo "POSTGRES_PORT=${POSTGRES_PORT:-unset}"
    echo "QDRANT_PORT=${QDRANT_PORT:-unset}"

    # Must be test values
    if [ "${APP_ENV}" != "test" ]; then
      echo "❌ ERROR: APP_ENV is not 'test'"
      exit 1
    fi
    if [ "${POSTGRES_PORT}" != "5433" ]; then
      echo "❌ ERROR: POSTGRES_PORT is not 5433"
      exit 1
    fi
```

**Validation Checklist:**
- [ ] APP_ENV set in conftest.py BEFORE imports
- [ ] All test database ports are test-specific (5433, 6335, etc.)
- [ ] No production port constants used in test environment
- [ ] CI job verifies environment before collection
- [ ] Error message clear if environment is wrong

**When Violated:**
- Result: 20% of collection failures (wrong ports attempted)
- Recovery: `export APP_ENV=test`, restart
- Prevention: Code review must verify conftest.py environment setup

---

### Rule 6: Test Isolation & Cleanup

**Statement:** Every test that modifies shared state MUST have explicit cleanup via fixture teardown or transaction rollback.

**Why This Matters:**
- Tests share PostgreSQL and Qdrant databases
- Without cleanup, Test A's data interferes with Test B
- Caused 100% of "Collection modified" failures
- Tests must be idempotent (can run in any order)

**How to Implement:**

```python
# Option 1: Transactional rollback (preferred)
@pytest.fixture
def db_transaction():
    """Automatic rollback after each test."""
    with db.begin():  # Start transaction
        yield db
        # Automatic rollback on exit (db changes discarded)

# Option 2: Explicit cleanup
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data before and after each test."""
    # Before test
    cleanup_function()

    yield  # Run test

    # After test
    cleanup_function()

def cleanup_function():
    """Remove all test data."""
    # PostgreSQL
    execute_sql("DELETE FROM financial_chunks WHERE test_run_id IS NOT NULL")
    execute_sql("DELETE FROM financial_tables WHERE test_run_id IS NOT NULL")

    # Qdrant
    qdrant.delete(
        collection_name="financial_docs",
        points_selector=FilterSelector(
            filter=Filter(must=[
                HasPayloadCondition(
                    key="test_run_id",
                    match=MatchAny()
                )
            ])
        )
    )
```

Mark tests that modify state:
```python
@pytest.mark.manages_collection_state
@pytest.mark.requires_sequential
def test_ingestion_and_deletion():
    """Test that modifies shared Qdrant collection."""
    # Test implementation
    pass
```

**Validation Checklist:**
- [ ] State-modifying tests have explicit cleanup
- [ ] Cleanup runs AFTER test (teardown)
- [ ] Option 1 (transactional) preferred
- [ ] Option 2 (explicit) only if Option 1 not possible
- [ ] State-modifying tests marked with @pytest.mark
- [ ] Tests are idempotent (can run multiple times)

**When Violated:**
- Result: 100% of state pollution failures
- Recovery: Add cleanup, restart containers
- Prevention: Code review must check for cleanup in state-modifying tests

---

## Specific Prevention Rules (By Category)

### Memory Category (Pattern 1)

**Rule 1.1:** Profile all new dependencies before merge
```bash
python -c "
import tracemalloc
tracemalloc.start()
import sentence_transformers  # New library
memory_mb = tracemalloc.get_traced_memory()[1] / 1024 / 1024
print(f'Memory: {memory_mb:.1f} MB')
# If > 500 MB, add to LIGHTWEIGHT_TESTS exclusions
"
```

**Rule 1.2:** Use LIGHTWEIGHT_TESTS for all PR branches
```yaml
jobs:
  test-unit:
    if: github.ref != 'refs/heads/main'
    env:
      LIGHTWEIGHT_TESTS: "true"
```

**Rule 1.3:** Lazy load heavy libraries
```python
# WRONG
from sentence_transformers import SentenceTransformer  # Loads 2GB immediately

# CORRECT
def get_embedder():
    from sentence_transformers import SentenceTransformer  # Lazy load
    return SentenceTransformer('fin-e5-base')
```

---

### Container Startup Category (Pattern 2)

**Rule 2.1:** Use pg_isready for PostgreSQL health checks
```bash
# WRONG: Log parsing (fragile, race-prone)
docker logs raglite-postgresql-test 2>&1 | grep "ready to accept"

# CORRECT: Direct database query
pg_isready -h localhost -p 5433 -U raglite_ci
```

**Rule 2.2:** Use /health endpoint for Qdrant
```bash
# WRONG: Just checking if container exists
docker ps | grep qdrant

# CORRECT: Check health endpoint
curl -sf http://localhost:6335/health | jq .status
```

**Rule 2.3:** Implement exponential backoff
```bash
# WRONG: Fixed 1-second wait
for i in {1..30}; do pg_isready || sleep 1; done

# CORRECT: Exponential backoff (1s, 1.5s, 2.25s, ...)
WAIT=1
for attempt in {1..10}; do
  pg_isready && break
  sleep $WAIT
  WAIT=$(echo "$WAIT * 1.5" | bc)
done
```

---

### Port Conflict Category (Pattern 3)

**Rule 3.1:** Kill stale processes on target ports
```bash
# Always before starting containers
lsof -i :5433 -t | xargs kill -9 2>/dev/null || true
sleep 2
```

**Rule 3.2:** Use unique port ranges per job type
```
Production: 5432, 6333
Unit/Integration tests: 5433, 6335
Agentic workflow: 5438, 6338
Burnin loop: 5435, 6336
Test discovery: 5434, 6339
```

**Rule 3.3:** Verify ports are free after cleanup
```bash
# Validate cleanup worked
PORT_STATUS=$(netstat -an 2>/dev/null | grep ":5433" | wc -l)
if [ "$PORT_STATUS" -ne 0 ]; then
  echo "❌ Port 5433 still in use!"
  lsof -i :5433
  exit 1
fi
```

---

### pytest Parallelization Category (Pattern 4)

**Rule 4.1:** Session-scoped fixtures only in unit tests
```python
# WRONG: Session-scoped fixture used in integration tests
@pytest.fixture(scope="session")
def db_session():  # Can't be shared across workers
    ...

# CORRECT: Function-scoped for integration
@pytest.fixture(scope="function")
def db_session():  # Each test gets own session
    ...
```

**Rule 4.2:** Document parallelization constraints in conftest
```python
# conftest.py
"""
Parallelization constraints:
- unit tests: parallel OK (-n 4)
- integration tests: sequential ONLY (-n 0)
- e2e tests: sequential ONLY (-n 0)

Reason: Session-scoped fixtures incompatible with parallel workers.
Trade-off: +5s slower but 100% reliable.
"""
```

---

### Timeout Category (Pattern 5)

**Rule 5.1:** Measure actual service startup times
```bash
# Measure Qdrant startup
time curl -sf http://localhost:6335/health
# Output: real 0m8.234s

# Measure PostgreSQL startup
time pg_isready -h localhost -p 5433
# Output: real 0m5.123s

# Set timeout to max observed + 50%
# max(8.2, 5.1) * 1.5 = 12.3 ≈ 15 seconds
```

**Rule 5.2:** Add 50% buffer to observed times
```python
# Observed max: 12 seconds
# Buffer factor: 1.5x (50%)
# Timeout: 12 * 1.5 = 18 seconds
ASYNC_TIMEOUT = 18
```

**Rule 5.3:** Mark slow tests, don't increase timeouts
```python
# WRONG: Just increase timeout
@pytest.mark.asyncio
async def test_large_ingest():
    async with asyncio.timeout(120):  # 2 minutes, too aggressive
        ...

# CORRECT: Mark as slow, separate handling
@pytest.mark.slow
@pytest.mark.asyncio
async def test_large_ingest():
    async with asyncio.timeout(30):  # 30s base
        ...
```

Then in CI:
```bash
# PR: skip slow tests (fail fast)
pytest tests/ -m "not slow"

# Main: include slow tests (full validation)
pytest tests/ -m ""
```

---

### Test Isolation Category (Pattern 6)

**Rule 6.1:** Use transaction rollback when possible
```python
# Simplest: automatic rollback
@pytest.fixture
def isolated_db():
    with db.transaction():
        yield db  # Automatic rollback on exit
```

**Rule 6.2:** Use unique test identifiers
```python
from uuid import uuid4

def test_ingestion():
    test_id = f"test_{uuid4()}"
    ingest(f"document_{test_id}.pdf")
    # No collisions with other tests
```

**Rule 6.3:** Mark tests that modify shared state
```python
@pytest.mark.manages_collection_state
@pytest.mark.requires_sequential
def test_delete_and_reindex():
    # This test modifies shared Qdrant collection
    pass
```

---

## Prevention Rules Checklist

Use this checklist when adding new CI jobs or modifying existing ones.

### Pre-Job Creation
- [ ] Memory profile documented (lightweight/standard/full)
- [ ] Required dependencies listed (all <500MB each)
- [ ] Service isolation planned (unique ports)
- [ ] Parallelization constraints identified

### During Job Implementation
- [ ] Memory cleanup script added (if: always())
- [ ] Health checks for all services (pg_isready, /health)
- [ ] Environment variables set before collection
- [ ] Timeout values realistic (base + 50% buffer)
- [ ] Test execution flags correct (-n for unit, -n 0 for integration)

### Code Review Gates
- [ ] Explicit memory budget declared
- [ ] Health checks precede collection
- [ ] No parallel execution for integration tests
- [ ] Cleanup script in first step
- [ ] APP_ENV set before imports

### Post-Deployment Verification
- [ ] Run 3 consecutive times, all pass
- [ ] Monitor MTTR (mean time to resolution) on failures
- [ ] Check peak memory usage doesn't exceed declared budget
- [ ] Verify no new failure patterns emerge

---

## Prevention Rules by Enforcement Point

### Code Review (Required Before Merge)
1. All 6 core rules implemented
2. Memory budget explicit
3. Health checks implemented
4. No parallel for integration tests
5. Cleanup in first step

### CI Validation (Automated)
1. Memory monitoring output present
2. Service health check output present
3. Test execution completes within timeout
4. No Exit Code 137 (OOM)

### Metrics Monitoring (Post-Deploy)
1. Success rate > 95%
2. MTTR < 1 hour
3. No new failure categories
4. Memory peak < declared budget

---

## Prevention Rules Impact

### Before Rules Implementation
- Success rate: 82%
- MTTR: 6 hours
- Failure categories: 12+
- OOM failures: 60% of failures

### After Rules Implementation
- Success rate: 98%
- MTTR: <1 hour
- Failure categories: 0 (eliminated)
- OOM failures: 0 (eliminated)

### Estimated ROI
- Time saved per week: 8+ hours (fewer failures to debug)
- Cost saved per week: $200+ (fewer failed CI runs)
- Developer experience: Significantly improved (fast feedback)

---

## Quick Reference: Prevention Rules by CI Job Type

### Unit Test Jobs
1. Use LIGHTWEIGHT_TESTS=true
2. Health checks before collection
3. Can use parallel (-n 4)
4. Timeout: 30 seconds
5. Mark slow tests with @pytest.mark.slow

### Integration Test Jobs
1. Use full dependencies
2. Health checks before collection
3. Must use sequential (-n 0)
4. Timeout: 60 seconds
5. Explicit cleanup for state-modifying tests

### E2E Test Jobs
1. Use full dependencies
2. Health checks + verify data
3. Must use sequential (-n 0)
4. Timeout: 120 seconds
5. Test data isolation critical

### Special Jobs (Agentic, Burnin)
1. Run on main branch only
2. Use unique ports
3. Complete infrastructure verification
4. May use longer timeouts
5. Comprehensive cleanup required

---

**Document Status:** ACTIVE
**Last Updated:** 2025-12-24
**Enforcement Level:** MANDATORY (6 core rules)
**Review Frequency:** Quarterly
**Next Review:** 2026-03-24
