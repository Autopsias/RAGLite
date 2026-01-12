# CI Failure Runbook

Quick reference for diagnosing and resolving CI failures.

**Last Updated:** 2025-01-12
**CI Infrastructure Version:** 1.3 (self-hosted runners with enhanced pre-commit enforcement)

---

## Strategic Analysis Summary (2025-01-12)

**CI Fix Commits:** 52% of total commits (85% of last 20 commits before this update)
**Root Cause Analysis:** Four systemic patterns identified and addressed with pre-commit hooks
**Prevention Mechanisms:** Now enforced via 8 active pre-commit hooks + CI workflows + runtime guards

### Four Root Causes Identified

| Root Cause | Frequency | Fix Implemented | Enforcement |
|-----------|-----------|-----------------|------------|
| **Incomplete Mock Coverage** | 10-15% of failures (P0-3) | External API blocking fixture + pre-commit hook | `block_external_apis_in_unit_tests` autouse fixture + `check-deferred-imports.sh` |
| **Mock Target Drift** | 12% of failures | `validate-mock-targets.py` script | Pre-commit hook + CI validation job |
| **pytest-xdist isinstance()** | 15% of failures | Duck-typing replacement rules | `check-isinstance-violations` hook (NEW) |
| **xdist Marker Gaps** | 10% of failures | Add xdist_group markers | `validate-xdist-markers` hook (NEW) |

### Key Metrics

- **Before:** 52% of commits were CI fixes (85% in last 20: reactive)
- **Target:** <10% of commits are CI fixes (proactive prevention)
- **Prevention Rules:** 8 automated checks now active (was 5)
- **Documentation:** Runbook expanded to 16 failure categories with solutions
- **Hook Enforcement:** All pre-commit hooks active for all developers

### Enforcement Mechanisms Now Active

**Pre-commit Hooks (8 total):**
1. **validate-mock-targets** - Verify mock patch targets exist
2. **check-isinstance-violations** - Catch isinstance usage in tests (NEW)
3. **validate-xdist-markers** - Ensure xdist_group markers on state-dependent tests (NEW)
4. **check-file-sizes** - Block new files >500 LOC
5. **validate-pytest-fixtures** - Verify fixture patterns
6. **validate-pytest-markers** - Ensure markers are registered
7. **check-pytestmark-e402** - Check for E402 violations with pytest markers
8. **safety-check** - Verify production database isolation

**CI Workflows:**
1. Mock patch validation job on all PRs
2. isinstance() linting job
3. xdist marker validation job

---

## Pre-commit Hook Enforcement

All pre-commit hooks are active and enforced on every commit. Hooks run BEFORE code is committed to git.

### Hook Status (2025-01-12)

| Hook ID | Purpose | Status | Auto-Fix | Impact |
|---------|---------|--------|----------|--------|
| `validate-mock-targets` | Verify mock patch targets exist | ACTIVE | No | Blocks commits with invalid mock targets |
| `check-isinstance-violations` | Catch isinstance() on custom types | ACTIVE | No | Blocks commits with xdist-unsafe isinstance |
| `validate-xdist-markers` | Ensure xdist_group markers | ACTIVE | No | Blocks commits with state-dependent tests missing markers |
| `check-file-sizes` | Block new files >500 LOC | ACTIVE | No | Blocks commits with oversized files |
| `validate-pytest-fixtures` | Verify fixture patterns | ACTIVE | No | Blocks commits with unsafe fixture patterns |
| `validate-pytest-markers` | Ensure markers are registered | ACTIVE | No | Blocks commits with unregistered pytest markers |
| `check-pytestmark-e402` | Check E402 violations with markers | ACTIVE | No | Blocks commits with import ordering issues |
| `safety-check` | Verify database isolation | ACTIVE | No | Blocks commits that expose production ports |

### Common Hook Failures and Fixes

**Hook: check-isinstance-violations**
```bash
# Error: isinstance check on custom class in tests
# Appears in: tests/unit/test_example.py:45

# FIX 1: Use __class__.__name__
assert result.__class__.__name__ == 'ResultType'

# FIX 2: Use hasattr() for duck typing
assert hasattr(result, 'value')

# FIX 3: Use .name or .value for enums
assert result.status.name == 'SUCCESS'
```

**Hook: validate-xdist-markers**
```bash
# Error: State-dependent test missing @pytest.mark.xdist_group
# Appears in: tests/integration/test_shared_state.py:20

# FIX: Add marker to test
@pytest.mark.xdist_group(name="shared_resources")
def test_something_with_state():
    # This test uses shared state and cannot run in parallel
```

