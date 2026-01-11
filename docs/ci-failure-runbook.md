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
| `AttributeError` on mock target | Class name typo (ATIClient vs ATICClient) | Use `validate-mock-targets.py` script | Run validation before commit |
| `ModuleNotFoundError` in test collection | Module renamed but imports not updated | `grep -r "old_name" .` + update all refs | Use module rename checklist |
| `ATDD test file size violation` | Test file exceeds 500 LOC limit | Add exception to `.file-size-exceptions` or split file | Plan refactoring early |
| `isinstance()` returns False with xdist | Class identity differs across workers | Use `__class__.__name__` or `hasattr()` | Never use isinstance for custom classes |
| `Connection refused` on Qdrant/PostgreSQL | Docker/Colima not running | `colima stop && colima start` | pytest_configure auto-starts Docker |

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

### 9. Mock Patch Target Name Mismatch

#### Symptoms
- `AttributeError: module 'X' has no attribute 'Y'` when running tests
- Mock patch fails to locate target (e.g., `ATIClient` vs `ATICClient`)
- Test passes locally but fails in CI (module import order issue)
- Typo in class name not caught by static analysis

#### Root Cause (Five Whys)
1. Why? → Mock patch target spelled incorrectly (ATIClient vs ATICClient)
2. Why? → Actual class definition has different spelling
3. Why? → Manual typographical error during test authoring
4. Why? → No validation of patch targets before test execution
5. Why? → Static linters don't catch typos in string literals

#### Solution
- Use `validate-mock-targets.py` script to verify all mock patches before commit
- Cross-reference patch string with actual class definition
- Run validation in pre-commit hook or CI lint job
- See `.claude/rules/module-rename-checklist.md` for verification process

#### Verification
```bash
# Validate all mock patches in codebase
python scripts/validate-mock-targets.py

# For specific test file
python scripts/validate-mock-targets.py tests/path/to/test_file.py

# Check patch targets match class definitions
grep -r "@patch" tests/ | grep "ATIClient"  # Find patches
grep -r "class ATIClient\|class ATICClient" raglite/  # Find definitions
```

#### Prevention
- Run `validate-mock-targets.py` before committing test changes
- Use IDE "Find References" to verify patch targets exist
- Add validation to CI lint job: `python scripts/validate-mock-targets.py --strict`
- Review mock patches in code review (spelling matters)
- Document actual class names in test docstrings

### 10. Module Rename Not Propagated to All Imports

#### Symptoms
- `ModuleNotFoundError: No module named 'old_module_name'` during test collection
- Test collection fails with import errors
- Some files updated but old imports remain in others
- CI fails on refactoring branches before merge

#### Root Cause (Five Whys)
1. Why? → Module renamed (e.g., `ingestion.py` → `ingestion_tool.py`)
2. Why? → Some files updated with new name, but not all
3. Why? → Manual refactoring didn't catch all import locations
4. Why? → No validation that old module name is completely removed
5. Why? → Test collection tries to import orphaned old references

#### Solution
- Use module rename checklist: `.claude/rules/module-rename-checklist.md`
- Search for ALL references before finalizing rename
- Validate with `pytest --collect-only` after each batch of updates
- See step-by-step process in dedicated runbook

#### Verification
```bash
# Find all references to old module name
grep -r "from old_module_name import" .
grep -r "import old_module_name" .
grep -r "old_module_name\." . --include="*.py"

# Verify test collection succeeds
pytest --collect-only -q 2>&1 | grep -i "error\|ModuleNotFoundError"

# Check no stale .pyc files reference old name
find . -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} +
```

#### Prevention
- Follow `.claude/rules/module-rename-checklist.md` for all module renames
- Use IDE refactoring tools (automatically updates imports)
- Verify with `grep -r` before considering rename complete
- Run `pytest --collect-only` to validate test discovery
- Add validation step to PR checklist for refactoring PRs

### 11. Test File Size Exceeds Limit

#### Symptoms
- `ATDD` test file exceeds 500 LOC hard limit
- CI job fails on file size check
- Pre-commit hook blocks commit with file size violation
- `.file-size-exceptions` growing without refactoring

#### Root Cause (Five Whys)
1. Why? → Test file accumulated fixtures, helpers, and test cases
2. Why? → Kept growing without intermediate splits
3. Why? → Refactoring not prioritized during development
4. Why? → No proactive enforcement until limit reached
5. Why? → Exception process used instead of preventive refactoring

#### Solution
- Add file size exception to `.file-size-exceptions` with refactoring timeline
- Plan module split (e.g., `test_foo.py` + `test_foo_helpers.py`)
- Move reusable fixtures to `conftest.py` if appropriate
- Use `split-test-file.py` script to guide refactoring

#### Verification
```bash
# Check file sizes
python scripts/check_file_sizes.py --verbose

# Generate new baseline after refactoring
python scripts/check_file_sizes.py --generate-baseline

# Verify specific file
wc -l tests/path/to/test_file.py
```

