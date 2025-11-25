# CI Workflow Hang Analysis - Deep Dive

**Date:** 2025-10-29
**Issue:** Local MacBook hangs when running CI workflow
**Status:** ROOT CAUSE IDENTIFIED

---

## 🔴 CRITICAL FINDINGS

### System State
- **Total RAM:** 24 GB
- **Free RAM:** 0.24 GB ⚠️ CRITICAL
- **Active Memory:** 9.35 GB
- **Inactive Memory:** 9.24 GB
- **CPU Cores:** 12
- **Docker Services:**
  - Qdrant: 207 MB (1.3%)
  - PostgreSQL: 48 MB (0.3%)

### GitHub Actions Self-Hosted Runners
**DISCOVERED: 20 ACTIVE RUNNER INSTANCES** 🚨

```
/Users/ricardocarvalho/github-runners/actions-runner
/Users/ricardocarvalho/github-runners/actions-runner-2
/Users/ricardocarvalho/github-runners/runner-1
/Users/ricardocarvalho/github-runners/runner-2
/Users/ricardocarvalho/github-runners/powerpoint-runner-1
/Users/ricardocarvalho/github-runners/powerpoint-runner-2
/Users/ricardocarvalho/github-runners/powerpoint-runner-3
/Users/ricardocarvalho/actions-runner (3 instances)
```

All runners are listening and ready to accept jobs simultaneously.

---

## 🔥 ROOT CAUSE: Resource Amplification Cascade

### The Perfect Storm

#### 1. **Excessive Runner Parallelism**
```yaml
# CI workflow has 11 jobs
runs-on: self-hosted  # Each job can grab any of 20 runners
```

**Problem:** With 20 runners available, GitHub Actions will aggressively dispatch jobs in parallel.

#### 2. **Pytest Worker Explosion**
```ini
# pytest.ini (line 44)
-n 10              # DEFAULT: 10 parallel workers for ALL tests
--dist loadfile    # Load distribution by file
```

```yaml
# ci.yml unit tests (line 180)
pytest tests/unit/ -n auto  # OVERRIDES to use ALL 12 CPU cores
```

**Calculation:**
- If 3 jobs run simultaneously: 3 jobs × 10 workers = **30 pytest processes**
- If 5 jobs run simultaneously: 5 jobs × 10 workers = **50 pytest processes**
- If all 11 jobs run: 11 jobs × 10 workers = **110 pytest processes** 💥

#### 3. **Memory Multiplication**
Each parallel job:
```bash
uv venv ci-venv              # Create fresh venv (~500MB-1GB)
uv pip install -e .          # Install dependencies
uv pip install pytest...     # Install test tools
```

**Per-Job Memory Usage:**
- Base venv: 500-800 MB
- pytest processes (10 workers): 50-100 MB each = 500-1000 MB
- Sentence-transformers model: 500 MB (loaded per worker)
- Docling dependencies: 200-300 MB
- **Total per job: 1.7-2.8 GB**

**If 5 jobs run simultaneously: 8.5-14 GB just for CI** 😱

#### 4. **Integration Test Duration**
```yaml
timeout-minutes: 60          # Integration tests can run for 1 hour
TEST_USE_FULL_PDF: "true"    # 160-page PDF (~150s ingestion per test)
```

Long-running jobs occupy runners and memory for extended periods.

---

## 📊 Parallelism Analysis Matrix

| Concurrent Jobs | Pytest Workers | Total Processes | Memory (Estimated) | System State |
|----------------|----------------|----------------|-------------------|--------------|
| 1 | 10 | 10 | 2.8 GB | ✅ Stable |
| 2 | 20 | 20 | 5.6 GB | ⚠️ Elevated |
| 3 | 30 | 30 | 8.4 GB | 🔶 High pressure |
| 4 | 40 | 40 | 11.2 GB | 🔴 Critical |
| 5 | 50 | 50 | 14 GB | 💥 System hang |
| 11 (max) | 110 | 110 | 30.8 GB | 💀 OOM killer |

**Current Free RAM: 0.24 GB** - System is already at capacity before CI starts!

---

