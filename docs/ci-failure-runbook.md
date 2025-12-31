# CI Failure Runbook

Quick reference for diagnosing and resolving CI failures.

**Last Updated:** 2025-12-30
**CI Infrastructure Version:** 1.1 (self-hosted runners with resource isolation)

## Quick Reference

| Failure Pattern | Likely Cause | Quick Fix | Prevention |
|-----------------|--------------|-----------|-----------|
| `pytest-xdist worker pollution` | Singleton init at import time | Mark test `@pytest.mark.slow` | Use lazy loading |
| `SIGKILL` during parallel jobs | Resource tracker leaks | `pkill -9 -f resource_tracker` | Add cleanup in CI workflow |
| `Database Empty` errors | Stale container mounts | `./scripts/start-dev.sh` | Validate mounts in CI |
| `PYTHONPATH bytecode cache` | `.pyc` pollution between runs | Set `PYTHONDONTWRITEBYTECODE=1` | Enabled globally in CI |
| `Joblib multiprocessing deadlock` | Process conflicts with pytest | Set `LOKY_MAX_CPU_COUNT=1` | Enabled globally in CI |
| `TimeoutError` in async | Timing too aggressive | Increase `--timeout` | Review test performance |
| `APIConnectionError` | Missing mock | Check wrapper function mock | Patch at usage location |
| `ATDD subprocess TimeoutError` | 180s timeout insufficient for subprocess | Increase to 300s timeout | Register marker, exclude from defaults |
| `pytest.mark.atdd unregistered` | Marker not in pytest.ini | Add to `markers` section | Always register markers with --strict-markers |

---

## Failure Categories

### 1. pytest-xdist Worker State Pollution

#### Symptoms
- Test state leaking between workers
- intermittent failures in different order runs
- `pytest-xdist` showing "worker stopped unexpectedly"
- Settings singleton initialized before test isolation

#### Root Cause (Five Whys)
1. Why? → Settings singleton initialized at import time
2. Why? → Global variable created at module level
3. Why? → No lazy loading pattern implemented
4. Why? → Assumed single-threaded test execution
5. Why? → No multiprocessing-safe design

#### Solution
- Mark affected tests as `@pytest.mark.slow` to disable parallelization
- Use `--tb=short` flag for cleaner error output
- Implement lazy loading for settings in `9256895`

#### Prevention
- Always use lazy loading for global objects
- Add `@pytest.mark.slow` for state-dependent tests
- Check `pytest-xdist` compatibility for new tests

### 2. Resource Tracker SIGKILL

#### Symptoms
- `SIGKILL` errors during parallel test execution
- Joblib multiprocessing processes not terminating
- CI jobs running out of memory
- Test hangs that require manual intervention

#### Root Cause (Five Whys)
1. Why? → Joblib processes not properly cleaned up
2. Why? → Resource tracker not disposed in teardown
3. Why? → Missing cleanup in pytest fixtures
4. Why? → No process management in CI environment
5. Why? → Assumed ephemeral process behavior

#### Solution
- Add orphaned process cleanup in CI workflow (commit `de770b1`)
- Implement `ResourceTracker` cleanup in fixtures
- Use `ensure_qdrant_test_isolation` lazy restoration pattern

#### Prevention
- Always clean up multiprocessing resources
- Add `try/finally` blocks for process management
- Check for orphaned processes after test runs

### 3. Container Volume Mount Staleness

#### Symptoms
- "Databases Empty" despite data on disk
- `docker-compose` services not mounting correct volumes
- Tests failing with connection errors
- Different behavior between local and CI runs

#### Root Cause (Five Whys)
1. Why? → Docker containers have stale volume mounts
2. Why? → Previous CI runs created incorrect mount paths
3. Why? → CI containers use ephemeral storage mismatch
4. Why? → No mount validation at startup
5. Why? → Assumed consistent environment behavior

#### Solution
- Add container mount validation script (commit `f282531`)
- Use `./scripts/start-dev.sh` for development startup
- Implement volume mount checks in CI workflows

#### Prevention
- Always verify mount paths before running tests
- Use dedicated scripts for container management
- Check mounts with `docker inspect --format='{{json .Mounts}}'`

### 4. Mock Patch Interference

#### Symptoms
- Mocks not working as expected
- Different behavior between local and CI runs
- Stale mock state across test runs
- Patch targets not being recognized

#### Root Cause (Five Whys)
1. Why? → Mocks applied at wrong scope
2. Why? → Class-level vs function-level patching confusion
3. Why? → Mock definitions at import location
4. Why? → No isolation between test runs
5. Why? → Missing context management

#### Solution
- Patch wrapper functions, not direct imports (commit `ea9b558`)
- Apply mocks where objects are USED, not defined
- Use explicit `@pytest.fixture` with `autouse=True`

#### Prevention
- Always patch at usage location, not definition
- Use wrapper functions for external libraries
- Add clear documentation on mock patterns

### 5. AsyncMock Pattern Requirements

#### Symptoms
- Async functions not properly mocked
- Test failures in async code
- Missing call count assertions
- TypeError: coroutine not awaited

#### Root Cause (Five Whys)
1. Why? → Standard Mock doesn't handle async
2. Why? → Missing `AsyncMock` for async functions
3. Why? → Incorrect patching of async methods
4. Why? → No proper async test patterns
5. Why? → Legacy test code migration needed

#### Solution
- Use `AsyncMock` for all async functions (commit `f282531`)
- Patch wrapper functions, not direct async calls
- Verify call counts match expected behavior

#### Prevention
- Always import `unittest.mock.AsyncMock`
- Patch async functions at usage location
- Add explicit call verification in tests