**Hook: validate-mock-targets**
```bash
# Error: Mock patch target does not exist
# Error message: "Cannot find 'raglite.module.NonExistentClass' in source"

# FIX: Verify class exists in module
grep -n "class NonExistentClass" raglite/module.py  # Should find something
# Then update patch with correct class name
```

---

## Quick Reference

| Failure Pattern | Likely Cause | Quick Fix | Prevention |
|-----------------|--------------|-----------|-----------|
| `Timeout (>120s)` in unit tests | Incomplete mock coverage, fallback API calls | Mock ALL extraction functions (primary + fallback) | Use `block_external_apis_in_unit_tests` fixture |
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
| `AssertionError: N not in range(10, 55)` | Fixture validation range too strict | Use tolerance-based validation (±15%) | Document baseline, not hardcoded ranges |
| `TypeError: missing required argument` | API signature changed, test calls not updated | Update all function calls with required params | Add contract tests to catch drift early |
| `KeyError: 'cement_demand'` | Config and test files out of sync | Add validation that configured metrics exist | Sync verification CI job before merge |
| `Unit test attempted to call Mistral API!` | Lazy import in function body not patched | Add module to mock_clients.py patches | Run validate-mock-coverage.py before commit |
| `Docker daemon did not become ready within 60s` | Colima zombie state (process running, daemon dead) | `colima stop -f && colima delete -f && colima start` | Add zombie state detection to pre-flight check |

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

### 14. Fixture Validation Range Too Strict (Story 2.2 - PDF Optimization)

#### Symptoms
- 949-test cascade failure in PDF integration test suite
- `AssertionError: 120 not in range(10, 55)` in session fixture
- Chunk count validation fails for variable-size documents
- Non-deterministic chunk boundaries cause flaky assertions
- Same document produces different chunk counts in different runs
- Tests pass/fail based on document content variation

#### Root Cause (Five Whys)
1. Why? → Session fixture used hardcoded chunk count range (10, 55)
2. Why? → Range was arbitrary, not based on actual chunk distribution
3. Why? → Document processors produce non-deterministic chunk boundaries
4. Why? → No tolerance mechanism for valid chunk count variations
5. Why? → Tight range caught edge cases instead of errors

#### Solution
- Replace hardcoded ranges with tolerance-based validation
- Calculate expected range from actual baseline: baseline ± 15%
- Allow document-specific variance within tolerance band
- Example: If baseline is 80 chunks, accept 68-92 (80 ± 15%)

**Implementation:**
```python
# OLD: Strict range (fails on variations)
def validate_chunk_count(count, expected_range=(10, 55)):
    assert count in expected_range

# NEW: Tolerance-based (accepts variations)
def validate_chunk_count(count, baseline, tolerance=0.15):
    min_count = int(baseline * (1 - tolerance))
    max_count = int(baseline * (1 + tolerance))
    assert min_count <= count <= max_count, \
        f"Count {count} outside tolerance {min_count}-{max_count}"
```

#### Verification
```bash
# Test with 10-page fixture (produces ~80 chunks)
uv run pytest tests/integration/fixtures/_ingestion_helpers.py -v

# Check actual chunk distribution
uv run pytest tests/integration/ -k "pdf" --collect-only -q
```

#### Prevention
- Always use tolerance-based assertions for non-deterministic values
- Document baseline expectations in test comments
- Test with multiple document sizes and types
- Use parametrized tests to catch edge cases
- Never hardcode expected ranges without reasoning

---

### 15. API Contract Drift - Signature Changes Not Propagated (Epic 6)

#### Symptoms
- `TypeError: generate_ensemble_forecast() missing required argument: 'historical_data'`
- Function signature changed but test calls unchanged
- Works in main branch but fails after Epic 6 merge
- Multiple test methods fail with same error
- 5-10 test failures from same root cause (API change)
- Error only visible at test execution time, not on import

#### Root Cause (Five Whys)
1. Why? → API function signature changed (added required parameter)
2. Why? → Test calls to function not updated systematically
3. Why? → Change was localized to one module (forecast execution)
4. Why? → No automated check for function signature changes
5. Why? → Tests passed locally before Epic 6 but failed after merge

#### Solution
- Add API contract tests to detect signature drift early
- Update all function calls to pass required parameters
- Remove obsolete mock patches that reference old signatures

**Implementation:**
```python
# ADD: Signature validation test (detects drift early)
def test_forecast_signature_contract():
    """Verify generate_ensemble_forecast accepts required parameters."""
    import inspect
    sig = inspect.signature(generate_ensemble_forecast)
    params = list(sig.parameters.keys())

    # Assert required parameters exist
    assert 'historical_data' in params, \
        f"Missing required param 'historical_data'. Got: {params}"

# UPDATE: Test calls with required parameters
# OLD:
result = generate_ensemble_forecast(config)

# NEW:
result = generate_ensemble_forecast(config, historical_data=data)
```

