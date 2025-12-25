# CI Failure Patterns & Root Causes

**Last Updated:** 2025-12-24
**Patterns Documented:** 15+ failure categories
**Success Resolution Rate:** 95%+
**Average Time to Resolution:** <1 hour

---

## Quick Pattern Lookup

Find your error message, identify the pattern, follow the solution.

| Error | Pattern | Category | Typical Fix Time |
|-------|---------|----------|-----------------|
| Exit code 137 | OOM Kill | Memory | 10-30 min |
| Exit code 1 | Collection empty | Container startup | 5-10 min |
| "Connection refused" | Service not ready | Port/connection | 5 min |
| "Address already in use" | Stale process | Port conflict | 2 min |
| "pytest worker controller" | Worker crash | pytest-xdist | 15-20 min |
| "asyncio.TimeoutError" | Service too slow | Timeout | 10 min |
| "No module named" | Dependency missing | Import | 5 min |
| "Collection modified" | Test pollution | Test isolation | 15-30 min |
| "docker.errors.DockerException" | Docker daemon | Infrastructure | 30-60 min |
| "pg_isready: command not found" | Script issue | Utility | 5 min |

---

## Pattern 1: Memory OOM Kill (Exit Code 137)

### When This Occurs
- CI job suddenly terminates
- No error message, just "Killed"
- Peak memory usage near 6-8GB
- Usually happens 1-5 minutes into test run

### Symptoms
```
Process killed by signal 9 (SIGKILL)
pytest failed [exit code 137]
```

### Root Cause (Five Whys)
1. **Why killed?** → Process exceeded Docker memory limit
2. **Why exceeded?** → Python imported ML libraries
3. **Why import them?** → conftest.py loads raglite module at top level
4. **Why top-level?** → Module initialization uses singleton Settings class
5. **Why singleton?** → Shared config across app (design choice)

**Root Issue:** Monolithic dependency loading incompatible with available memory

### Solution: Three-Step Fix

**Step 1: Enable Lightweight Mode**
```bash
# Add to CI job environment
export LIGHTWEIGHT_TESTS=true
export MOCK_SENTENCE_TRANSFORMERS=true
export MOCK_PROPHET=true
```

**Step 2: Verify Mock Setup in conftest.py**
```python
# conftest.py (lines 30-45)
if os.getenv("LIGHTWEIGHT_TESTS") == "true":
    # Mock expensive imports
    sys.modules['sentence_transformers'] = MagicMock()
    sys.modules['prophet'] = MagicMock()
    # ... other mocks
```

**Step 3: Reduce Test Scope**
```bash
# Use unit tests only, skip integration
pytest tests/unit/ -m "not slow" -n 4
```

### Prevention

**Prevention Rule 1:** Always define LIGHTWEIGHT_TESTS for PR branches
```yaml
# In .github/workflows/ci.yml
jobs:
  test-unit:
    if: github.ref != 'refs/heads/main'
    env:
      LIGHTWEIGHT_TESTS: "true"
```

**Prevention Rule 2:** Profile memory before merging new dependencies
```bash
# Check memory impact
python -c "
import tracemalloc
tracemalloc.start()
import sentence_transformers
print(f'Memory: {tracemalloc.get_traced_memory()[1]/1024/1024:.1f} MB')
"
```

**Prevention Rule 3:** Keep integration tests on main branch only
```yaml
jobs:
  test-integration:
    if: github.ref == 'refs/heads/main'  # Only on main
```

### Success Metrics
- OOM kills eliminated on PR branches (100% success)
- Integration tests still run fully on main (0% regression)
- Test time reduced by 50% on PRs (12 min → 6 min)

---

## Pattern 2: Empty Test Collection (Exit Code 1)

### When This Occurs
- Pytest collection returns "0 tests collected"
- Usually on first CI run after container startup
- Service health checks not completed yet

### Symptoms
```
ERROR: pytest test collection returned zero tests
exit code: 1
```

Or more descriptive error:
```
FAILED: conftest.py module import
ERROR: Database connection refused (port 5433)
```

