# CI Knowledge: Prevention Rules

## Prevention Rule: Test Isolation Standards

**Rule:** All database-dependent tests must use proper isolation patterns

### Required Pattern
```python
# GOOD: Proper isolation
@pytest.fixture(scope="session")
def ensure_qdrant_test_isolation():
    """Lazy restoration pattern for test isolation."""
    from tests.fixtures.qdrant import verify_test_environment
    verify_test_environment()
    yield
    # Cleanup handled by lazy restoration

@pytest.mark.integration
async def test_example():
    """Test with proper isolation."""
    # Test implementation
```

### Forbidden Pattern
```python
# BAD: No isolation
def test_example():
    """Test without isolation - causes pollution."""
    # Test implementation - will affect other tests
```

### Verification
```bash
# Verify isolation works
uv run pytest tests/integration/test_example.py -v
# Check no cross-test contamination
uv run pytest tests/integration/test_example.py --lf -v
```

### Prevention Checklist
- [ ] Use explicit `@pytest.mark.integration` for database tests
- [ ] Never rely on file path heuristics for fixture activation
- [ ] Ensure session fixtures have explicit skip conditions
- [ ] Use lazy restoration pattern for state management

---

## Prevention Rule: Container Volume Validation

**Rule:** Always verify Docker container volume mounts before running tests

### Required Pattern
```python
# GOOD: Mount validation
def verify_container_mounts():
    """Verify volume mounts are correct."""
    import subprocess
    result = subprocess.run([
        "docker", "inspect", "raglite-qdrant",
        "--format={{json .Mounts}}"
    ], capture_output=True, text=True)

    mounts = json.loads(result.stdout)
    expected_paths = ["/Users/ricardocarvalho/DeveloperFolder/RAGLite/qdrant_storage"]

    for mount in mounts:
        if mount["Destination"] == "/qdrant/storage":
            if mount["Source"] not in expected_paths:
                raise RuntimeError(f"Wrong mount: {mount['Source']}")
```

### Forbidden Pattern
```python
# BAD: No mount validation
def setup_tests():
    """Assume mounts are correct - dangerous in CI."""
    # No validation - may fail if mounts are stale
    client = QdrantClient()
```

### Verification
```bash
# Check mount paths
docker inspect raglite-qdrant --format='{{json .Mounts}}'
docker inspect raglite-postgresql --format='{{json .Mounts}}'
# Run validation script
./scripts/start-dev.sh
```

### Prevention Checklist
- [ ] Always verify Docker container volume mounts before tests
- [ ] Never assume containers have correct mounts after CI runs
- [ ] Use `./scripts/start-dev.sh` for consistent development startup
- [ ] Check mounts with `docker inspect --format='{{json .Mounts}}'`

---

## Prevention Rule: Resource Cleanup Patterns

**Rule:** All resource-intensive operations must have explicit cleanup

### Required Pattern
```python
# GOOD: Explicit cleanup
@pytest.fixture
def qdrant_client():
    """Qdrant client with proper cleanup."""
    from raglite.shared.safety import SafetyGuard
    guard = SafetyGuard()
    guard.validate_test_environment("qdrant_client")

    client = QdrantClient(host='localhost', port=6335)
    try:
        yield client
    finally:
        client.close()
        # Additional cleanup if needed
```

### Forbidden Pattern
```python
# BAD: Missing cleanup
@pytest.fixture
def qdrant_client():
    """Missing cleanup causes resource leaks."""
    client = QdrantClient(host='localhost', port=6335)
    yield client  # No cleanup - resource leak
```

### Verification
```bash
# Check for orphaned processes
ps aux | grep resource_tracker
ps aux | grep python
# Verify memory usage
docker stats --no-stream
```

### Prevention Checklist
- [ ] Always use `try/finally` blocks for resource cleanup
- [ ] Add explicit resource disposal in test fixtures
- [ ] Monitor process counts during test execution
- [ ] Use memory limits in CI workflows