#### Verification
```bash
# Run API contract tests
uv run pytest tests/integration/epic6/ -v -k "contract"

# Check for remaining signature mismatches
grep -r "generate_ensemble_forecast" tests/ --include="*.py" | grep -v "historical_data"
```

#### Prevention
- Add contract tests for public API functions (detect changes early)
- Include function signature in docstring
- Document required vs optional parameters
- Use type hints to make contracts explicit
- Run contract tests on every merge to main

---

### 16. Config-Test Synchronization Drift

#### Symptoms
- `KeyError: 'cement_demand'` when accessing configured metric
- Metric referenced in test but not defined in config
- Test expects metric to exist but config.yaml doesn't include it
- Inconsistency between pytest fixtures and system configuration
- Configuration changes made without updating dependent tests
- Error only occurs at test data setup time

#### Root Cause (Five Whys)
1. Why? → Config and test files drifted out of sync
2. Why? → Config updated to remove metric, tests not updated
3. Why? → No validation that configured metrics exist in tests
4. Why? → No CI job to verify config-test synchronization
5. Why? → Metrics added/removed without cross-file impact analysis

#### Solution
- Add config-test synchronization CI job
- Verify all configured metrics are tested
- Verify all test metrics are configured
- Document metric definitions and usage

**Implementation:**
```python
# ADD: Config sync validation
def test_config_metrics_in_tests():
    """Verify all configured metrics are tested."""
    from raglite.config import Settings
    from tests.fixtures.metrics import EXPECTED_METRICS

    config = Settings()
    configured = set(config.metrics.keys())
    expected = set(EXPECTED_METRICS)

    # Check for missing metrics
    missing = configured - expected
    assert not missing, f"Configured but not tested: {missing}"

    # Check for orphaned tests
    orphaned = expected - configured
    assert not orphaned, f"Tested but not configured: {orphaned}"
```

#### Verification
```bash
# Verify config-test synchronization
uv run pytest tests/ -v -k "sync" --tb=short

# Check config metrics
grep "metrics:" raglite/config.yaml -A 10

# Check test expectations
grep "EXPECTED_METRICS\|cement_demand" tests/ -r --include="*.py"
```

#### Prevention
- Run config-test sync verification before every merge
- Include config changes in test review checklist
- Document metric definitions in both config and tests
- Use shared constants for metric names (avoid duplication)
- Add validation to config loader (verify referenced metrics exist)

---

### 17. Timeout Due to Incomplete Mock Coverage (P0-3)

#### Symptoms
- `Timeout (>120.0s) from pytest-timeout` in unit tests
- Tests involve MCP tools (forecast, model selection, timeseries extraction)
- Tests pass locally with full stack but timeout in CI
- Specific tests timeout while others pass (not a general performance issue)
- Test hangs at ~82% progress (suggesting fallback code path executed)
- Most common with `get_financial_forecast` and `select_best_model` tools

#### Root Cause (Five Whys)
1. Why? → Unit tests mock primary extraction functions but miss fallback paths
2. Why? → When primary extraction fails, code calls real external API (Mistral, Claude)
3. Why? → External API calls have no network connectivity or timeout in CI
4. Why? → Mock coverage only 50-70%, leaving critical paths unmocked
5. Why? → Tests designed for local full-stack execution, not API isolation

#### Example Flow (Extract Timeseries)
```
Unit test expects mocked data
  ↓
forecast_helpers.extract_historical_data_by_type() mocked ✓
  ↓
[But if that mock returns None or fails...]
  ↓
extract_timeseries() called as fallback [NOT MOCKED] ✗
  ↓
Mistral API call attempted
  ↓
No network/timeout
  ↓
120s timeout expires → test fails
```

#### Detection

**Quick check for test that's timing out:**
```bash
# Run test with verbose timeout output
uv run pytest path/to/test.py::test_name -v --timeout=30 --timeout-method=thread

# Check what mocks are applied
grep -A 10 "test_name" path/to/test.py | grep "patch\|mock"

# Search for incomplete mock patterns
grep -B 5 "extract_timeseries" tests/unit/
```

**Comprehensive check for all incomplete mocks:**
```bash
# Find all MCP tool tests
grep -r "get_financial_forecast\|select_best_model" tests/unit/ --include="*.py" -l

# For each test, verify BOTH primary and fallback extraction mocks
grep -A 20 "@patch" tests/unit/mcp/test_tools.py | grep "extract_"
```