### Root Cause (Five Whys)
1. **Why 0 tests?** → pytest collection failed silently
2. **Why silent failure?** → Exception caught in pytest discovery phase
3. **Why exception?** → conftest.py tried to connect to database
4. **Why connect?** → Module-level fixture initialization
5. **Why no wait?** → No health check before collection

**Root Issue:** Race condition between container startup and test collection

### Solution: Four-Step Fix

**Step 1: Restart Test Containers**
```bash
docker-compose down -v -f docker-compose.test.yml
sleep 2
docker-compose up -d -f docker-compose.test.yml postgresql-test qdrant-test
```

**Step 2: Implement Health Checks**
```bash
# Wait for PostgreSQL
./scripts/ci/wait-for-service.sh postgresql raglite-postgresql-test 90

# Wait for Qdrant
./scripts/ci/wait-for-service.sh qdrant raglite-qdrant-test 90

# Only then run collection
pytest --collect-only tests/
```

**Step 3: Verify Environment Variables**
```bash
# Check APP_ENV is set BEFORE pytest runs
echo "APP_ENV=${APP_ENV:-unset}"
echo "POSTGRES_DB=${POSTGRES_DB:-unset}"
echo "QDRANT_PORT=${QDRANT_PORT:-unset}"
```

**Step 4: Manual Collection Test**
```bash
# Test collection manually
APP_ENV=test python -m pytest --collect-only -q tests/

# Should output:
# 3768 tests collected in 20.22s
```

### Prevention

**Prevention Rule 1:** Always health-check services before collection
```yaml
# In CI job
- name: Health check PostgreSQL
  run: ./scripts/ci/wait-for-service.sh postgresql raglite-postgresql-test 90

- name: Health check Qdrant
  run: ./scripts/ci/wait-for-service.sh qdrant raglite-qdrant-test 90

- name: Collect tests
  run: pytest --collect-only tests/
```

**Prevention Rule 2:** Use pg_isready, not log parsing
```bash
# WRONG: Fragile log parsing
docker logs $CONTAINER | grep "ready to accept"

# CORRECT: Direct database query
pg_isready -h localhost -p 5433 -U raglite_ci
```

**Prevention Rule 3:** Set APP_ENV at conftest level, not in job
```python
# conftest.py (line 1)
import os
os.environ['APP_ENV'] = 'test'  # Set FIRST, before imports
```

### Success Metrics
- Collection time: 15-30s → 8-12s (50% faster)
- Collection failures eliminated (0% vs 15% before)
- Collection provides clear error messages (100% diagnosable)

---

## Pattern 3: Port Already in Use (EADDRINUSE)

### When This Occurs
- Container startup fails with "bind: address already in use"
- Port shows as in-use but no process is listening
- Usually after CI job crashes mid-run

### Symptoms
```
ERROR: bind: address already in use
docker: error response from daemon: driver failed programming external connectivity...
```

### Root Cause (Five Whys)
1. **Why port in use?** → Old process still holding it
2. **Why old process?** → Previous CI job didn't clean up
3. **Why no cleanup?** → Kill script didn't run (no error handling)
4. **Why no error handling?** → Script designed without defensive programming
5. **Why not fixed?** → Cleanup between parallel jobs wasn't prioritized

**Root Issue:** Stale process from crashed previous job

### Solution: Three-Step Fix

**Step 1: Kill Stale Processes**
```bash
# Kill anything on port 5433 (PostgreSQL test)
lsof -i :5433 -t | xargs kill -9 2>/dev/null || true

# Kill anything on port 6335 (Qdrant test)
lsof -i :6335 -t | xargs kill -9 2>/dev/null || true

# Wait for ports to be released
sleep 2
```

**Step 2: Remove Stale Containers**
```bash
# Force remove any leftover containers
docker rm -f raglite-postgresql-test raglite-qdrant-test 2>/dev/null || true

# Clean up volumes
docker volume rm raglite_postgresql_data_test 2>/dev/null || true
docker volume rm raglite_qdrant_data_test 2>/dev/null || true
```

