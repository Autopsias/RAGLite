# CI Knowledge: Failure Patterns

## Failure Pattern: pytest-xdist Worker State Pollution

**First Observed:** 2025-12-28
**Frequency:** 3 times in past week
**Affected Files:** `tests/integration/test_ac3_ground_truth.py`, multiple integration tests

### Symptoms
- `pytest-xdist` showing "worker stopped unexpectedly"
- Test state leaking between different order runs
- Intermittent failures in parallel execution
- Settings singleton initialized before test isolation

### Root Cause (Five Whys)
1. Why? → Settings singleton initialized at import time
2. Why? → Global variable created at module level
3. Why? → No lazy loading pattern implemented
4. Why? → Assumed single-threaded test execution
5. Why? → No multiprocessing-safe design for CI

### Solution Applied
- Mark affected tests as `@pytest.mark.slow` to disable parallelization
- Use `--tb=short` flag for cleaner error output
- Implement lazy loading for settings (commit `9256895`)

### Verification
```bash
# Run tests without parallelization
uv run pytest tests/integration/test_ac3_ground_truth.py -n 0 --tb=short
# Verify no worker state issues
uv run pytest tests/integration/test_ac3_ground_truth.py --tb=short
```

### Prevention
- Always use lazy loading for global objects in test files
- Add `@pytest.mark.slow` for state-dependent tests
- Check `pytest-xdist` compatibility for new tests
- Use explicit test isolation fixtures

---

## Failure Pattern: Resource Tracker SIGKILL

**First Observed:** 2025-12-28
**Frequency:** 2 times in past week
**Affected Files:** `tests/integration/`, `tests/e2e/`

### Symptoms
- `SIGKILL` errors during parallel test execution
- Joblib multiprocessing processes not terminating
- CI jobs running out of memory
- Test hangs requiring manual intervention

### Root Cause (Five Whys)
1. Why? → Joblib processes not properly cleaned up
2. Why? → Resource tracker not disposed in teardown
3. Why? → Missing cleanup in pytest fixtures
4. Why? → No process management in CI environment
5. Why? → Assumed ephemeral process behavior

### Solution Applied
- Add orphaned process cleanup in CI workflow (commit `de770b1`)
- Implement `ResourceTracker` cleanup in fixtures
- Use `ensure_qdrant_test_isolation` lazy restoration pattern

### Verification
```bash
# Check for orphaned processes
ps aux | grep resource_tracker
# Verify resource cleanup
docker system prune -f
```

### Prevention
- Always clean up multiprocessing resources in `try/finally` blocks
- Add explicit resource disposal in test fixtures
- Monitor process counts during test execution
- Use memory limits in CI workflows

---

## Failure Pattern: Container Volume Mount Staleness

**First Observed:** 2025-12-28
**Frequency:** 4 times in past week
**Affected Files:** All database-dependent tests

### Symptoms
- "Databases Empty" despite data on disk
- `docker-compose` services not mounting correct volumes
- Tests failing with connection errors
- Different behavior between local and CI runs

### Root Cause (Five Whys)
1. Why? → Docker containers have stale volume mounts
2. Why? → Previous CI runs created incorrect mount paths
3. Why? → CI containers use ephemeral storage mismatch
4. Why? → No mount validation at startup
5. Why? → Assumed consistent environment behavior

### Solution Applied
- Add container mount validation script (commit `f282531`)
- Use `./scripts/start-dev.sh` for development startup
- Implement volume mount checks in CI workflows

### Verification
```bash
# Verify mount paths
docker inspect raglite-qdrant --format='{{json .Mounts}}'
docker inspect raglite-postgresql --format='{{json .Mounts}}'
# Run validation script
./scripts/start-dev.sh
```

### Prevention
- Always verify mount paths before running tests
- Use dedicated scripts for container management
- Check mounts with `docker inspect` after CI runs
- Use unique container names per CI job type

---

## Failure Pattern: Mock Patch Interference

**First Observed:** 2025-12-28
**Frequency:** 5 times in past week
**Affected Files:** `tests/unit/`, `tests/integration/`

### Symptoms
- Mocks not working as expected
- Different behavior between local and CI runs
- Stale mock state across test runs
- Patch targets not being recognized

### Root Cause (Five Whys)
1. Why? → Mocks applied at wrong scope
2. Why? → Class-level vs function-level patching confusion
3. Why? → Mock definitions at import location
4. Why? → No isolation between test runs
5. Why? → Missing context management

### Solution Applied
- Patch wrapper functions, not direct imports (commit `ea9b558`)
- Apply mocks where objects are USED, not defined
- Use explicit `@pytest.fixture` with `autouse=True`