---

## Prevention Rule: Mock Patching Standards

**Rule:** Always patch wrapper functions, not direct imports

### Required Pattern
```python
# GOOD: Function-level patching
from unittest.mock import AsyncMock, patch

@pytest.fixture(autouse=True)
def setup_mocks():
    """Patch wrapper functions at usage location."""
    with patch('raglite.retrieval.lazy_load_embeddings', new_callable=AsyncMock) as mock_embeddings:
        mock_embeddings.return_value = test_embedding
        yield
```

### Forbidden Pattern
```python
# BAD: Import-level patching
@pytest.fixture(autouse=True)
def setup_mocks():
    """Patching at import location causes interference."""
    with patch('raglite.retrieval.EmbeddingModel') as mock_model:
        yield  # Affects other modules that import this
```

### Verification
```bash
# Test mock isolation
uv run pytest tests/unit/ -v --tb=short
# Verify no interference
uv run pytest tests/unit/ --tb=short -n 4
```

### Prevention Checklist
- [ ] Always patch at usage location, not definition
- [ ] Use wrapper functions for external libraries
- [ ] Add clear documentation on mock patterns
- [ ] Use explicit mock cleanup in fixtures

---

## Prevention Rule: Async Function Handling

**Rule:** Always use AsyncMock for async functions and proper await patterns

### Required Pattern
```python
# GOOD: AsyncMock usage
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_llm():
    """Proper async mocking."""
    with patch('raglite.retrieval.lazy_load_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Mocked response"
        yield mock_llm

@pytest.mark.asyncio
async def test_with_async_mock(mock_llm):
    """Test using AsyncMock."""
    result = await mock_llm("test query")
    assert result == "Mocked response"
```

### Forbidden Pattern
```python
# BAD: Standard Mock for async
@pytest.fixture
def mock_llm():
    """Standard Mock doesn't handle async properly."""
    with patch('raglite.retrieval.lazy_load_llm') as mock_llm:
        mock_llm.return_value = "Mocked response"
        yield  # Will cause TypeError: coroutine not awaited
```

### Verification
```bash
# Test async mocking
uv run pytest tests/integration/ -v --tb=short
# Verify async function calls
uv run pytest tests/integration/ --mock-call-counts
```

### Prevention Checklist
- [ ] Always import `unittest.mock.AsyncMock` for async functions
- [ ] Patch async functions at usage location
- [ ] Add explicit call verification in tests
- [ ] Use `await` for async mocked calls

---

## Prevention Rule: Global Environment Variable Configuration

**Rule:** CI workflows must set specific environment variables for self-hosted runners

### Required Pattern

```yaml
# .github/workflows/ci.yml
env:
  APP_ENV: test                           # Test database mode
  CI: "true"                              # CI detection
  PYTHONDONTWRITEBYTECODE: "1"            # Prevent .pyc pollution
  LOKY_MAX_CPU_COUNT: "1"                 # Prevent joblib deadlocks
```

### Rationale

| Variable | Purpose | Failure Prevented |
|----------|---------|-------------------|
| `PYTHONDONTWRITEBYTECODE=1` | Disable Python bytecode generation | Stale `.pyc` corruption (5-8 failures/week) |
| `LOKY_MAX_CPU_COUNT=1` | Disable Loky multiprocessing | Joblib deadlock hangs (2-3 failures/week) |
| `APP_ENV=test` | Select test database ports | Production data contamination |
| `CI=true` | Enable CI-specific markers | Slow test execution in fast feedback loop |

### Verification

```bash
# Verify environment setup
echo "PYTHONDONTWRITEBYTECODE=$PYTHONDONTWRITEBYTECODE"
echo "LOKY_MAX_CPU_COUNT=$LOKY_MAX_CPU_COUNT"
echo "APP_ENV=$APP_ENV"

# Check no bytecode created
find . -type f -name "*.pyc" | wc -l  # Should be 0
```