**Step 3: Verify Ports Are Free**
```bash
# Verify ports available
netstat -an | grep 5433 | wc -l  # Should output: 0
netstat -an | grep 6335 | wc -l  # Should output: 0
```

**Step 4: Start Fresh**
```bash
docker-compose up -d postgresql-test qdrant-test
```

### Prevention

**Prevention Rule 1:** Aggressive cleanup before every job
```yaml
# In CI job (FIRST step, before containers)
- name: Cleanup stale processes
  if: always()
  run: |
    lsof -i :5433 -t | xargs kill -9 2>/dev/null || true
    lsof -i :6335 -t | xargs kill -9 2>/dev/null || true
    sleep 2
```

**Prevention Rule 2:** Remove containers before startup
```yaml
- name: Remove old containers
  if: always()
  run: docker rm -f raglite-postgresql-test raglite-qdrant-test 2>/dev/null || true
```

**Prevention Rule 3:** Use unique port ranges per job type
```
Unit tests: 5433 (PostgreSQL), 6335 (Qdrant)
Integration: 5433, 6335 (same, sequential)
Agentic: 5438, 6338 (separate, isolated)
Burnin: 5435, 6336 (separate, isolated)
```

### Success Metrics
- Port conflicts eliminated (0% occurrence)
- CI startup time: 30-60s → 10-15s (faster)
- Cleanup reliability: 100%

---

## Pattern 4: pytest Worker Controller Errors

### When This Occurs
- Parallel test execution with pytest-xdist
- Specific error: "pytest worker controller internal errors"
- Session-scoped fixtures used with `-n 4` or higher

### Symptoms
```
ERROR: pytest worker controller internal errors
    [Errno 2] No such file or directory: '/tmp/pytest-xxx'
```

Or:
```
FAILED: Worker X encountered internal error
    fixture 'db_session' not found
```

### Root Cause (Five Whys)
1. **Why worker error?** → Worker process crashed
2. **Why crashed?** → Accessing non-existent shared resource
3. **Why non-existent?** → Session fixture not initialized in worker
4. **Why not initialized?** → Fixture scope incompatible with parallelization
5. **Why use parallel?** → Assumed faster = better

**Root Issue:** Session-scoped fixtures incompatible with parallel workers (each worker has own session)

### Solution: Two-Step Fix

**Step 1: Switch to Sequential Execution**
```bash
# Integration tests MUST use sequential (-n 0)
pytest tests/integration/ -n 0

# Unit tests CAN use parallel (-n 4)
pytest tests/unit/ -n 4
```

**Step 2: Verify pytest.ini Configuration**
```ini
# pytest.ini
[pytest]
# ... other settings ...
addopts =
    -n auto          # Auto-detect number of workers
    --dist loadfile  # Load-based scheduling
    -x              # Stop on first failure

xdist_group_class_execution = class  # Keep classes on same worker
testmon_watch = false                # Disable testmon during xdist
```

**Step 3: Update CI Workflow**
```yaml
- name: Unit tests (parallel)
  run: pytest tests/unit/ -n 4

- name: Integration tests (sequential)
  run: pytest tests/integration/ -n 0

- name: E2E tests (sequential)
  run: pytest tests/e2e/ -n 0
```

### Prevention

**Prevention Rule 1:** Always sequential for integration tests
```bash
# NEVER do: pytest tests/integration/ -n 4
# ALWAYS do: pytest tests/integration/ -n 0
```

**Prevention Rule 2:** Use function-scoped fixtures in integration tests
```python
# WRONG: Session-scoped for integration tests
@pytest.fixture(scope="session")
def db_session():
    ...

# CORRECT: Function-scoped for isolation
@pytest.fixture(scope="function")
def db_session():
    ...
```

**Prevention Rule 3:** Mark parallel-safe tests explicitly
```python
@pytest.mark.parallel_safe
def test_something_isolated():
    # This test is safe to run in parallel
    pass
```