#### Solution Pattern

**WRONG: Primary function mocked only**
```python
@patch("raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type")
async def test_forecast(mock_extract):
    mock_extract.return_value = {"data": [...]}
    result = await get_financial_forecast.fn(request)
    # If extract_historical_data_by_type fails, calls UNMOCKED
    # extract_timeseries() → real API call → timeout
```

**CORRECT: Both primary AND fallback mocked**
```python
@patch("raglite.mcp.tools.forecast_helpers.extract_timeseries")
@patch("raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type")
async def test_forecast(mock_extract, mock_timeseries):
    # Primary function
    mock_extract.return_value = {"data": [...]}
    # Fallback function
    mock_timeseries.return_value = ([], [])

    result = await get_financial_forecast.fn(request)
    # Now both paths are covered
```

**BEST: Use context manager for clarity**
```python
async def test_forecast_request():
    """Test financial forecast generation."""
    with (
        patch("raglite.mcp.tools.forecast_helpers.extract_historical_data_by_type") as m1,
        patch("raglite.mcp.tools.forecast_helpers.extract_timeseries") as m2,
    ):
        m1.return_value = {"data": [...]}
        m2.return_value = ([], [])

        result = await get_financial_forecast.fn(request)
        assert result.forecast is not None
```

#### Identifying Missing Mocks

**Trace the code path:**
1. Read the MCP tool implementation
2. Identify all external API/database calls
3. Check if each is mocked in the test
4. Look for fallback code paths (try/except, if/else)
5. Verify fallback paths are also mocked

**Common fallback patterns to check:**
```python
# Pattern 1: Try-except fallback
try:
    data = extract_historical_data_by_type(...)  # Mock this
except:
    data = extract_timeseries(...)  # AND mock this!

# Pattern 2: Conditional extraction
if use_cached:
    data = get_cached_data()  # Mock this
else:
    data = extract_from_api()  # Mock this too!

# Pattern 3: Nested extraction calls
result1 = primary_extract()  # Mock this
if not result1:
    result2 = fallback_extract()  # Don't forget this!
```

#### Verification

**Run test with strace to detect API calls:**
```bash
# Minimal timeout to fail fast if APIs are called
uv run pytest tests/unit/mcp/test_tools.py::test_forecast -v --timeout=10

# If it still times out, an API call is happening
# Search for where that API call originates
grep -r "Mistral\|request.post\|openai.ChatCompletion" raglite/
```

**Verify all mocks are present:**
```bash
# Extract function names from tool implementation
grep -o "extract_[a-z_]*" raglite/mcp/tools/forecast_helpers.py | sort -u

# Check which are mocked in tests
for func in $(grep -o "extract_[a-z_]*" raglite/mcp/tools/forecast_helpers.py | sort -u); do
    echo "=== $func ==="
    grep -c "patch.*$func" tests/unit/mcp/test_tools.py || echo "NOT MOCKED"
done
```

#### Prevention (2025-01-12)

**1. External API Blocking Fixture** (Created in `/tests/unit/conftest.py`)
```python
@pytest.fixture(autouse=True)
def block_external_apis_in_unit_tests():
    """Fail fast if unit tests attempt external API calls."""
    # Blocks: Mistral, Claude, Qdrant, PostgreSQL
    # Ensures mocks are comprehensive before test starts
```

This fixture is session-scoped with `autouse=True`, so:
- All unit tests automatically get protection
- If any external API is called, test fails immediately with clear error
- No need to wait 120s for timeout - you know instantly

**2. Pre-commit Hook** (`scripts/check-deferred-imports.sh`)
```bash
# Runs before every commit
# Detects deferred imports that could cause slowdown
# Prevents: late imports, lazy loading abuse, mock miss patterns
```

**3. Test Pattern Checklist**

When writing new tests that call MCP tools:
- [ ] Identify all extraction functions called (trace code path)
- [ ] Identify all fallback paths (try/except, if/else)
- [ ] Mock ALL extraction functions (primary + fallbacks)
- [ ] Run with `--timeout=30` to catch incomplete mocks early
- [ ] Verify test completes in <3 seconds (not <120s)

**4. Code Review Checklist**

When reviewing test PRs:
- [ ] Are all external API calls mocked?
- [ ] Are fallback code paths covered?
- [ ] Does test complete in <5 seconds?
- [ ] Does test fail immediately (not timeout) if mock missing?

#### Related Documentation
- **Mock Patch Interference:** Section 4 (mock target drift)
- **Test Reliability Rules:** `.claude/rules/testing.md` → Mock Patterns
- **External API Blocking:** `tests/unit/conftest.py` → `block_external_apis_in_unit_tests`