### Verification
```bash
# Test mock isolation
uv run pytest tests/unit/ -v --tb=short
# Verify no interference between test runs
uv run pytest tests/unit/ --tb=short -n 4
```

### Prevention
- Always patch at usage location, not definition
- Use wrapper functions for external libraries
- Add clear documentation on mock patterns
- Use explicit mock cleanup in fixtures

---

## Failure Pattern: AsyncMock Requirements

**First Observed:** 2025-12-28
**Frequency:** 3 times in past week
**Affected Files:** `tests/integration/`, `tests/e2e/`

### Symptoms
- Async functions not properly mocked
- Test failures in async code
- Missing call count assertions
- TypeError: coroutine not awaited

### Root Cause (Five Whys)
1. Why? → Standard Mock doesn't handle async
2. Why? → Missing `AsyncMock` for async functions
3. Why? → Incorrect patching of async methods
4. Why? → No proper async test patterns
5. Why? → Legacy test code migration needed

### Solution Applied
- Use `AsyncMock` for all async functions (commit `f282531`)
- Patch wrapper functions, not direct async calls
- Verify call counts match expected behavior

### Verification
```bash
# Test async mocking
uv run pytest tests/integration/ -v --tb=short
# Verify async function calls
uv run pytest tests/integration/ --mock-call-counts
```

### Prevention
- Always import `unittest.mock.AsyncMock`
- Patch async functions at usage location
- Add explicit call verification in tests
- Use `await` for async mocked calls

---

## Failure Pattern: Python Bytecode Cache Pollution

**First Observed:** 2025-12-28
**Frequency:** 5-8 times per week (intermittent failures)
**Affected Files:** All test files (non-deterministic impact)

### Symptoms
- Tests pass locally but fail in CI
- `ModuleNotFoundError` or `ImportError` after CI runs
- Intermittent failures across different test suites
- Stale `.pyc` files in `__pycache__` directories
- Different behavior in consecutive CI runs

### Root Cause (Five Whys)
1. Why? → Python writes `.pyc` bytecode files during import
2. Why? → Multiple CI processes write to same `__pycache__`
3. Why? → CI runners reuse environments between builds
4. Why? → Old bytecode persists from previous test runs
5. Why? → No mechanism to prevent bytecode generation

### Solution Applied
- Set `PYTHONDONTWRITEBYTECODE=1` globally in CI (commit `a04ba51`)
- Clear bytecode cache in cache cleanup action
- Use find command to remove stale `__pycache__` directories

### Verification
```bash
# Verify bytecode prevention
export PYTHONDONTWRITEBYTECODE=1
uv run pytest tests/ -q
find . -type d -name __pycache__ | wc -l  # Should be 0

# Verify CI cleanup works
./scripts/ci/validate-cache  # Part of workflow
```

### Prevention
- Always set `PYTHONDONTWRITEBYTECODE=1` in CI `env:` section
- Add cache cleanup before and after test runs
- Use `find . -type d -name __pycache__ -exec rm -rf {} +`
- Verify no `.pyc` files created during CI runs

---

## Failure Pattern: Joblib Multiprocessing Deadlocks

**First Observed:** 2025-12-28
**Frequency:** 2-3 times per week (hanging tests)
**Affected Files:** Tests using statsmodels, pmdarima, or joblib-backed libraries

### Symptoms
- Tests hang indefinitely during parallel execution
- Job timeout triggered (30 min+ wait)
- "Resource exhaustion" or OOM in logs
- Works fine with `-n 0` (serial mode)
- Loky worker processes never terminate

### Root Cause (Five Whys)
1. Why? → Joblib uses Loky backend for multiprocessing
2. Why? → Loky spawns worker processes for CPU-bound tasks
3. Why? → pytest-xdist also uses multiprocessing for test distribution
4. Why? → Both systems compete for CPU resources in CI
5. Why? → Resource contention causes Loky workers to deadlock

### Solution Applied
- Set `LOKY_MAX_CPU_COUNT=1` in CI to disable Loky (commit `a04ba51`)
- Keep pytest-xdist at `-n 4` for fast unit tests
- Use `-n 1` for integration tests with multiprocessing code

### Verification
```bash
# Verify LOKY_MAX_CPU_COUNT prevents multiprocessing
export LOKY_MAX_CPU_COUNT=1
uv run pytest tests/integration/ -n 1 --tb=short --timeout=120
# Verify no hanging tests

# Check process count (should be stable)
ps aux | wc -l
```

### Prevention
- Always set `LOKY_MAX_CPU_COUNT=1` in CI `env:` section
- Mark tests using joblib/statsmodels with `@pytest.mark.slow`
- Use `-n 1` parallelism for integration tests
- Monitor process count during test runs