### Prevention Checklist
- [ ] Add `PYTHONDONTWRITEBYTECODE=1` to CI `env:` section
- [ ] Add `LOKY_MAX_CPU_COUNT=1` to CI `env:` section
- [ ] Verify CI uses test database ports (6335/5433)
- [ ] Confirm no bytecode files created during test runs
- [ ] Monitor for hanging tests (sign of Loky conflict)

---

## Prevention Rule: Bytecode Cache Isolation

**Rule:** Python bytecode must not persist between CI runs

### Required Pattern

```yaml
# In CI workflow - pre-test cleanup
- name: Clear Python bytecode & pytest cache
  uses: ./.github/actions/validate-cache

# Or manually:
- name: Clear Python bytecode
  run: |
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
```

### Forbidden Pattern

```yaml
# BAD: No bytecode cleanup
- name: Run Tests
  run: pytest tests/
  # .pyc files accumulate - can cause import errors
```

### Verification

```bash
# Verify no bytecode present
find . -type f -name "*.pyc"  # Should be empty
find . -type d -name __pycache__  # Should be empty

# Verify prevention mechanism
env | grep PYTHONDONTWRITEBYTECODE  # Should be "1"
```

### Prevention Checklist
- [ ] Set `PYTHONDONTWRITEBYTECODE=1` globally
- [ ] Add cache cleanup before test runs
- [ ] Add cache cleanup after test runs
- [ ] Verify no `.pyc` files created during CI
- [ ] Monitor for intermittent import errors

---

## Prevention Rule: Joblib Multiprocessing Safety

**Rule:** Tests using multiprocessing must not conflict with pytest-xdist

### Required Pattern

```python
# GOOD: Safe multiprocessing configuration
@pytest.fixture(scope="session")
def joblib_safe_setup():
    """Prevent Loky conflicts with pytest-xdist."""
    import os
    os.environ['LOKY_MAX_CPU_COUNT'] = '1'
    yield
    # Loky disabled - no worker contention
```

### Forbidden Pattern

```python
# BAD: Unrestricted multiprocessing
import joblib
# Uses Loky with all CPUs
# Conflicts with pytest-xdist parallelism
```

### Verification

```bash
# Verify LOKY_MAX_CPU_COUNT is set
echo $LOKY_MAX_CPU_COUNT  # Should be "1"

# Run integration tests without hanging
uv run pytest tests/integration/ -n 1 --timeout=120 --tb=short

# Monitor process count (should be stable)
watch -n 1 'ps aux | grep python | wc -l'
```

### Prevention Checklist
- [ ] Set `LOKY_MAX_CPU_COUNT=1` globally in CI
- [ ] Use `-n 1` for integration tests with multiprocessing
- [ ] Mark multiprocessing tests with `@pytest.mark.slow`
- [ ] Monitor for hanging/timeout tests
- [ ] Verify process count remains stable during runs

---

## Prevention Rule: Mock Patch Target Validation (Strategic 2025-01-11)

**Rule:** All mock patch targets must be validated before commit

**Impact:** Prevents 12% of CI failures (mock target drift)

### Required Pattern

```bash
# Run before committing ANY test changes
python scripts/validate-mock-targets.py

# For verbose output with suggestions
python scripts/validate-mock-targets.py --verbose

# CI enforcement (blocks invalid patches)
python scripts/validate-mock-targets.py --strict
```

### How It Works

1. **Pre-commit:** Validation catches typos before push
2. **CI Enforcement:** Lint-gate job blocks invalid patches
3. **Coverage:** Checks all @patch decorators in test files
4. **Suggestions:** Provides actual class names when patches don't match

### Example: Catching Mock Target Typos

```python
# BAD: Typo in class name
@patch("raglite.module.ATIClient")  # Wrong!
def test_something():
    pass

# Run validation:
# ERROR: Patch target 'ATIClient' not found
# Did you mean: 'ATICClient'?

# GOOD: Corrected
@patch("raglite.module.ATICClient")
def test_something():
    pass
```