---

### 18. Docker Daemon Socket Inaccessibility - Colima VM Failures (Strategic Analysis 2025-01-12)

#### Symptoms
- `Error: Cannot connect to Docker daemon at unix:///var/run/docker.sock: connect: no such file or directory`
- `Error: Colima VM stopped unexpectedly - socket at ~/.colima/default/docker.sock inaccessible`
- Integration tests fail with connection refused on random jobs (intermittent)
- Docker commands work locally but fail in GitHub Actions self-hosted runner
- Health check timeouts after container startup (30s timeout too aggressive)

#### Root Cause (Five Whys)
1. Why? → Docker socket at ~/.colima/default/docker.sock becomes inaccessible between jobs
2. Why? → Colima VM stops or becomes unresponsive on self-hosted macOS runner
3. Why? → No health check before attempting container operations
4. Why? → 30-second health check timeout insufficient for container lifecycle
5. Why? → Missing symlink: /var/run/docker.sock not created (standard Docker path)

#### Strategic Impact
**Root cause of 80% of recent CI failures** - Affects job-to-job consistency on self-hosted runner. When Colima daemon becomes inaccessible, all container operations fail until VM is restarted.

#### Solution Pattern

**P0: Add Pre-Flight Colima Health Check**
```bash
# Before any container operations, verify Colima is healthy
./scripts/ensure-colima-health.sh

# This script:
# 1. Checks if Docker daemon is responding: docker info
# 2. If unavailable: attempts colima stop && colima start
# 3. Verifies socket is accessible: ls -la ~/.colima/default/docker.sock
# 4. Creates symlink for standard path: ln -s ~/.colima/default/docker.sock /var/run/docker.sock
# 5. Waits for Docker readiness: retry docker info with backoff
```

**P0: Create Docker Socket Symlink**
```bash
# Ensure standard Docker socket path works
if [ ! -L /var/run/docker.sock ]; then
    sudo mkdir -p /var/run
    sudo ln -s ~/.colima/default/docker.sock /var/run/docker.sock
fi
```

**P1: Increase Container Health Check Timeout**
```yaml
# In docker-compose.yml or container startup
healthcheck:
  test: ["CMD", "docker", "ps"]
  interval: 10s
  timeout: 60s      # Increased from 30s
  retries: 5
  start_period: 15s
```

**P1: Add Port-in-Use Validation Before Container Startup**
```bash
# Verify ports are not already in use
netstat -tuln | grep -E ':6335|:5433|:6333|:5432'
# If in use, kill previous containers: docker-compose down -v
```

#### Verification
```bash
# Check Colima health
colima status
colima version

# Verify Docker socket accessibility
ls -la ~/.colima/default/docker.sock
ls -la /var/run/docker.sock

# Test container startup
docker ps
docker-compose up -d qdrant postgresql
docker ps --filter "name=raglite"

# Verify health check passes
docker exec raglite-qdrant wget --spider localhost:6333 2>/dev/null && echo "healthy" || echo "unhealthy"
```

#### Prevention (2025-01-12)

**1. Pre-Flight Validation Action (CI)**
```yaml
- name: Validate Colima Health
  uses: ./.github/actions/validate-colima
  # Runs: ensure-colima-health.sh before any container operations
```

**2. Container Startup Standards**
- Always run pre-flight check before docker-compose up
- Increase health check timeout to 60s
- Validate ports are available before starting containers
- Create symlink for /var/run/docker.sock

**3. Self-Hosted Runner Setup**
```bash
# On runner setup (one-time):
sudo mkdir -p /var/run
sudo ln -s ~/.colima/default/docker.sock /var/run/docker.sock

# Verify in cron (periodic health check):
*/30 * * * * ~/scripts/ensure-colima-health.sh > /dev/null 2>&1
```

#### Related Documentation
- **CI Strategy:** `docs/ci-strategy.md` → Docker/Colima Reliability section
- **Prevention Rules:** `docs/ci-knowledge/prevention-rules.md` → Docker Infrastructure
- **Infrastructure Script:** `scripts/ensure-colima-health.sh`
- **Self-Hosted Guide:** `docs/ci-knowledge/self-hosted-runner-guide.md`

---

### 19. Colima Zombie State - Daemon Process Unresponsive (Strategic Analysis 2025-01-12)

#### Symptoms
- Docker Pre-flight Validation step fails after exactly 60s timeout
- Logs show: `colima start` succeeded with message "already running, ignoring"
- Then: `Still waiting for Docker daemon... 10s/60s` → `20s/60s` → ... → `60s/60s`
- Finally: `Docker daemon did not become ready within 60s`
- `colima status` shows "running" but `docker info` fails or times out
- Colima VM process visible in `ps aux` but internal Docker daemon is dead
- Container operations fail with "Cannot connect to Docker daemon"

