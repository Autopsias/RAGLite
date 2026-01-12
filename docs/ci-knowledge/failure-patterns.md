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

---

## Failure Pattern: Mock Patch Target Drift (Strategic Analysis 2025-01-11)

**First Observed:** 2025-01-08 (Epic 8 refactoring)
**Frequency:** ~12% of CI failures in recent sprints
**Strategic Impact:** Part of 39% CI fix commits (systemic root cause)
**Enforcement Mechanism:** `scripts/validate-mock-targets.py` runs in CI lint-gate job

### Symptoms

- `AttributeError: module 'X' has no attribute 'Y'` when running tests with mocks
- Mock patch fails silently (creates attribute in test, doesn't affect actual code)
- Test passes in isolation but fails in suite (import order dependent)
- Typo in class name not caught by linters: `ATIClient` vs `ATICClient`
- Patch target string references non-existent module attributes

### Root Cause (Five Whys)

1. **Why?** → Mock patch target spelled incorrectly or module name changed during refactoring
2. **Why?** → Manual refactoring didn't update all patch target strings systematically
3. **Why?** → Mock targets are string literals, not validated by static analysis tools
4. **Why?** → No tool checks that patch strings match actual class/function names
5. **Why?** → String-based patching creates drift when code is refactored

### Solution Applied

**Proactive Prevention (Added 2025-01-11):**

1. Created `scripts/validate-mock-targets.py` to verify all patch targets before commit
2. Script cross-references patch strings against actual class/function definitions
3. CI job runs validation on all PRs (part of lint-gate job) - **blocks invalid patches**
4. Pre-commit hook added to catch issues before push
5. Mock patch patterns documented in `.claude/rules/testing.md`

**How It Works:**

```bash
# Run validation before commit
python scripts/validate-mock-targets.py

# For specific test file
python scripts/validate-mock-targets.py tests/path/to/test_file.py --verbose

# CI enforcement (fails on any error)
python scripts/validate-mock-targets.py --strict
```

### Verification

```bash
# Validate all mock patches in codebase
python scripts/validate-mock-targets.py

# Run after test file updates
python scripts/validate-mock-targets.py --verbose

# Check CI validation passes
grep "validate-mock-targets" .github/workflows/ci.yml
```

### Prevention Checklist

- [ ] Run `validate-mock-targets.py` before committing test changes
- [ ] Use IDE "Find References" to verify patch targets exist
- [ ] Review mock patches in code review (spelling and module paths matter)
- [ ] Document actual class/function names in test docstrings
- [ ] Use `patch.object()` when possible (type-safe variant)

### Related Documentation

- **Runbook:** `docs/ci-failure-runbook.md` → Section 9 (Mock Patch Target Name Mismatch)
- **Prevention Tool:** `scripts/validate-mock-targets.py`
- **Testing Rules:** `.claude/rules/testing.md` → Mock Patching section
- **CI Strategy:** `docs/ci-strategy.md` → Mock Standards section

---

## Failure Pattern: pytest-xdist isinstance() Failures (Strategic Analysis 2025-01-11)

**First Observed:** 2025-01-08 (Epic 8 test validation)
**Frequency:** ~15% of CI failures in parallel test runs
**Strategic Impact:** Part of 39% CI fix commits (systemic root cause)
**Enforcement Mechanism:** `scripts/check-isinstance-violations.sh` runs in CI lint-gate job

### Symptoms

- `AssertionError: assert False` on `isinstance(result, CustomClass)` checks
- Test passes with `-n 0` (sequential) but fails with `-n auto` (parallel)
- Class name appears correct in error output but isinstance returns False
- Dataclass or enum type checks fail intermittently in CI only
- Same code works locally (single process) but fails in CI (parallel workers)

### Root Cause (Five Whys)

1. **Why?** → `isinstance(result, CustomClass)` returns False despite matching types
2. **Why?** → pytest-xdist runs each test in a separate OS process
3. **Why?** → Each process independently imports all modules
4. **Why?** → Python creates distinct class objects with same name per process
5. **Why?** → `isinstance()` uses object identity (`is`) comparison, not name matching

### Solution Applied

**Proactive Prevention (Added 2025-01-11):**

1. Created `scripts/check-isinstance-violations.sh` to detect xdist-incompatible patterns
2. CI job runs linter on all PRs (part of lint-gate job) - **blocks violations**
3. Automated detection prevents isinstance patterns from ever reaching test execution
4. Prevention rules documented in `.claude/rules/testing.md`
5. All existing isinstance() violations fixed before merge

**How It Works:**

```bash
# Run detection before commit
./scripts/check-isinstance-violations.sh

# Output shows violations with fix suggestions
VIOLATION: tests/unit/test_example.py:42
  assert isinstance(result, TrendAnalysisResult)
  Suggested fix: Use __class__.__name__ or hasattr() instead

# CI blocks commits with violations
```

**Correct Patterns:**

```python
# CORRECT - use class name check
assert result.__class__.__name__ == 'TrendAnalysisResult'

# CORRECT - use duck-typing (verify attributes)
assert hasattr(result, 'trends')
assert hasattr(result, 'metrics_analyzed')

# CORRECT - for enum checks
assert trend.direction.name in ['INCREASING', 'DECREASING', 'STABLE']
```

### Prevention Checklist

- [ ] Never use `isinstance()` for custom class checks
- [ ] Use `__class__.__name__` for type validation
- [ ] Use `hasattr()` for duck-typing checks
- [ ] Use `.name` or `.value` for enum checks
- [ ] Run `check-isinstance-violations.sh` before committing
- [ ] CI blocks commits with xdist-incompatible patterns

### Related Documentation

- **Runbook:** `docs/ci-failure-runbook.md` → Section 12 (isinstance Failures)
- **Testing Rules:** `.claude/rules/testing.md` → isinstance Checks section
- **Linter Script:** `scripts/check-isinstance-violations.sh`
- **CI Strategy:** `docs/ci-strategy.md` → Prevention Rules section

---

## Failure Pattern: Docker/Colima Not Running (Strategic Analysis 2025-01-11)

**First Observed:** 2025-01-08 (Epic 8 CI analysis)
**Frequency:** ~10% of CI failures in integration test runs
**Strategic Impact:** Part of 39% CI fix commits (systemic root cause)
**Enforcement Mechanism:** `pytest_configure` hook auto-starts Docker before test collection

### Symptoms

- `qdrant_client.http.exceptions.ResponseHandlingException: [Errno 61] Connection refused`
- `psycopg2.OperationalError: could not connect to server: Connection refused`
- All integration tests fail with connection errors
- Error occurs at fixture setup time, before test execution
- Intermittent failures (depends on whether Colima service is running)

### Root Cause (Five Whys)

1. **Why?** → Qdrant/PostgreSQL containers unreachable on their ports
2. **Why?** → Docker daemon is not running (containers not executing)
3. **Why?** → Colima VM stopped (macOS Docker Desktop alternative)
4. **Why?** → System reboot, sleep/wake cycle, or Colima crash
5. **Why?** → No automatic Docker startup mechanism in test fixtures

### Solution Applied

**Automatic Recovery (Added 2025-01-11):**

The `pytest_configure` hook in `tests/fixtures/pytest_hooks.py` now:
1. Detects if Docker daemon is running (before test collection)
2. Calls `scripts/ensure-docker-running.sh` if Docker is unavailable
3. Falls back to direct `colima start` if script not found
4. Waits for Docker to be ready before test collection begins
5. Skips integration tests gracefully if recovery fails

**How It Works:**

```bash
# Automatic - happens before pytest test collection
# If Docker not running:
#   1. Start Colima
#   2. Wait for Docker daemon
#   3. Proceed with tests

# Manual recovery (if needed)
./scripts/ensure-docker-running.sh
```

### Prevention Checklist

- [ ] Automatic recovery via pytest_configure (already implemented)
- [ ] Manual verification before long test sessions: `colima status`
- [ ] Optional auto-start: `brew services start colima`
- [ ] Check Docker health if tests suddenly fail: `docker info`
- [ ] Verify containers are healthy: `docker ps --filter "name=raglite"`

### Related Documentation

- **Runbook:** `docs/ci-failure-runbook.md` → Section 13 (Docker/Colima)
- **Database Safety:** `.claude/rules/database-safety.md` → Container Lifecycle
- **Infrastructure:** `scripts/ensure-docker-running.sh`
- **Fixture Hooks:** `tests/fixtures/pytest_hooks.py` → pytest_configure hook
- **CI Strategy:** `docs/ci-strategy.md` → Infrastructure Improvements

---

## Failure Pattern: Fixture Validation Range Too Strict (Strategic 2025-01-11)

**First Observed:** 2025-01-11 (Epic 8: PDF optimization)
**Frequency:** 949-test cascade failure from single root cause
**Affected Files:** `tests/integration/fixtures/_ingestion_helpers.py`, `tests/integration/fixtures/ingestion/verification_helpers.py`
**Strategic Impact:** Revealed systemic validation anti-pattern across test suite

### Symptoms

- `AssertionError: 120 not in range(10, 55)` in session fixture validation
- Chunk count validation fails for variable-size documents
- Non-deterministic chunk boundaries cause intermittent failures
- Same document produces different chunk counts in different runs
- Tests pass/fail based on document content variation
- 949 tests fail because single fixture has too-strict range check

### Root Cause (Five Whys)

1. Why? → Session fixture used hardcoded chunk count range (10, 55)
2. Why? → Range was arbitrary, not based on actual chunk distribution analysis
3. Why? → Document processors produce non-deterministic chunk boundaries
4. Why? → No tolerance mechanism for valid chunk count variations
5. Why? → Hard assertion on arbitrary range instead of baseline ± tolerance

### Solution Applied

- Replaced hardcoded ranges with tolerance-based validation (baseline ± 15%)
- Calculate expected range dynamically: baseline * (1 ± tolerance)
- Allow document-specific variance within tolerance band
- Example: If baseline is 80 chunks, accept 68-92 (80 ± 15%)
- Updated verification helpers to use tolerance-based checks

### Verification

```bash
# Test with 10-page fixture (produces ~80 chunks)
uv run pytest tests/integration/fixtures/_ingestion_helpers.py -v

# Verify actual chunk distribution
uv run pytest tests/integration/ -k "pdf" --collect-only -q
```

### Prevention

- Always use tolerance-based assertions for non-deterministic values
- Document baseline expectations in test comments
- Test with multiple document sizes and types to establish realistic ranges
- Use parametrized tests to catch edge cases systematically
- Never hardcode expected ranges without statistical reasoning
- Review tolerance ranges annually as systems evolve

### Related Documentation

- **Runbook:** `docs/ci-failure-runbook.md` → Section 14 (Fixture Validation)
- **Prevention Rules:** `docs/ci-knowledge/prevention-rules.md` → Tolerance-Based Validation
- **CI Strategy:** `docs/ci-strategy.md` → Test Validation Patterns

---

## Failure Pattern: API Contract Drift - Signature Changes Not Propagated (Strategic 2025-01-11)

**First Observed:** 2025-01-11 (Epic 8: Epic 6 forecast API integration)
**Frequency:** 5 test methods failed from single API signature change
**Affected Files:** `tests/integration/epic6/test_forecast_execution.py`, `tests/integration/epic6/test_real_data_validation.py`
**Strategic Impact:** Revealed missing automated API contract validation

### Symptoms

- `TypeError: generate_ensemble_forecast() missing required argument: 'historical_data'`
- Function signature changed but test calls unchanged across multiple files
- Works in main branch but fails after Epic 6 merge
- Multiple test methods fail with same error pattern (5+ failures)
- 11 mock patches became obsolete when function signature was updated
- Error only visible at test execution time, not during import

### Root Cause (Five Whys)

1. Why? → API function signature changed (added required `historical_data` parameter)
2. Why? → Test method calls to function not updated systematically across all files
3. Why? → Change was localized to one module (forecast execution)
4. Why? → No automated check for function signature changes at merge time
5. Why? → Tests passed locally before Epic 6 but failed after merge to main

### Solution Applied

- Added API contract tests to detect signature drift early
- Updated all 5 test method calls to pass required `historical_data` parameter
- Removed 11 obsolete mock patches that referenced old function signature
- Implemented systematic validation of function parameters

### Verification

```bash
# Run API contract tests
uv run pytest tests/integration/epic6/ -v -k "contract"

# Check for remaining signature mismatches
grep -r "generate_ensemble_forecast" tests/ --include="*.py" | grep -v "historical_data"
```

### Prevention

- Add contract tests for all public API functions (especially those that change)
- Include function signature in docstring with parameter documentation
- Document required vs optional parameters explicitly
- Use type hints to make contracts visible
- Run contract tests as part of CI (before feature tests)
- Update contract test when intentionally changing API signature

### Related Documentation

- **Runbook:** `docs/ci-failure-runbook.md` → Section 15 (API Contract Drift)
- **Prevention Rules:** `docs/ci-knowledge/prevention-rules.md` → API Contract Testing
- **CI Strategy:** `docs/ci-strategy.md` → Test Validation Patterns

---

## Failure Pattern: Config-Test Synchronization Drift (Strategic 2025-01-11)

**First Observed:** 2025-01-11 (Epic 8: Metric configuration references)
**Frequency:** 3 tests failed due to missing configured metric (`cement_demand`)
**Affected Files:** Test fixture configuration, system config.yaml
**Strategic Impact:** Revealed lack of cross-file validation mechanisms

### Symptoms

- `KeyError: 'cement_demand'` when accessing configured metric from test fixture
- Metric referenced in test fixture but not defined in config.yaml
- Test expects metric to exist but configuration doesn't include it
- Inconsistency between pytest fixtures and system configuration
- Configuration changes made without updating dependent test fixtures
- Error only occurs at test data setup time (not visible until tests run)

### Root Cause (Five Whys)

1. Why? → Metric removed from config.yaml but test fixtures still reference it
2. Why? → Configuration changes made without systematically updating dependent tests
3. Why? → No validation that configured metrics exist in test expectations
4. Why? → No CI job to verify config-test synchronization before merge
5. Why? → Metrics added/removed without cross-file impact analysis

### Solution Applied

- Added config-test synchronization verification in test fixtures
- Implemented validation that all configured metrics are tested
- Implemented validation that all tested metrics are configured
- Documented metric definitions in both config and test files

### Verification

```bash
# Verify config-test synchronization
uv run pytest tests/ -v -k "sync" --tb=short

# Check config metrics
grep "metrics:" raglite/config.yaml -A 10

# Check test expectations
grep "EXPECTED_METRICS\|cement_demand" tests/ -r --include="*.py"
```

### Prevention

- Run config-test sync verification as part of pre-commit validation
- Include config changes in test review checklist (cross-file impact)
- Document metric definitions in both config.yaml and test fixtures
- Use shared constants for metric names (avoid duplication/drift)
- Add validation to config loader (verify referenced metrics exist)
- Treat config updates as API changes requiring test updates

### Related Documentation

- **Runbook:** `docs/ci-failure-runbook.md` → Section 16 (Config Sync Drift)
- **Prevention Rules:** `docs/ci-knowledge/prevention-rules.md` → Config-Test Synchronization
- **CI Strategy:** `docs/ci-strategy.md` → Test Validation Patterns

---

## Failure Pattern: Lazy Import Mock Coverage Gap (Strategic Analysis 2025-01-12)

**First Observed:** 2025-01-12 (CI strategy analysis)
**Frequency:** 80% of CI failures driven by reactive mock patching
**Strategic Impact:** 17+ modules import get_mistral_client, only 5 patched initially
**Enforcement Mechanism:** `scripts/validate-mock-coverage.py` validates all imports before commit

### Symptoms

- `Unit test attempted to call Mistral API!` in test output (fixture protection triggered)
- Test timeout (>120s) after external API blocking fixture runs
- Specific modules like `enrichment.py`, `anomaly_detection.py` escape mock coverage
- 80% CI fix rate despite core mock fixtures in place (reactive patching pattern)
- New code adding `get_mistral_client` imports causes immediate test timeout failures
- Different behavior between old tests (patched) and newly written tests (unpatched)

### Root Cause (Five Whys)

1. **Why do tests timeout?** → External API calls execute (Mistral API requests)
2. **Why aren't they mocked?** → Lazy imports inside function bodies execute at test runtime
3. **Why use lazy imports?** → Avoid circular imports, defer module loading until needed
4. **Why do patches miss locations?** → 17+ modules import get_mistral_client, only 5 manually patched
5. **Why no structural prevention?** → No validation that all import locations are patched before tests run

### Solution Applied

- Created `scripts/validate-mock-coverage.py` to automatically detect unpatched import locations
- Script scans all `raglite/` modules for `get_mistral_client` imports
- Compares against patches in `tests/fixtures/mock_clients.py`
- Reports gaps with actionable fix suggestions
- Exit code allows use as pre-commit hook (blocks commits with gaps)
- Added 12+ new patches to `tests/fixtures/mock_clients.py` (session fixture now covers all locations)

### Verification

```bash
# Validate mock coverage
python scripts/validate-mock-coverage.py

# Should output: ✅ Mock coverage validation PASSED
# (or show gaps that need fixing before commit)

# Detailed report
python scripts/validate-mock-coverage.py --verbose

# Run unit tests with short timeout (fails fast if API calls happen)
uv run pytest tests/unit/ -v --timeout=10
# Should all pass in <3 seconds (no timeouts)
```

### Prevention

**1. Automated Validation (Pre-commit)**
- Script blocks commits if gaps found
- Runs before every `git commit`
- Provides exact patch lines needed

**2. Code Review Checklist**
- When adding code with `get_mistral_client`:
  - [ ] Run `python scripts/validate-mock-coverage.py`
  - [ ] Add patch to `tests/fixtures/mock_clients.py` if needed
  - [ ] Unit tests complete in <3 seconds
  - [ ] Validation passes in CI

**3. Pattern for New Code**
```python
# Import at function level (lazy)
def my_function():
    from raglite.shared.clients import get_mistral_client
    client = get_mistral_client()
    # ...

# Then add patch to tests/fixtures/mock_clients.py
# Then verify: python scripts/validate-mock-coverage.py
```

### Related Documentation

- **Comprehensive Guide:** `docs/ci-knowledge/mock-coverage-pattern.md` (detailed walkthrough)
- **Runbook:** `docs/ci-failure-runbook.md` → Section 18 (Lazy Import Mock Coverage Gap)
- **Validation Script:** `scripts/validate-mock-coverage.py` (automation)
- **Fixture Locations:** `tests/fixtures/mock_clients.py` (patch definitions)
- **CI Strategy:** `docs/ci-strategy.md` → Mock Coverage section