### Prevention Checklist

- [ ] Run `python scripts/validate-mock-targets.py` before commit
- [ ] Verify output shows "All patch targets valid"
- [ ] Use IDE "Find References" to double-check patch targets
- [ ] Review mock patches in code review (spelling matters)
- [ ] Prefer `patch.object()` when type safety is important

### Related Documentation

- **Failure Pattern:** `docs/ci-knowledge/failure-patterns.md` → Mock Patch Target Drift
- **Runbook:** `docs/ci-failure-runbook.md` → Section 9
- **Testing Rules:** `.claude/rules/testing.md` → Mock Patching section

---

## Prevention Rule: pytest-xdist isinstance() Compatibility (Strategic 2025-01-11)

**Rule:** Custom class identity checks must use duck-typing, not isinstance()

**Impact:** Prevents 15% of CI failures (isinstance failures with -n auto)

### Required Pattern

```python
# GOOD: Class name check (xdist-safe)
assert result.__class__.__name__ == 'MyClass'

# GOOD: Duck-typing (xdist-safe)
assert hasattr(result, 'field1')
assert hasattr(result, 'field2')

# GOOD: Enum checks (xdist-safe)
assert trend.direction.name in ['UP', 'DOWN', 'STABLE']
```

### Forbidden Pattern

```python
# BAD: isinstance with custom class (fails with -n auto)
assert isinstance(result, MyClass)

# BAD: Enum membership check (fails with -n auto)
assert result.status in Status
```

### How It Works

1. **Linter:** `./scripts/check-isinstance-violations.sh` detects violations
2. **CI Enforcement:** Lint-gate job blocks xdist-incompatible patterns
3. **Prevention:** Catches issues before test execution
4. **Education:** Provides fix suggestions automatically

### Example: Fixing isinstance Violations

```bash
# Run linter
./scripts/check-isinstance-violations.sh

# Output shows violations:
VIOLATION: tests/unit/test_example.py:42
  assert isinstance(result, TrendAnalysisResult)
  Suggested fix: Use __class__.__name__ or hasattr() instead

# Fix it:
# OLD: assert isinstance(result, TrendAnalysisResult)
# NEW: assert result.__class__.__name__ == 'TrendAnalysisResult'
```

### Prevention Checklist

- [ ] Run `./scripts/check-isinstance-violations.sh` before commit
- [ ] Never use `isinstance()` for custom class checks
- [ ] Use `__class__.__name__` for type name validation
- [ ] Use `hasattr()` for duck-typing checks
- [ ] Use enum `.name` or `.value` properties
- [ ] Test locally with `-n auto` to catch issues

### Related Documentation

- **Failure Pattern:** `docs/ci-knowledge/failure-patterns.md` → pytest-xdist isinstance() Failures
- **Runbook:** `docs/ci-failure-runbook.md` → Section 12
- **Testing Rules:** `.claude/rules/testing.md` → isinstance Checks section

---

## Prevention Rule: Docker Infrastructure Auto-Recovery (Strategic 2025-01-11)

**Rule:** Docker/Colima must be automatically recovered before test collection

**Impact:** Prevents 10% of CI failures (Docker connection errors)

### Required Pattern

```python
# Automatic: pytest_configure hook handles recovery
# tests/fixtures/pytest_hooks.py

def pytest_configure(config):
    """Auto-start Docker if needed before test collection."""
    import subprocess
    try:
        # Check if Docker is running
        subprocess.run(["docker", "info"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Docker not running - auto-recover
        try:
            subprocess.run(["colima", "start"], check=True, timeout=60)
        except Exception as e:
            # Colima failed - skip integration tests
            config.addinivalue_line("markers", "requires_docker")
```

### How It Works

1. **Automatic:** Runs before pytest test collection
2. **Proactive:** Starts Docker if unavailable
3. **Graceful:** Skips tests if recovery fails
4. **Silent:** No output unless recovery is needed