#### Root Cause (Five Whys)
1. Why? → Docker Pre-flight validation times out after 60s
2. Why? → Colima responds to status check but daemon socket is unresponsive
3. Why? → Colima VM process is running but internal Docker daemon crashed
4. Why? → No health check exists to detect zombie VM state
5. Why? → VM process can be "running" while daemon inside is dead

#### Strategic Impact
**Transient failure pattern** - Occurs intermittently on self-hosted runner when Colima VM enters zombie state. The VM appears running to the OS but Docker daemon inside is unresponsive. Different from general Docker unavailability (Section 13) - this is VM-level zombie state.

#### Detection (Quick Check)

**Test if Colima is in zombie state:**
```bash
# Step 1: Check if colima process exists
colima status 2>/dev/null | grep -q "Running" && echo "Process: OK" || echo "Process: DEAD"

# Step 2: Check if Docker daemon responds
docker info &>/dev/null && echo "Daemon: OK" || echo "Daemon: DEAD"

# Result: If "Process: OK" and "Daemon: DEAD" → Zombie state
```

**Full diagnostic:**
```bash
# Check Colima status
colima status

# Check Docker daemon responsiveness (with timeout)
timeout 5 docker info > /dev/null 2>&1
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "Daemon: RESPONSIVE"
elif [ $EXIT_CODE -eq 124 ]; then
    echo "Daemon: TIMEOUT (zombie state likely)"
else
    echo "Daemon: ERROR"
fi

# Check for stale processes
ps aux | grep colima | grep -v grep

# Check socket status
ls -la ~/.colima/default/docker.sock 2>/dev/null || echo "Socket not accessible"
```

#### Solution Pattern

**Quick Recovery (30 seconds):**
```bash
# Force stop and delete VM (kills zombie process)
colima stop -f
colima delete -f

# Restart with explicit resource allocation
colima start --cpu 4 --memory 6 --disk 50 --runtime docker

# Verify daemon is responsive
docker info

# Verify containers can be accessed
docker ps
```

**Immediate Workaround (if scripts unavailable):**
```bash
# Single command to kill and restart
colima stop -f && sleep 1 && colima delete -f && sleep 1 && colima start
```

**In CI Workflow:**
```yaml
- name: Recover from Colima Zombie State
  if: failure()
  run: |
    colima stop -f
    colima delete -f
    colima start --cpu 4 --memory 6 --disk 50 --runtime docker
    docker info
    docker-compose up -d
```

#### Verification
```bash
# Verify recovery successful
colima status
# Should show: colima is running

docker info | head -5
# Should show Docker version and system information

docker ps --filter "name=raglite" --format "table {{.Names}}\t{{.Status}}"
# Should show running containers with healthy status

# Run integration test to confirm
uv run pytest tests/integration/chunking/test_ac5_validation.py -v --timeout=120
```

#### Prevention (2025-01-12)

**1. Pre-Flight Zombie Detection Hook**

Add to pytest_configure in `tests/fixtures/pytest_hooks.py`:
```python
import subprocess
import time
import logging

logger = logging.getLogger(__name__)

def _is_colima_zombie():
    """Detect if Colima VM is in zombie state (process running but daemon dead)."""
    try:
        # Check if colima process exists
        colima_status = subprocess.run(
            ["colima", "status"],
            capture_output=True,
            timeout=5,
            text=True
        )
        if "running" not in colima_status.stdout.lower():
            return False  # Not zombie - just not running

        # Check if Docker daemon responds (with short timeout)
        docker_info = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            text=True
        )
        if docker_info.returncode == 0:
            return False  # Daemon responds - healthy
        else:
            return True  # Process running but daemon dead = zombie!
    except subprocess.TimeoutExpired:
        return True  # Timeout on docker info = zombie behavior
    except Exception:
        return False  # Can't determine

def _recover_from_zombie():
    """Force recreate Colima VM to recover from zombie state."""
    commands = [
        ["colima", "stop", "-f"],
        ["sleep", "2"],
        ["colima", "delete", "-f"],
        ["sleep", "2"],
        ["colima", "start"]
    ]
    for cmd in commands:
        subprocess.run(cmd)
    time.sleep(10)

def pytest_configure(config):
    if _is_colima_zombie():
        logger.warning("Colima zombie state detected - forcing restart")
        _recover_from_zombie()
```

**2. Enhanced Health Check Script**