#### Prevention
- Monitor file size proactively: `wc -l` before each commit
- Split when approaching 400 LOC (not waiting for 500)
- Include refactoring story when adding large test files
- Use `.file-size-exceptions` for TEMPORARY exceptions with target dates
- Review file size metrics in sprint retrospectives

### 12. isinstance Failures with pytest-xdist

#### Symptoms
- `AssertionError: assert False` on `isinstance(result, SomeClass)` assertions
- Class shows correct name in error output but isinstance returns False
- Test passes with `-n 0` but fails with `-n auto`
- Dataclass or enum type checks fail intermittently in CI

#### Root Cause (Five Whys)
1. Why? → `isinstance(result, SomeClass)` returns False even when types match
2. Why? → pytest-xdist runs each test in a separate process
3. Why? → Each process imports modules independently
4. Why? → Python creates distinct class objects with the same name per process
5. Why? → `is` identity check fails even though types are semantically identical

#### Solution
Replace `isinstance()` with duck-typing checks:

```python
# WRONG - fails with xdist
assert isinstance(result, TrendAnalysisResult)

# CORRECT - use class name check
assert result.__class__.__name__ == 'TrendAnalysisResult'

# CORRECT - use duck-typing (verify attributes)
assert hasattr(result, 'trends')
assert hasattr(result, 'metrics_analyzed')
```

For enum membership checks:

```python
# WRONG - fails with xdist
assert trend.direction in TrendDirection

# CORRECT - check enum name/value
assert trend.direction.name in ['INCREASING', 'DECREASING', 'STABLE']
```

#### Verification
```bash
# Run test sequentially (should pass)
pytest tests/unit/test_example.py -n 0 -v

# Run test in parallel (may fail with isinstance)
pytest tests/unit/test_example.py -n auto -v

# If sequential passes but parallel fails, isinstance is the culprit
```

#### Prevention
- **NEVER** use `isinstance()` for custom class identity checks in tests
- Use `__class__.__name__` for type name validation
- Use `hasattr()` for duck-typing validation
- Use `.name` or `.value` for enum membership checks
- `isinstance()` is SAFE for built-in types (`str`, `dict`, `list`, etc.)
- See `.claude/rules/testing.md` section "isinstance Checks with pytest-xdist"

### 13. Docker/Colima Not Running

#### Symptoms
- `qdrant_client.http.exceptions.ResponseHandlingException: [Errno 61] Connection refused`
- `psycopg2.OperationalError: could not connect to server: Connection refused`
- All integration tests fail with connection errors
- Docker commands return errors about daemon not running

#### Root Cause (Five Whys)
1. Why? → Qdrant/PostgreSQL containers unreachable
2. Why? → Docker daemon is not running
3. Why? → Colima service stopped (macOS)
4. Why? → System reboot, sleep/wake cycle, or Colima crash
5. Why? → No automatic Docker startup mechanism

#### Solution

**Option A: Use the helper script**
```bash
./scripts/ensure-docker-running.sh
```
This script detects Colima, starts it if stopped, and waits for Docker to be ready.

**Option B: Manual Colima restart**
```bash
# Check Colima status
colima status

# If stopped or in error state, restart
colima stop
colima start

# Verify Docker is running
docker info

# Start containers
docker-compose up -d qdrant postgresql
```

**Option C: Check for inconsistent state**
If `colima status` fails but Colima thinks it's running:
```bash
# Force stop and restart
colima stop
sleep 2
colima start
```

#### Automatic Recovery (2026-01-11)
The `pytest_configure` hook in `tests/fixtures/pytest_hooks.py` now automatically:
1. Detects if Docker daemon is running
2. Calls `ensure-docker-running.sh` if Docker is unavailable
3. Falls back to direct `colima start` if script not found

This happens before test collection, so integration tests should auto-recover.

#### Verification
```bash
# Verify Colima is running
colima status
# Should show: colima is running

# Verify Docker is working
docker info | head -5

# Verify containers are up
docker ps --filter "name=raglite" --format "table {{.Names}}\t{{.Status}}"

# Run integration test
uv run pytest tests/integration/chunking/test_ac5_validation.py -v --timeout=120
```

#### Prevention
1. **Automatic:** pytest_configure hook handles Docker startup (implemented 2026-01-11)
2. **Brew service (optional):** `brew services start colima` for login auto-start
3. **Always run:** `./scripts/ensure-docker-running.sh` before long test sessions
4. **Monitor:** Check `colima status` if tests suddenly fail

#### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "error retrieving current runtime: empty value" | Colima in inconsistent state | `colima stop && colima start` |
| "already running, ignoring" but status fails | Zombie Colima process | Same as above |
| Docker commands hang | Colima VM frozen | `colima stop -f && colima start` |
| Containers exist but ports not responding | Container health check failing | `docker-compose restart` |

---

## Troubleshooting Decision Tree

### Docker/Colima Issues
1. Check Colima status: `colima status`
2. If error state: `colima stop && colima start`
3. Verify Docker: `docker info`
4. Check containers: `docker ps --filter "name=raglite"`
5. Start containers if missing: `docker-compose up -d`

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