### 6. Bytecode Cache Pollution (`.pyc` Files)

#### Symptoms
- Intermittent test failures
- Tests pass locally but fail in CI
- `ModuleNotFoundError` or `ImportError` after runs
- Stale `.pyc` files in `__pycache__` directories

#### Root Cause (Five Whys)
1. Why? → Python writes `.pyc` bytecode files during import
2. Why? → Multiple processes writing to same `__pycache__`
3. Why? → CI runners reuse environments between builds
4. Why? → Bytecode from old code versions pollutes cache
5. Why? → No environment isolation between runs

#### Solution
- Set `PYTHONDONTWRITEBYTECODE=1` globally in CI (commit `a04ba51`)
- Clear bytecode cache between test runs
- Use cache cleanup action in CI workflows

#### Prevention
- Always set `PYTHONDONTWRITEBYTECODE=1` in CI `env:`
- Add pre-test cache cleanup step
- Use `find . -type d -name __pycache__ -exec rm -rf {} +`

### 7. Joblib Multiprocessing Resource Conflicts

#### Symptoms
- Hanging tests that require timeout
- Resource exhaustion during parallel execution
- Loky worker process deadlocks
- Job never completes or kills with OOM

#### Root Cause (Five Whys)
1. Why? → Joblib uses Loky backend for multiprocessing
2. Why? → Loky creates multiple worker processes
3. Why? → pytest-xdist also uses multiprocessing
4. Why? → Both try to allocate CPU resources in CI
5. Why? → Resource contention causes deadlocks

#### Solution
- Set `LOKY_MAX_CPU_COUNT=1` in CI to disable Loky parallelism (commit `a04ba51`)
- Keep pytest-xdist parallelism at `-n 4` for unit tests
- Use `-n 1` for integration tests with multiprocessing code

#### Prevention
- Always set `LOKY_MAX_CPU_COUNT=1` in CI `env:`
- Reduce parallelism for tests using joblib/statsmodels
- Monitor resource usage during test runs

### 8. ATDD Subprocess Timeout (Story 8.4b)

#### Symptoms
- `TimeoutError: Test took too long (180s)` in ATDD validation job
- ATDD tests pass locally but fail in CI
- Subprocess tests hanging or taking >3 minutes
- `pytest.mark.atdd unregistered` error with `--strict-markers`

#### Root Cause (Five Whys)
1. Why? → ATDD tests spawn subprocesses that run code dynamically
2. Why? → Subprocess execution includes process creation overhead (~5-10s)
3. Why? → Default timeout (120s-180s) insufficient for subprocess lifecycle
4. Why? → ATDD marker not registered when test suite changed
5. Why? → Marker filtering didn't skip ATDD in default validation job

#### Solution
- Increased timeout from 180s to 300s for subprocess tests (commit `cb20a3b`)
- Registered `atdd` marker in pytest.ini `markers` section
- Excluded ATDD tests from default runs: `-m "not slow and not health_check and not atdd"`
- Created dedicated `atdd-validation` CI job (main branch only)

#### Verification
```bash
# Verify marker registration
grep "atdd:" pytest.ini

# Run ATDD tests locally with 300s timeout
pytest tests/atdd/story_8_4b/ -m atdd --timeout=300 -n 0

# Check marker filtering in validation job
pytest tests/ -m "not atdd" --collect-only | grep atdd | wc -l  # Should be 0
```

#### Prevention
- Always register pytest markers in pytest.ini when creating new test categories
- Use `--strict-markers` in CI to catch unregistered markers
- Set appropriate timeouts for subprocess tests (300s minimum)
- Run subprocess-heavy tests sequentially (`-n 0`) to avoid resource contention
- Exclude subprocess tests from default runs to maintain fast feedback loop
- Document timeout rationale in pytest.ini comments

---

## Troubleshooting Decision Tree

### Database Connection Issues
1. Check container mounts: `docker inspect --format='{{json .Mounts}}'`
2. Verify database ports:
   - Production: 6333/5432
   - Test: 6335/5433
3. Run mount validation: `./scripts/start-dev.sh`
4. Check if using correct `APP_ENV`

### Test Failures
1. Run tests locally: `uv run pytest tests/ --tb=short`
2. Check for `pytest-xdist` issues: disable with `-n 0`
3. Verify mock patches are at usage location
4. Look for orphaned processes: `ps aux | grep resource_tracker`

### CI Pipeline Issues
1. Check for stale container mounts
2. Verify volume mounts are correct
3. Look for SIGKILL in logs
4. Check memory usage and resource cleanup

### Performance Issues
1. Check for `slow` test markers
2. Look for parallel execution issues
3. Verify async function mocking
4. Check for resource leaks

---

## Prevention Checklist

### Before Running Tests
- [ ] Use `./scripts/start-dev.sh` for development
- [ ] Verify container mounts with `docker inspect`
- [ ] Check for orphaned processes
- [ ] Ensure `APP_ENV=test` is set

### When Adding New Tests
- [ ] Use `@pytest.mark.integration` for integration tests
- [ ] Patch wrapper functions, not direct imports
- [ ] Use `AsyncMock` for async functions
- [ ] Add test isolation cleanup

### CI Pipeline Setup
- [ ] Use unique container names for each job
- [ ] Implement mount validation before tests
- [ ] Add resource cleanup after runs
- [ ] Use ephemeral storage for CI containers

### Test Pattern Compliance
- [ ] Lazy loading for global objects
- [ ] Proper async function handling
- [ ] Explicit mock patching
- [ ] State isolation between runs