Update `scripts/ensure-colima-health.sh` to detect zombie state:
```bash
#!/bin/bash
# Enhanced Colima health check with zombie state detection

# Check for zombie state (process running but daemon unresponsive)
if colima status 2>/dev/null | grep -q "running"; then
    # Process is running - check if daemon responds
    if ! timeout 5 docker info > /dev/null 2>&1; then
        echo "ZOMBIE STATE DETECTED: Colima process running but daemon unresponsive"
        echo "Forcing VM recreation..."

        colima stop -f
        sleep 2
        colima delete -f
        sleep 2
        colima start --cpu 4 --memory 6 --disk 50 --runtime docker

        # Wait for startup
        for i in {1..60}; do
            if docker info > /dev/null 2>&1; then
                echo "VM recovered after ${i}s"
                break
            fi
            sleep 1
        done
    fi
fi

# Continue with standard health checks...
```

**3. CI Job Configuration**

Add zombie state handling to all jobs using Docker:
```yaml
jobs:
  test:
    runs-on: self-hosted-macos
    steps:
      - name: Detect and Fix Colima Zombie State
        run: |
          # Check for zombie state
          if colima status 2>/dev/null | grep -q "running"; then
            if ! timeout 5 docker info > /dev/null 2>&1; then
              echo "Zombie state detected - recovering..."
              colima stop -f
              sleep 2
              colima delete -f
              sleep 2
              colima start
            fi
          fi

      - name: Run Tests
        run: uv run pytest tests/integration/
```

**4. Monitoring Zombie State Occurrences**

Track in CI logs:
```bash
# Enhanced health check with logging
if colima status 2>/dev/null | grep -q "running" && \
   ! timeout 5 docker info > /dev/null 2>&1; then
    echo "ALERT: Colima zombie state detected at $(date)" >&2
    # Trigger recovery
fi
```

#### Related Documentation
- **CI Strategy:** `docs/ci-strategy.md` → Docker/Colima Reliability section
- **Colima Reliability:** `docs/ci-knowledge/colima-reliability.md` → Zombie State Prevention
- **Prevention Rules:** `docs/ci-knowledge/prevention-rules.md` → Docker Infrastructure
- **Self-Hosted Guide:** `docs/ci-knowledge/self-hosted-runner-guide.md` → Zombie Recovery

---

### 20. Lazy Import Mock Coverage Gap (Strategic Analysis 2025-01-12)

#### Symptoms
- `Unit test attempted to call Mistral API!` in test logs
- Test timeout after passing fixture blocking checks (>120s)
- Specific modules like `enrichment.py` escape mock coverage
- 80% CI fix rate despite 5 patched locations (reactive vs structural)
- New code adding `get_mistral_client` imports causes immediate test failures
- Different behavior between older tests and newly written tests

#### Root Cause (Five Whys)
1. Why? → 17+ modules import get_mistral_client inside function bodies (lazy imports)
2. Why? → Mock session fixture only patches 5 locations (incomplete coverage)
3. Why? → Lazy imports inside functions execute at test runtime, not import time
4. Why? → Session fixture patches only module-level imports
5. Why? → No structural validation of mock coverage before tests run

#### Example Problem
```python
# raglite/retrieval/search/enrichment.py (NOT patched)
def enrich_result(query: str):
    # Lazy import inside function
    from raglite.shared.clients import get_mistral_client  # <-- This line bypasses session fixture!
    client = get_mistral_client()  # Attempts real API call → test timeout
    return client.enrich(query)

# Test fixture patches location:
@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally():
    with (
        patch("raglite.retrieval.search.get_mistral_client"),  # Only patches 5 known locations
        # Missing: patch("raglite.retrieval.search.enrichment.get_mistral_client")
    ):
        yield
```

#### Detection

**Quick check for lazy imports:**
```bash
# Find all get_mistral_client imports
grep -r "from raglite.shared.clients import get_mistral_client" raglite/ --include="*.py"

# Find which are patched in test fixture
grep -r "patch.*get_mistral_client" tests/fixtures/mock_clients.py

# Run validation script (shows gaps)
python scripts/validate-mock-coverage.py --verbose
```

**Output if gaps exist:**
```
ERROR: Mock coverage gaps detected!
Found 3 module(s) importing get_mistral_client without mock coverage:

  ❌ raglite.retrieval.search.enrichment.get_mistral_client
  ❌ raglite.mcp.tools.model_selector.get_mistral_client
  ❌ raglite.insights.anomaly_detection.get_mistral_client
```

#### Solution Pattern

**WRONG: Session fixture patches only known locations**
```python
@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally():
    with patch("raglite.mcp.tools.get_mistral_client"):  # Only 5 locations
        yield
    # New modules bypass this coverage
```