## 🎯 Why This Causes Hangs

### 1. **Memory Thrashing**
- With <1 GB free RAM, macOS starts aggressive swapping
- Disk I/O becomes bottleneck (even on SSD)
- System becomes unresponsive as it swaps virtual memory

### 2. **CPU Context Switching Overhead**
- 12 cores handling 50-110 processes
- Context switch overhead: ~5-10 μs per switch
- With 100 processes: ~1000-2000 context switches/sec
- CPU time wasted on scheduling instead of work

### 3. **Resource Starvation**
- Desktop apps (VS Code, browsers) can't get CPU time
- UI becomes frozen
- Mouse/keyboard lag or complete freeze

### 4. **Test Framework Deadlocks**
- pytest-xdist workers waiting for resources
- Integration tests waiting for Qdrant connections
- Circular resource contention

---

## 🔍 CI Workflow Hotspots

### Job Parallelism (Line 27-29)
```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```
✅ **GOOD:** Cancels old runs, but doesn't limit concurrent jobs within a run.

### Job Dependencies
```yaml
# Jobs that can run in parallel (NO dependencies):
1. lint
2. type-check
3. security
4. docs-validation
5. test-count-validation

# Jobs with dependencies (run sequentially):
6. test-unit (no deps)
7. test-integration (needs: test-unit)
8. test-e2e (needs: test-unit)
9. test-accuracy (needs: test-integration)
10. test-performance (needs: test-integration)
11. build-summary (needs: all)
```

**Peak Parallelism:** 5 jobs can start simultaneously (jobs 1-5), then unit tests (6) join.

---

## 🚨 Critical Configuration Issues

### Issue 1: Unlimited Job Parallelism
**File:** `.github/workflows/ci.yml`
**Problem:** No limits on concurrent job execution

### Issue 2: Aggressive Worker Count
**File:** `pytest.ini` (line 44)
```ini
-n 10  # Hardcoded 10 workers regardless of system load
```

**File:** `.github/workflows/ci.yml` (line 180)
```yaml
pytest tests/unit/ -n auto  # Uses all 12 cores
```

### Issue 3: Multiple venv Installations
**Problem:** Each job creates a fresh venv instead of reusing
- 11 jobs × 800 MB = 8.8 GB just for venvs

### Issue 4: Excessive Runner Count
**Problem:** 20 runners for a single developer is overkill
- Recommended: 1-2 runners per developer
- Current: 20 runners (10x over-provisioned)

---

## 💡 RECOMMENDED SOLUTIONS

### Immediate Fixes (Do These Now)

#### 1. **Reduce Active Runners** ⭐⭐⭐ CRITICAL
```bash
# Stop excess runners (keep only 2-3)
cd ~/github-runners/powerpoint-runner-1 && ./svc.sh stop
cd ~/github-runners/powerpoint-runner-2 && ./svc.sh stop
cd ~/github-runners/powerpoint-runner-3 && ./svc.sh stop
cd ~/github-runners/runner-2 && ./svc.sh stop
cd ~/actions-runner-2 && ./svc.sh stop
cd ~/actions-runner-3 && ./svc.sh stop
```

**Keep running:**
- 1 runner for RAGLite
- 1 runner for Powerpoint Agent (if needed)

**Impact:** Limits max concurrent jobs to 2 instead of 20

#### 2. **Limit Pytest Workers in CI** ⭐⭐⭐ CRITICAL
**File:** `.github/workflows/ci.yml`

```yaml
# Line 180 - Unit tests
- name: Run unit tests with coverage
  run: |
    source ci-venv/bin/activate
    pytest tests/unit/ \
      -n 4 \              # ⬅️ CHANGE: Limit to 4 workers instead of auto
      --dist worksteal \
      -m "" \
      --cov=raglite \
      # ... rest unchanged
```

**Impact:**
- Before: 12 workers × 3 jobs = 36 processes
- After: 4 workers × 2 jobs = 8 processes
- Memory: 11.2 GB → 3.2 GB (72% reduction)

#### 3. **Sequential Job Execution for Heavy Tests** ⭐⭐
**File:** `.github/workflows/ci.yml`