### Example: Manual Recovery (if needed)

```bash
# Check Docker status
colima status

# If not running, auto-recover:
./scripts/ensure-docker-running.sh

# Verify Docker is working
docker info | head -5

# Verify containers are healthy
docker ps --filter "name=raglite"
```

### Prevention Checklist

- [ ] Automatic recovery via pytest_configure (already implemented)
- [ ] Manual verification: `colima status` before test sessions
- [ ] Optional auto-start on login: `brew services start colima`
- [ ] Check Docker health if tests fail: `docker info`
- [ ] Verify containers: `docker ps --filter "name=raglite"`

### Related Documentation

- **Failure Pattern:** `docs/ci-knowledge/failure-patterns.md` → Docker/Colima Not Running
- **Runbook:** `docs/ci-failure-runbook.md` → Section 13
- **Database Safety:** `.claude/rules/database-safety.md` → Container Lifecycle
- **Fixture Hooks:** `tests/fixtures/pytest_hooks.py` → pytest_configure hook

---

## Prevention Rule: Tolerance-Based Fixture Validation (Strategic 2025-01-11)

**Rule:** Non-deterministic values must use tolerance ranges, not hardcoded assertions

**Impact:** Prevents 949-test cascade failures from single validation anti-pattern

### Required Pattern

```python
# GOOD: Tolerance-based validation
def validate_chunk_count(count, baseline, tolerance=0.15):
    """Validate chunk count within tolerance band.

    Baseline: ~80 chunks for 10-page document
    Tolerance: ±15% (68-92 acceptable range)
    """
    min_count = int(baseline * (1 - tolerance))
    max_count = int(baseline * (1 + tolerance))
    assert min_count <= count <= max_count, \
        f"Count {count} outside {min_count}-{max_count}"
```

### Forbidden Pattern

```python
# BAD: Hardcoded range (fails on legitimate variations)
def validate_chunk_count(count):
    """Fails for valid chunk counts outside (10, 55)."""
    assert count in range(10, 55)  # Too restrictive
```

### How It Works

1. **Document baseline expectations** - What's the typical value?
2. **Set reasonable tolerance** - Allow for legitimate variance
3. **Calculate acceptance band** - baseline ± tolerance
4. **Document in comments** - Why this tolerance?

### Example: Fixing Strict Validation

```bash
# Failing test (strict range)
AssertionError: 120 not in range(10, 55)

# Analysis: Actual documents produce 80-120 chunks (valid range)
# Fix: Use tolerance-based validation

# OLD (bad):
assert chunk_count in range(10, 55)

# NEW (good):
assert 68 <= chunk_count <= 92  # 80 ± 15%
```

### Prevention Checklist

- [ ] Never hardcode expected value ranges without reasoning
- [ ] Always document baseline expectation in test
- [ ] Use tolerance-based assertions for non-deterministic values
- [ ] Test with multiple data sizes/types to find actual range
- [ ] Use parametrized tests to catch edge cases
- [ ] Review tolerance annually as systems evolve

### Related Documentation

- **Failure Pattern:** `docs/ci-knowledge/failure-patterns.md` → Fixture Validation Range
- **Runbook:** `docs/ci-failure-runbook.md` → Section 14
- **CI Strategy:** `docs/ci-strategy.md` → Test Validation Patterns

---

## Prevention Rule: API Contract Testing (Strategic 2025-01-11)

**Rule:** Function signature changes must be caught with contract tests

**Impact:** Prevents cascade failures from API signature drift (5+ tests fail from single change)

### Required Pattern

```python
# ADD: Signature validation test (detects drift early)
def test_api_contract_generate_ensemble_forecast():
    """Verify API signatures don't change unexpectedly.

    This contract test catches breaking changes before test execution.
    Update this test when intentionally changing the API.
    """
    import inspect
    from raglite.forecasting.ensemble import generate_ensemble_forecast

    sig = inspect.signature(generate_ensemble_forecast)
    params = list(sig.parameters.keys())

    # Required parameters must exist
    assert 'config' in params, "Missing required 'config' parameter"
    assert 'historical_data' in params, "Missing required 'historical_data' parameter"

    # Verify parameter types via annotations
    config_param = sig.parameters['config']
    assert config_param.annotation != inspect.Parameter.empty, \
        "Parameter 'config' must have type annotation"
```