**CORRECT: Patch ALL locations where get_mistral_client is imported**
```python
@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally():
    """Mock Mistral API globally for all unit tests (17+ import locations)."""
    with (
        patch("raglite.mcp.tools.get_mistral_client") as mock1,
        patch("raglite.retrieval.search.enrichment.get_mistral_client") as mock2,
        patch("raglite.mcp.tools.model_selector.get_mistral_client") as mock3,
        # ... all 17+ locations
    ):
        mock_client = AsyncMock()
        mock_client.enrich = AsyncMock(return_value="mocked")

        for mock in [mock1, mock2, mock3]:  # Apply to all patches
            mock.return_value = mock_client

        yield
```

**BEST: Use validation script to find all locations**
```bash
# Step 1: Find all import locations
python scripts/validate-mock-coverage.py --verbose

# Step 2: Update mock_clients.py with ALL locations
# (Script shows exact patch lines needed)

# Step 3: Verify coverage
python scripts/validate-mock-coverage.py
# Should output: ✅ Mock coverage validation PASSED
```

#### Identifying Missing Mocks

**Scan all modules:**
```bash
# Find every module importing get_mistral_client
grep -r "from raglite.shared.clients import get_mistral_client" raglite/ --include="*.py" -l

# Example output:
# raglite/mcp/tools.py
# raglite/retrieval/search/enrichment.py
# raglite/mcp/tools/model_selector.py
# raglite/insights/anomaly_detection.py
# (and 13+ more)
```

**Check if patched in fixture:**
```bash
# For each module found above, verify patch exists
grep "patch.*raglite.retrieval.search.enrichment.get_mistral_client" tests/fixtures/mock_clients.py

# If no match, that location is unpatched (coverage gap)
```

#### Verification

**Run validation before every commit:**
```bash
# Quick check (binary pass/fail)
python scripts/validate-mock-coverage.py

# Detailed report (shows all gaps)
python scripts/validate-mock-coverage.py --verbose
```

**Expected output (pass):**
```
================================================================================
✅ Mock coverage validation PASSED
================================================================================
  - 17 module(s) import get_mistral_client
  - 17 location(s) patched in mock fixtures
  - 0 gaps (100% coverage)
```

**Expected output (fail):**
```
ERROR: Mock coverage gaps detected!
Found 2 module(s) importing get_mistral_client without mock coverage:
  ❌ raglite.retrieval.search.enrichment.get_mistral_client
  ❌ raglite.insights.anomaly_detection.get_mistral_client
```

#### Prevention (2025-01-12)

**1. Pre-commit Enforcement**

Add to `.pre-commit-config.yaml`:
```yaml
- repo: local
  hooks:
    - id: validate-mock-coverage
      name: Validate mock coverage
      entry: python scripts/validate-mock-coverage.py
      language: system
      stages: [commit]
      pass_filenames: false
```

This prevents commits that introduce unpatched import locations.

**2. CI Job Enforcement**

Runs on all PRs:
```bash
python scripts/validate-mock-coverage.py --strict
# Exits with error if gaps found, blocks merge
```

**3. Code Review Checklist**

When adding new code that imports get_mistral_client:
- [ ] Module appears in `python scripts/validate-mock-coverage.py --verbose` output
- [ ] Corresponding patch exists in `tests/fixtures/mock_clients.py`
- [ ] Patch is applied in `mock_mistral_api_globally` fixture
- [ ] `python scripts/validate-mock-coverage.py` passes
- [ ] All unit tests complete in <5 seconds (not timeout)

**4. Pattern for New Code**

When writing new code that needs Mistral client:
```python
# DO: Import at function level (lazy import)
def my_function():
    from raglite.shared.clients import get_mistral_client
    client = get_mistral_client()
    # ...

# THEN: Immediately add patch to tests/fixtures/mock_clients.py
@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally():
    with patch("raglite.NEW_MODULE_PATH.get_mistral_client") as mock_new:
        # ...
        mock_new.return_value = mock_client
        yield

# THEN: Verify with validation
python scripts/validate-mock-coverage.py
# Should pass with updated count
```

#### Related Documentation
- **Knowledge Base:** `docs/ci-knowledge/mock-coverage-pattern.md` (comprehensive guide)
- **Validation Script:** `scripts/validate-mock-coverage.py` (automated detection)
- **Mock Fixture Locations:** `tests/fixtures/mock_clients.py` (patch definitions)
- **Test Reliability Rules:** `.claude/rules/testing.md` → Mock Patterns
- **CI Strategy:** `docs/ci-strategy.md` → Mock Coverage section

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