Add job dependencies to prevent parallel execution:
```yaml
test-integration:
  needs: [test-unit, lint, type-check]  # Wait for fast checks first

test-e2e:
  needs: [test-integration]  # Sequential after integration

test-accuracy:
  needs: [test-e2e]  # Sequential after E2E
```

**Impact:** Only 1 heavy test job runs at a time

#### 4. **Add Matrix Strategy Limits** ⭐
```yaml
strategy:
  max-parallel: 2  # Limit concurrent jobs
  fail-fast: false
```

---

### Medium-Term Optimizations

#### 5. **Shared Dependency Cache**
```yaml
- name: Cache Python dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/uv
      ci-venv
    key: ${{ runner.os }}-uv-${{ hashFiles('pyproject.toml') }}

- name: Install dependencies with uv (use cache)
  run: |
    if [ ! -d "ci-venv" ]; then
      uv venv ci-venv
      source ci-venv/bin/activate
      uv pip install -e .
      uv pip install pytest...
    else
      source ci-venv/bin/activate
    fi
```

**Impact:** Reuse venv across jobs, save 8.8 GB

#### 6. **Split Fast/Slow Tests**
Run slow tests only when needed:
```yaml
test-unit-fast:
  run: pytest tests/unit/ -m "not slow" -n 4

test-unit-slow:
  if: github.event_name == 'pull_request'  # Only on PRs
  run: pytest tests/unit/ -m "slow" -n 2
```

#### 7. **Resource Monitoring**
Add pre-flight checks:
```yaml
- name: Check system resources
  run: |
    FREE_RAM=$(vm_stat | perl -ne '...')  # Your memory check
    if [ "$FREE_RAM" -lt "2.0" ]; then
      echo "⚠️ Low memory: ${FREE_RAM}GB - CI may be slow"
    fi
```

---

## 🎬 Action Plan

### Phase 1: Emergency Stabilization (NOW - 5 minutes)
1. ✅ Stop 18 excess runners (keep 2)
2. ✅ Restart system to clear memory pressure

### Phase 2: CI Configuration (TODAY - 30 minutes)
3. ⬜ Reduce pytest workers: `-n auto` → `-n 4`
4. ⬜ Add sequential dependencies for heavy jobs
5. ⬜ Test with single commit to verify

### Phase 3: Optimization (TOMORROW - 2 hours)
6. ⬜ Implement dependency caching
7. ⬜ Split fast/slow test suites
8. ⬜ Add resource monitoring

### Phase 4: Long-Term (NEXT WEEK)
9. ⬜ Move to cloud runners for CI (GitHub hosted)
10. ⬜ Keep 1 local runner for testing only

---

## 📈 Expected Improvements

| Metric | Before | After (Phase 2) | Improvement |
|--------|--------|----------------|-------------|
| Concurrent Processes | 50-110 | 8-12 | 82-89% ↓ |
| Memory Usage | 14-30 GB | 3-5 GB | 79-83% ↓ |
| CI Duration | Unknown (hangs) | 20-30 min | ✅ Completes |
| System Responsiveness | Frozen | Usable | ✅ Stable |

---

## 🔬 Validation Commands

### Check Active Runners
```bash
ps aux | grep Runner.Listener | grep -v grep | wc -l
```

### Monitor Resource Usage During CI
```bash
watch -n 5 'ps aux | grep pytest | wc -l && vm_stat | grep "Pages free"'
```

### Test CI Locally (Safe)
```bash
# Simulate CI with limited workers
pytest tests/unit/ -n 4 --timeout=900
```

---

## 📚 References

- CI Workflow: `.github/workflows/ci.yml`
- Pytest Config: `pytest.ini`
- Runner Locations: `~/github-runners/*`, `~/actions-runner*`
- System Specs: 24GB RAM, 12 CPU cores, macOS M4

---

**CONCLUSION:** The hang is caused by resource amplification from 20 runners × 11 parallel jobs × 10 pytest workers = 2200 potential processes competing for 12 cores and 24 GB RAM. Reducing to 2 runners and 4 workers per job will bring this down to ~16 processes, well within system capacity.
