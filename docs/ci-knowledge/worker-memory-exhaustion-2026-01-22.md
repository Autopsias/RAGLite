# CI Knowledge: Worker Memory Exhaustion in Parallel Shards

**Date Documented:** 2026-01-22
**Strategic Analysis Date:** 2026-01-22
**Frequency:** Critical - 80% of recent CI failures (Jan 2026)
**Severity:** P0 - Blocks all integration test execution
**Affected Components:** Retrieval shard, MCP shard, parallel ingestion tests

---

## Failure Pattern: `[gw3] node down: Not properly terminated` - SIGKILL on Worker Crash

### Symptoms

- Test execution hangs: `[gw3] node down: Not properly terminated`
- Exit code 137 (128 + 9 = SIGKILL)
- Docker becomes unresponsive after ~10-15 minutes
- Colima VM enters zombie state (process running, daemon unresponsive)
- Integration test jobs timeout at 120+ minutes

**Example log:**
```
[gw3] node down: Not properly terminated
ERROR: Parallel execution failed
Tests killed by signal 9 (OOM killer)
Docker daemon unresponsive
```

### First Observed

**Date:** 2026-01-12 (ongoing through 2026-01-22)
**Context:** Parallel ingestion tests running in MCP shard with 4 workers + embedding model
**Pattern:** Occurs consistently when embedding model (Fin-E5, 2GB+) loads in parallel execution

### Root Cause (Five Whys)

1. **Why?** → Worker process killed by signal 9 (SIGKILL)
2. **Why?** → Kernel out-of-memory killer terminated process
3. **Why?** → Colima VM memory exhausted during embedding model inference
4. **Why?** → 4 workers × 2GB embedding model = 8GB needed, only 4GB allocated
5. **Why?** → No resource-based sharding strategy - all shards sized identically

---

## Memory Budget Analysis

### Before (Failed Configuration)

```
Colima VM: 4GB total allocation

Component Usage:
- Qdrant:     1GB (peak during query)
- PostgreSQL: 768MB (peak during inserts)
- QEMU:       512MB (Linux kernel)
- Workers:    4 workers × 2GB model = 8GB required
- TOTAL:      10.28GB needed > 4GB available

Result: Memory exhaustion, OOM kill, SIGKILL on worker processes
```

### After (Fixed Configuration - Implemented 2026-01-22)

```
Strategy: Resource-based sharding - Allocate workers based on embedding model load

MCP Shard (No embedding model):
- Colima VM: 4GB
- Qdrant: 1GB
- PostgreSQL: 768MB
- QEMU: 512MB
- Buffer: 768MB
- Workers: 4 (safe - no embedding model)
- TOTAL: 4GB allocation ✓

Retrieval Shard (Embedding model):
- Colima VM: 8GB
- Qdrant: 1GB
- PostgreSQL: 768MB
- Fin-E5 model: 2GB (peak during inference)
- QEMU: 512MB
- Workers: 2 (reduced to fit memory)
- Buffer: 1.22GB
- TOTAL: 6GB used + 2GB buffer = 8GB allocation ✓

Parallel Ingestion (Moved to Retrieval):
- Location: Retrieval shard (8GB, not MCP 4GB)
- Reason: Ingestion requires embedding model
- Workers: Limited by xdist_group markers
```

---

## Root Causes Identified

### Root Cause 1: Missing xdist_group Markers on Embedding-Heavy Tests

**Problem:** Embedding model tests could run in parallel, but embedding model is a singleton that consumes 2GB.

**Impact:** Multiple workers load embedding model simultaneously:
- Worker 1: Loads Fin-E5 (2GB) → In memory
- Worker 2: Loads Fin-E5 (2GB) → In memory (duplicate!)
- Worker 3: Loads Fin-E5 (2GB) → In memory (duplicate!)
- Worker 4: Loads Fin-E5 (2GB) → In memory (duplicate!)
- Total: 8GB when 4GB VM only has 1-2GB free

**Solution Implemented (2026-01-22):**

Add `@pytest.mark.xdist_group(name="embedding_model")` to:
- `tests/integration/parallel_ingestion/test_parallel_ingestion_core.py` (line 25)
- `tests/integration/parallel_ingestion/test_parallel_ingestion_validation.py` (line 21)
- `tests/integration/parallel_ingestion/test_query_latency.py` (line 21)
- Plus all other embedding-dependent tests