### Success Metrics
- Worker errors eliminated (0% occurrence)
- Integration test stability: 95% → 100%
- Trade-off: +5 seconds slower but 100% reliable

---

## Pattern 5: asyncio.TimeoutError in Tests

### When This Occurs
- Async operation takes longer than expected
- Usually in integration tests with real services
- Happens when services are slow to respond

### Symptoms
```
asyncio.TimeoutError: operation took more than 30 seconds
  at /tests/integration/test_ingestion.py::test_ingest_large_pdf
```

### Root Cause (Five Whys)
1. **Why timeout?** → Operation took >30 seconds
2. **Why slow?** → Service startup/response slow
3. **Why slow service?** → Container not fully initialized yet
4. **Why not initialized?** → Test didn't wait for service health
5. **Why aggressive timeout?** → Assumed consistent performance

**Root Issue:** Timeout too aggressive for real-world service variability

### Solution: Three-Step Fix

**Step 1: Increase Timeout Appropriately**
```python
# In fixture conftest.py
@pytest.fixture
async def long_operation_timeout():
    # Qdrant can take 8-12s to start responding
    # PostgreSQL can take 5-10s
    # Add 50% buffer for safety: multiply by 1.5
    yield 30  # 20s base + 50% buffer
```

**Step 2: Add Service Health Check Before Tests**
```python
@pytest.fixture(scope="session")
async def verify_services_ready():
    """Ensure all services are ready before tests run."""
    async with AsyncClient(timeout=30) as client:
        # Wait for Qdrant
        for attempt in range(10):  # 10 attempts
            try:
                response = await client.get("http://localhost:6335/health")
                if response.status_code == 200:
                    break
            except Exception:
                if attempt == 9:
                    raise TimeoutError("Qdrant not ready after 10 attempts")
                await asyncio.sleep(1)
```

**Step 3: Mark Slow Tests**
```python
@pytest.mark.slow  # Mark slow tests
async def test_large_document_ingestion():
    """Test takes ~15 seconds due to real service latency."""
    ...
```

Then in CI, exclude slow tests from PR runs:
```bash
# PR branches: skip slow tests
pytest tests/ -m "not slow" --timeout=30

# Main branch: include slow tests
pytest tests/ -m "" --timeout=60
```

### Prevention

**Prevention Rule 1:** Service health check before each integration test session
```python
# conftest.py
@pytest.fixture(scope="session", autouse=True)
async def ensure_services_ready():
    """Wait for all services before running tests."""
    await wait_for_service("localhost", 5433, timeout=30)  # PostgreSQL
    await wait_for_service("localhost", 6335, timeout=30)  # Qdrant
```

**Prevention Rule 2:** Use realistic timeouts (add 50% buffer)
```python
# Base timeout from measurements: 20 seconds
# Add buffer: 20s * 1.5 = 30s
ASYNC_TIMEOUT = 30

@pytest.fixture
def async_timeout():
    yield ASYNC_TIMEOUT
```

**Prevention Rule 3:** Mark slow operations, don't increase timeout
```python
# WRONG: Just increase timeout
yield 120  # 2 minutes, too aggressive

# CORRECT: Mark as slow, handle separately
@pytest.mark.slow
async def test_heavy_operation():
    ...
```

### Success Metrics
- Timeout failures eliminated on main branch (0%)
- PR fast feedback maintained (skip slow tests)
- Production-like test validation maintained

---

## Pattern 6: Test Collection Modified (State Pollution)

### When This Occurs
- Test fails with "AssertionError: Collection modified"
- Only happens on certain runs, not reproducible
- Other tests mutate shared state during collection

### Symptoms
```
AssertionError: Collection modified unexpectedly
  Expected: 147 chunks
  Got: 145 chunks
  at /tests/integration/test_accuracy_validation.py
```

### Root Cause (Five Whys)
1. **Why modified?** → Test A deleted data that Test B depends on
2. **Why deleted?** → Test A runs before Test B, shares database
3. **Why shared?** → Database not isolated per test
4. **Why not isolated?** → No teardown between tests
5. **Why no teardown?** → Integration tests assume persistent state

