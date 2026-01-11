# CI Knowledge: Self-Hosted Runner Guide

**Target Audience:** DevOps, CI/CD engineers
**Scope:** raglite self-hosted runners on MacOS with 24GB RAM
**Updated:** 2025-12-30

---

## Runner Specifications

### Hardware Configuration

- **OS:** macOS (Darwin 25.2.0)
- **RAM:** 24GB shared across projects
- **CPU:** Multi-core, supports parallelization
- **Colima Runtime:** Docker with 4 CPU / 6GB allocation (configurable)
- **Storage:** Local `__pycache__` and container volumes

### Current Configuration

```yaml
runner:
  labels: ["self-hosted", "raglite"]
  timeout-minutes: 30  # Hard limit per job
  environment: macOS with Colima Docker
```

---

## Known Issues & Mitigations

### Issue 1: Bytecode Cache Pollution

**Problem:** Python bytecode accumulates across builds, causing import errors

**Symptoms:**
- `ModuleNotFoundError` in CI but not locally
- Intermittent failures (works on retry)
- Different behavior in consecutive runs

**Root Cause:** macOS runner reuses environments. Python writes `.pyc` files to `__pycache__`. Old bytecode from previous builds causes import conflicts.

**Mitigation:**

```yaml
env:
  PYTHONDONTWRITEBYTECODE: "1"  # Global - prevents all .pyc generation
```

**Additional Steps:**
```yaml
- name: Clear Python bytecode & pytest cache
  uses: ./.github/actions/validate-cache
```

**Verification:**
```bash
# No .pyc files should exist
find . -type f -name "*.pyc" | wc -l  # Should be 0
find . -type d -name __pycache__ | wc -l  # Should be 0
```

---

### Issue 2: Joblib Multiprocessing Deadlocks

**Problem:** Joblib's Loky backend conflicts with pytest-xdist parallelism

**Symptoms:**
- Tests hang indefinitely (trigger 30-minute timeout)
- Resource exhaustion in logs
- Job needs manual cancellation
- Works fine with `-n 0` (no parallelism)

**Root Cause:**
1. Tests using statsmodels/pmdarima trigger Joblib → Loky
2. Loky spawns workers using all available CPUs
3. pytest-xdist also uses multiprocessing for test distribution
4. Both systems compete for CPU resources
5. Resource contention causes worker deadlock

**Mitigation:**

```yaml
env:
  LOKY_MAX_CPU_COUNT: "1"  # Disable Loky's multiprocessing entirely
```

**Test Configuration:**
- Unit tests: `-n 4` (pytest-xdist parallelism only)
- Integration tests: `-n 1` (serial execution for safety)

**Verification:**
```bash
# Tests should complete without hanging
export LOKY_MAX_CPU_COUNT=1
uv run pytest tests/integration/ -n 1 --timeout=120 --tb=short
```

---

### Issue 3: Resource Tracker Orphaned Processes

**Problem:** Multiprocessing resource tracker processes persist after tests

**Symptoms:**
- `SIGKILL` during parallel test execution
- Process count grows unbounded
- Memory usage increases over time
- Job runs out of memory

**Root Cause:**
- Joblib creates resource tracker processes
- These aren't cleaned up by pytest fixtures
- Accumulate across multiple test runs
- Consume memory until OOM

**Mitigation:**

```yaml
- name: Cleanup Orphaned Processes (P0 Fix)
  run: |
    pkill -9 -f "resource_tracker" 2>/dev/null || echo "No orphaned processes"
    pkill -9 -f "multiprocessing" 2>/dev/null || echo "No multiprocessing processes"
```

**Additional Protection:**
- Set `LOKY_MAX_CPU_COUNT=1` to prevent Loky from creating workers
- Add explicit resource cleanup in fixtures

**Verification:**
```bash
# Check for orphaned processes
ps aux | grep resource_tracker  # Should be empty
ps aux | wc -l  # Should be stable across runs
```

---

### Issue 4: pytest-xdist Worker State Pollution

**Problem:** Global singleton state leaks between pytest-xdist workers

**Symptoms:**
- Tests fail in parallel but pass serially
- "worker stopped unexpectedly" messages
- Intermittent test failures
- Different order of failures in different runs

**Root Cause:**
- Settings singleton initialized at import time
- All pytest-xdist workers import same module
- Global state is shared across workers
- Workers are isolated, but initialization happens before isolation

**Mitigation:**

```python
# GOOD: Lazy loading
def lazy_load_settings():
    """Load on demand, not at import."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# BAD: Module-level initialization
settings = Settings()  # Initializes for all workers
```

**Test Markers:**
```python
# Mark stateful tests as slow to disable parallelism
@pytest.mark.slow
async def test_state_dependent_behavior():
    """This test requires serial execution."""
    pass
```

**Verification:**
```bash
# Tests should pass with and without parallelism
uv run pytest tests/ -n 0 --tb=short  # Serial
uv run pytest tests/ -n 4 --tb=short  # Parallel
# Both should have identical results
```

---

### Issue 5: Container Volume Mount Staleness

**Problem:** Docker containers have stale volume mounts from previous runs

**Symptoms:**
- "Databases Empty" despite data on disk
- Connection errors to Qdrant/PostgreSQL
- Different behavior between local and CI
- Mount paths are incorrect in `docker inspect`

**Root Cause:**
- CI container names are reused (`raglite-qdrant`)
- Previous CI runs created containers with stale mounts
- New container creation doesn't update old mount paths
- Containers point to wrong storage volumes

**Mitigation:**