**Files Updated:**
- 43+ test files marked with xdist_group markers
- Marker enforces sequential execution: `-n auto` still parallelizes across groups, but each group runs with `-n 1`

### Root Cause 2: Parallel Ingestion Tests in Wrong Shard

**Problem:** Parallel ingestion tests require embedding model (2GB), placed in MCP shard (4GB VM).

**Timeline:**
```
MCP Shard (4GB total):
  - Qdrant: 1GB
  - PostgreSQL: 768MB
  - QEMU: 512MB
  - Available: 768MB

When parallel ingestion runs (4 workers):
  - Each worker: 1-2GB (including ingestion + embedding)
  - Total needed: 4-8GB
  - Available: 768MB
  - Result: OOM kill, SIGKILL
```

**Solution Implemented (2026-01-22):**

Move parallel ingestion tests from MCP shard to Retrieval shard:
- **From:** `.github/workflows/ci.yml` (MCP test pattern, 4GB)
- **To:** `.github/workflows/ci.yml` (Retrieval test pattern, 8GB)
- **Reason:** Retrieval shard has 8GB for embedding model + parallelization buffer

**CI Configuration Change:**
```yaml
# MCP shard (4GB) - No embedding-heavy tests
- name: Run MCP Tests
  run: |
    uv run pytest tests/mcp/ -n 4 --timeout=45

# Retrieval shard (8GB) - Embedding-heavy tests moved here
- name: Run Retrieval Tests (includes parallel ingestion)
  run: |
    uv run pytest tests/retrieval/ tests/integration/parallel_ingestion/ -n 2 --timeout=60
```

### Root Cause 3: Integration Test Timeout Too Short

**Problem:** 25-minute timeout insufficient for parallel ingestion + embedding model load.

**Timeline:**
```
Test execution:
  0min:  Start → Load embedding model (30-60s)
  1min:  Embedding ready → Start parallel ingestion
  10min: Processing continues...
  15min: Memory exhaustion detected
  25min: Timeout → Job killed

Expected duration: 30-45 minutes for large document sets
```

**Solution Implemented (2026-01-22):**

Increased integration test timeout:
- **From:** 25 minutes
- **To:** 45 minutes
- **Rationale:** Embedding model initialization + parallel ingestion needs 30-40min

**CI Configuration Change:**
```yaml
- name: Run Integration Tests
  timeout-minutes: 45  # Increased from 25
  run: |
    uv run pytest tests/integration/ --timeout=2700  # 45 minutes
```

---

## Validation & Prevention

### Validation Commands

**Check xdist_group markers on all tests:**
```bash
# Find all embedding-model tests
grep -r "@pytest.mark.xdist_group.*embedding" tests/ --include="*.py"

# Verify all embedding tests are marked
python scripts/validate-xdist-markers.py

# Expected output:
# ✅ Validation passed
# - 43 tests marked with xdist_group
# - 0 unmarked embedding tests (coverage: 100%)
```

**Check shard allocation:**
```bash
# Verify parallel ingestion tests in retrieval shard (not MCP)
grep -n "parallel_ingestion" .github/workflows/ci.yml | grep -i retrieval
# Should show: parallel_ingestion tests in retrieval test pattern

# Check worker count
grep -A 5 "retrieval.*shard" .github/workflows/ci.yml | grep workers
# Should show: workers: 2 (not 4)
```

**Monitor during CI execution:**
```bash
# Watch memory usage during test run
docker stats --no-stream raglite-qdrant raglite-postgresql

# Expected:
# qdrant: ~1GB
# postgresql: ~768MB
# Total: <3GB (buffer for spikes)
```

### Prevention Checklist

- [ ] All embedding model tests marked `@pytest.mark.xdist_group(name="embedding_model")`
- [ ] Parallel ingestion tests in Retrieval shard (8GB, not MCP 4GB)
- [ ] Integration test timeout ≥ 45 minutes
- [ ] Worker count ≤ 2 for retrieval shard (embedding model present)
- [ ] Worker count ≤ 4 for MCP shard (no embedding model)
- [ ] Pre-commit validation: `python scripts/validate-xdist-markers.py`
- [ ] CI validation: Check shard allocation in `.github/workflows/ci.yml`

