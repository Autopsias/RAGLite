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