```bash
# Verify mounts are correct
docker inspect raglite-qdrant --format='{{json .Mounts}}'
# Check mount sources point to /raglite directory, not CI temp paths

# If wrong, recreate containers
docker stop raglite-qdrant raglite-postgresql
docker rm raglite-qdrant raglite-postgresql
docker-compose up -d qdrant postgresql
```

**Container Naming Strategy:**
- Production: `raglite-qdrant` (persistent mounts)
- Test: `raglite-qdrant-test` (ephemeral, CI job cleanup)
- Each CI job type: unique suffix (`-test`, `-agentic`, `-discovery`, `-burnin`)

**Verification:**
```bash
# Mount paths should be in /Users/ricardocarvalho/DeveloperFolder/RAGLite/
docker inspect raglite-qdrant-test --format='{{range .Mounts}}{{.Source}} → {{.Destination}}{{end}}'

# Should output something like:
# /Users/ricardocarvalho/DeveloperFolder/RAGLite/qdrant_storage_test → /qdrant/storage
```

---

## Environment Configuration Checklist

### Before Every Test Run

- [ ] `PYTHONDONTWRITEBYTECODE=1` is set
- [ ] `LOKY_MAX_CPU_COUNT=1` is set
- [ ] `APP_ENV=test` is set (uses test database)
- [ ] No stale `.pyc` files exist
- [ ] Container mounts are correct
- [ ] Docker services are running and healthy

### Verification Script

```bash
#!/bin/bash
# verify-runner-env.sh

echo "=== CI Runner Environment Verification ==="

# Check environment variables
echo "PYTHONDONTWRITEBYTECODE: ${PYTHONDONTWRITEBYTECODE:-NOT SET}"
echo "LOKY_MAX_CPU_COUNT: ${LOKY_MAX_CPU_COUNT:-NOT SET}"
echo "APP_ENV: ${APP_ENV:-NOT SET}"

# Check for bytecode
PYCOUNT=$(find . -type f -name "*.pyc" | wc -l)
echo "Python bytecode files (.pyc): $PYCOUNT (should be 0)"

# Check for resource tracker
RTCOUNT=$(ps aux | grep -c "resource_tracker")
echo "Resource tracker processes: $RTCOUNT (should be 0-1)"

# Check containers
echo ""
echo "=== Docker Container Status ==="
docker ps -a | grep raglite

# Check Qdrant mount
QDRANT_MOUNT=$(docker inspect raglite-qdrant --format='{{range .Mounts}}{{println .Source}}{{end}}' 2>/dev/null)
echo "Qdrant mount: $QDRANT_MOUNT"

# Verify connectivity
echo ""
echo "=== Service Connectivity ==="
python3 -c "from qdrant_client import QdrantClient; c=QdrantClient('localhost',6335); print('Qdrant: OK')" 2>/dev/null || echo "Qdrant: FAIL"
docker exec raglite-postgresql psql -U raglite -d raglite -c "SELECT 1" &>/dev/null && echo "PostgreSQL: OK" || echo "PostgreSQL: FAIL"

echo ""
echo "=== Verification Complete ==="
```

---

## Debugging Commands

### Bytecode Issues

```bash
# Find all .pyc files
find . -type f -name "*.pyc"

# Clear bytecode
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Verify PYTHONDONTWRITEBYTECODE prevents generation
export PYTHONDONTWRITEBYTECODE=1
python3 -c "import sys; sys.exit(0)"
find . -type f -name "*.pyc"  # Should still be empty
```

### Multiprocessing Issues

```bash
# Check resource tracker processes
ps aux | grep resource_tracker

# Kill orphaned processes
pkill -9 -f resource_tracker
pkill -9 -f multiprocessing

# Monitor process count
watch -n 1 'ps aux | grep python | wc -l'

# Verify LOKY_MAX_CPU_COUNT
echo $LOKY_MAX_CPU_COUNT  # Should be "1"
```

### Container Issues

```bash
# Check mount correctness
docker inspect raglite-qdrant --format='{{json .Mounts}}'
docker inspect raglite-postgresql --format='{{json .Mounts}}'

# Test connectivity
python3 << 'EOF'
from qdrant_client import QdrantClient
try:
    c = QdrantClient(host='localhost', port=6335)
    print(f"Qdrant collections: {len(c.get_collections().collections)}")
except Exception as e:
    print(f"Qdrant error: {e}")
EOF

# Check database
docker exec raglite-postgresql psql -U raglite -d raglite -c "SELECT COUNT(*) FROM information_schema.tables;"
```

### pytest-xdist Issues

```bash
# Run serially to test isolation
uv run pytest tests/ -n 0 --tb=short

# Run with parallelism
uv run pytest tests/ -n 4 --tb=short

# Compare results - should be identical
# If different, likely xdist worker pollution
```

---

## Performance Tuning

### Parallelism Configuration

| Test Suite | Parallelism | Rationale | Duration |
|------------|-------------|-----------|----------|
| Unit tests | `-n 4` | Low resource usage, isolated | <2m |
| Integration | `-n 1` | Database contention, resource management | <10m |
| E2E | `-n 1` | Full system stress, serial required | <15m |

### Timeout Tuning

```yaml
# CI job timeout
timeout-minutes: 30  # Hard limit

# Individual test timeout
--timeout=120  # 2 minutes per test
```

### Memory Management

```bash
# Monitor memory during tests
watch -n 1 'ps aux | grep python | awk "{sum+=$6} END {print sum/1024 \"MB\"}"'

# Check container memory
docker stats --no-stream raglite-qdrant raglite-postgresql
```

---

## References

- **CI Failure Runbook:** `/docs/ci-failure-runbook.md`
- **CI Strategy:** `/docs/ci-strategy.md`
- **Database Safety:** `/.claude/rules/database-safety.md`
- **Test Reliability Rules:** `/.claude/rules/testing.md`