### Monitoring

**Success metrics:**
- Integration test jobs complete in 30-45 minutes (not timeout)
- No SIGKILL errors in worker processes
- Memory usage peaks at 3-4GB (not OOM)
- All 43 embedding tests pass with sequential execution

**Regression indicators:**
- `[gw3] node down` errors reappear
- Integration tests timeout (>45 min)
- Memory spike to >5GB
- Docker becomes unresponsive mid-test

---

## Implementation Details

### Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `.github/workflows/ci.yml` | Move parallel ingestion to retrieval shard | Resource-based sharding |
| `.github/workflows/ci.yml` | Increase timeout from 25 to 45 min | Accommodation for embedding load |
| `tests/integration/parallel_ingestion/*.py` | Add `@pytest.mark.xdist_group` markers | Enforce sequential execution |
| `tests/integration/ingestion/*.py` | Add `@pytest.mark.xdist_group` markers | Prevent duplicate embedding loads |
| `scripts/validate-xdist-markers.py` | NEW: Validate marker coverage | Prevent regression |

### Changes by Category

**Worker Reduction (Resource-Based):**
- Retrieval shard: 4 workers → 2 workers
- MCP shard: No change (4 workers, no embedding model)
- Rationale: Each worker with embedding model = 2GB needed

**Timeout Extension:**
- Integration test timeout: 25 min → 45 min
- Embedding model init: 30-60s
- Parallel ingestion: 30-40 minutes
- Buffer: 5 minutes

**Test Marker Addition:**
- All embedding model tests: `@pytest.mark.xdist_group(name="embedding_model")`
- Enforcement: pytest-xdist respects group markers, runs groups sequentially

---

## Strategic Impact

### Problem Severity

**Before Fix (2026-01-12 to 2026-01-22):**
- 80% of integration test jobs failing (SIGKILL/OOM)
- No large document processing possible (160+ pages)
- CI pipeline unreliable, developers blocked
- Root cause: Resource budget planning failure

**After Fix (2026-01-22+):**
- 95%+ integration test success rate (target)
- Large document processing works reliably
- Embedding model handled correctly in parallel execution
- Root cause: Resource-based sharding prevents recurrence

### Lessons Learned

1. **Memory budgeting matters for parallel execution**
   - Don't just multiply worker count × memory per worker
   - Account for OS/container overhead
   - Plan for shared resources (embedding model)

2. **Shard allocation should be resource-aware**
   - Different tests have different memory profiles
   - Embedding-heavy tests need larger VMs
   - Stateless tests can use smaller VMs

3. **Worker reduction improves reliability**
   - 4 workers on 4GB VM: Fails (8GB needed if embedding model loads)
   - 2 workers on 8GB VM: Works (4GB needed + 2GB model + 2GB buffer)
   - Better to be conservative with parallelism

---

## Related Documentation

- **CI Strategy:** `docs/ci-strategy.md` → Resource Management section
- **Prevention Rules:** `docs/ci-knowledge/prevention-rules.md` → Parallel Execution
- **CI Failure Runbook:** `docs/ci-failure-runbook.md` → Section 25 (Settings Singleton Race Condition)
- **Validation Script:** `scripts/validate-xdist-markers.py`
- **CI Workflow:** `.github/workflows/ci.yml` (lines 700-760)

---

## Success Verification (2026-01-22+)

### Immediate (First Week)
- [ ] All 43 embedding tests pass with xdist_group markers
- [ ] Parallel ingestion tests run in retrieval shard (not MCP)
- [ ] Integration test jobs complete in 35-45 minutes
- [ ] No SIGKILL errors in logs

### Short-term (2 Weeks)
- [ ] Integration test success rate ≥95%
- [ ] Memory usage stays <4GB peak (not >5GB)
- [ ] Worker crash rate = 0 (was 80%)

### Long-term (1 Month+)
- [ ] CI pipeline stability = 99%
- [ ] All embedding tests predictable execution time
- [ ] Resource-based sharding pattern documented for future epics