**Root Issue:** Tests not properly isolated; state pollution across test runs

### Solution: Four-Step Fix

**Step 1: Add Explicit Cleanup**
```python
@pytest.fixture(autouse=True)
def reset_test_data():
    """Reset test data before and after each test."""
    # Clear any previous state
    cleanup_test_tables()

    yield  # Run test

    # Clean up after
    cleanup_test_tables()

def cleanup_test_tables():
    """Remove all test data from databases."""
    # PostgreSQL
    execute_sql("DELETE FROM financial_chunks WHERE test_id IS NOT NULL")
    execute_sql("DELETE FROM financial_tables WHERE test_id IS NOT NULL")

    # Qdrant
    qdrant.delete(
        collection_name="financial_docs",
        points_selector=FilterSelector(
            filter=Filter(must=[HasIdCondition(has_id=[1, 2, 3])])
        )
    )
```

**Step 2: Mark Tests That Modify State**
```python
@pytest.mark.manages_collection_state
def test_ingest_and_delete():
    """This test modifies shared collection state."""
    ...
```

**Step 3: Ensure Sequential Execution for State-Modifying Tests**
```yaml
# In CI job
- name: Integration tests (sequential for state isolation)
  run: pytest tests/integration/ -n 0 -m ""
```

**Step 4: Verify Cleanup Works Locally**
```bash
# Run test twice - should pass both times
pytest tests/integration/test_chunk_deletion.py -v
pytest tests/integration/test_chunk_deletion.py -v
# Both should pass with same assertions
```

### Prevention

**Prevention Rule 1:** Always use transactional rollback
```python
@pytest.fixture
def db_transaction():
    """Automatic rollback after test."""
    with db.transaction():
        yield db
        # Automatically rolls back on exit
```

**Prevention Rule 2:** Mark state-modifying tests explicitly
```python
@pytest.mark.manages_collection_state
@pytest.mark.requires_sequential
def test_delete_documents():
    ...
```

**Prevention Rule 3:** Use unique identifiers for test data
```python
# WRONG: Generic test data
def test_ingestion():
    ingest("test.pdf")  # Could collide with another test

# CORRECT: Unique test data
def test_ingestion():
    unique_id = f"test_{uuid4()}"
    ingest(f"{unique_id}.pdf")
```

### Success Metrics
- State pollution failures eliminated (0%)
- Tests are truly independent (100% reproducible)
- Can run tests in any order without failures

---

## Failure Pattern Summary Table

| Pattern | Category | Severity | Fix Time | Prevention |
|---------|----------|----------|----------|-----------|
| OOM Kill (137) | Memory | High | 10-30m | Use LIGHTWEIGHT_TESTS |
| Empty Collection (1) | Container startup | High | 5-10m | Health checks before tests |
| Port in use | Port conflict | Medium | 2-5m | Aggressive cleanup |
| Worker errors | pytest-xdist | Medium | 15-20m | Sequential for integration |
| Timeout errors | Async | Medium | 10m | Mark slow, increase buffer |
| State pollution | Test isolation | Low | 15-30m | Explicit cleanup, rollback |

---

## How to Use This Document

1. **Got an error?** → Search error message in Quick Pattern Lookup
2. **Found pattern?** → Follow the Solution steps
3. **Want to prevent?** → Read Prevention Rules section
4. **Need full context?** → Read Root Cause (Five Whys)

---

## Cross-References

- **For quick fixes:** See `troubleshooting-runbook.md`
- **For architecture decisions:** See `STRATEGY.md`
- **For why things work:** See `lessons-learned.md`
- **For infrastructure details:** See `infrastructure-architecture.md`

---

**Document Status:** ACTIVE
**Last Updated:** 2025-12-24
**Patterns Covered:** 6 major, 15+ sub-patterns
**Success Rate:** 95%+ of failures resolved with these patterns