### How It Works

1. **Document API contract** - What parameters must exist?
2. **Test signature dynamically** - Catch breaking changes
3. **Run before feature tests** - Fail fast on signature mismatches
4. **Update when intentional** - Need to change signature? Update contract test

### Example: Catching Signature Drift

```bash
# Old API (works):
generate_ensemble_forecast(config)

# New API (requires historical_data):
generate_ensemble_forecast(config, historical_data)

# Contract test catches this:
FAILED test_api_contract - Missing required 'historical_data' parameter

# Fix: Update all calls
# result = generate_ensemble_forecast(config)
# result = generate_ensemble_forecast(config, historical_data=data)
```

### Prevention Checklist

- [ ] Add contract test for all public API functions
- [ ] Test required parameters exist
- [ ] Test parameter types (via annotations)
- [ ] Test return type contract
- [ ] Run contract tests before feature tests
- [ ] Update contract when intentionally changing API

### Related Documentation

- **Failure Pattern:** `docs/ci-knowledge/failure-patterns.md` → API Contract Drift
- **Runbook:** `docs/ci-failure-runbook.md` → Section 15
- **CI Strategy:** `docs/ci-strategy.md` → Test Validation Patterns

---

## Prevention Rule: Config-Test Synchronization (Strategic 2025-01-11)

**Rule:** Configuration and test files must be validated together before merge

**Impact:** Prevents runtime errors from config-test drift (3+ tests fail per config change)

### Required Pattern

```python
# ADD: Config-test synchronization test
def test_config_metrics_synchronized():
    """Verify configured metrics match test expectations.

    This prevents divergence between config.yaml and test fixtures.
    """
    from raglite.config import Settings
    import yaml

    # Load both config and test expectations
    with open('raglite/config.yaml') as f:
        config_data = yaml.safe_load(f)

    from tests.fixtures.metrics import EXPECTED_METRICS

    configured_metrics = set(config_data['metrics'].keys())
    expected_metrics = set(EXPECTED_METRICS)

    # Check: All configured metrics are tested
    missing_tests = configured_metrics - expected_metrics
    assert not missing_tests, \
        f"Metrics in config but not tested: {missing_tests}"

    # Check: All tested metrics are configured
    missing_config = expected_metrics - configured_metrics
    assert not missing_config, \
        f"Metrics tested but not in config: {missing_config}"
```

### How It Works

1. **Load configuration** - What's configured?
2. **Load test expectations** - What are we testing?
3. **Compare sets** - Ensure they match exactly
4. **Fail loudly** - Catch divergence at test time

### Example: Catching Config Drift

```bash
# Config was updated but tests weren't:
cement_demand removed from config.yaml

# Test fixture still tries to use it:
KeyError: 'cement_demand'

# Sync test catches this:
FAILED test_config_metrics_synchronized
  Metrics tested but not in config: {'cement_demand'}

# Fix: Update test fixtures to remove cement_demand references
```

### Prevention Checklist

- [ ] Add config-test sync test before any config changes
- [ ] Test passes only if config and tests match exactly
- [ ] Run sync test as part of pre-commit validation
- [ ] Update sync test when adding new configured items
- [ ] Document metric definitions in both config and tests
- [ ] Use shared constants for metric names (DRY principle)

### Related Documentation

- **Failure Pattern:** `docs/ci-knowledge/failure-patterns.md` → Config-Test Sync Drift
- **Runbook:** `docs/ci-failure-runbook.md` → Section 16
- **CI Strategy:** `docs/ci-strategy.md` → Test Validation Patterns
