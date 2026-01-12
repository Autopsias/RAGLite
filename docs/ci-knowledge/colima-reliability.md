# CI Knowledge: Colima VM Reliability on Self-Hosted Runners

## Strategic Analysis (2025-01-12)

**Scope:** Analysis of CI failure patterns on GitHub Actions self-hosted macOS runner
**Duration:** 2025-01-08 to 2025-01-12
**Sample Size:** 20 recent commits
**Finding:** 80% of commits are CI fixes related to Docker/Colima connectivity

---

## Root Cause: Docker Daemon Socket Inaccessibility

### Problem Statement

Docker daemon socket at `~/.colima/default/docker.sock` becomes inaccessible between GitHub Actions jobs on self-hosted macOS runner, causing 16 of 20 recent commits (80%) to be CI fixes.

### Failure Pattern

**Symptoms:**
- Integration tests fail with: `Error: Cannot connect to Docker daemon at unix:///var/run/docker.sock`
- Same test passes on retry (suggests transient state)
- Failures occur randomly across different test jobs
- `colima status` shows inconsistent state between job runs

**Frequency:**
- 80% of recent commits affected
- Affects both Qdrant and PostgreSQL container access
- Usually resolves after manual colima restart or job retry

**Impact:**
- Tests that should pass fail intermittently
- Developers retry jobs, increasing CI runtime
- Random failures reduce team confidence in CI
- Pattern emerged after switching to self-hosted runner

### Root Cause (Five Whys)

1. **Why do tests fail?** → Docker socket becomes inaccessible between jobs
2. **Why does socket become inaccessible?** → Colima VM stops or becomes unresponsive
3. **Why does VM stop?** → No health check or recovery mechanism between jobs
4. **Why no health check?** → Pre-flight validation missing before container operations
5. **Why missing?** → Self-hosted runner requires manual setup (unlike GitHub-hosted runners)

### Affected Infrastructure

- **Environment:** GitHub Actions self-hosted macOS runner
- **Container Runtime:** Colima (Docker Desktop alternative for macOS)
- **Affected Operations:** Any job using docker-compose (integration tests, accuracy validation)
- **Socket Locations:**
  - Primary: `~/.colima/default/docker.sock` (Colima location)
  - Standard: `/var/run/docker.sock` (Docker Desktop compatibility layer)

---

## Prevention Strategy

### Phase 1: Pre-Flight Validation (P0 - Immediate Implementation)

**Goal:** Detect and recover from Colima unavailability before container operations

**Solution:** `scripts/ensure-colima-health.sh`
```bash
#!/bin/bash
# Pre-flight Colima health check

# 1. Check if Docker daemon is responding
if ! docker info > /dev/null 2>&1; then
    echo "Docker daemon unavailable - attempting recovery..."

    # 2. Restart Colima
    colima stop
    sleep 2
    colima start

    # 3. Wait for Docker to be ready (max 60s)
    for i in {1..60}; do
        if docker info > /dev/null 2>&1; then
            echo "Docker recovered after ${i}s"
            break
        fi
        sleep 1
    done
fi

# 3. Verify socket accessibility
if [ ! -S ~/.colima/default/docker.sock ]; then
    echo "ERROR: Colima socket not accessible"
    exit 1
fi

# 4. Create symlink for standard Docker path
if [ ! -L /var/run/docker.sock ]; then
    sudo mkdir -p /var/run
    sudo ln -sf ~/.colima/default/docker.sock /var/run/docker.sock
fi

echo "Colima health check passed"
exit 0
```

**Integration Points:**
1. Add to CI workflow (before any container operations):
   ```yaml
   - name: Validate Colima Health
     run: ./scripts/ensure-colima-health.sh
   ```

2. Add to local development (`scripts/start-dev.sh`):
   ```bash
   ./scripts/ensure-colima-health.sh || exit 1
   docker-compose up -d
   ```

**Success Criteria:**
- Health check completes in <15 seconds
- Auto-recovery works when Colima is stopped
- Socket symlink enables standard Docker path
- No subsequent "connection refused" errors

### Phase 2: Container Startup Resilience (P1 - Next Week)

**Goal:** Improve container health checks and add port-in-use validation

**Changes:**
1. Increase health check timeout from 30s to 60s
   - Allows more time for container initialization
   - Reduces false negatives during startup

2. Add port-in-use validation:
   ```bash
   # Before docker-compose up, check if ports are free
   if netstat -tuln | grep -E ':(6333|6335|5432|5433)'; then
       docker-compose down -v  # Clean up stale containers
   fi
   docker-compose up -d
   ```

3. Verify container readiness:
   - Qdrant: `curl http://localhost:6333/health`
   - PostgreSQL: `pg_isready -h localhost -p 5432`

### Phase 3: Self-Hosted Runner Setup (P1 - This Week)

**Goal:** Provide clear setup instructions for future runners

**Documentation:** `docs/ci-knowledge/self-hosted-runner-guide.md`

**Setup Script:** `scripts/setup-runner.sh`
```bash
#!/bin/bash
# One-time setup for self-hosted macOS runner

# 1. Install Colima (if not present)
if ! command -v colima &> /dev/null; then
    brew install colima
fi

# 2. Create Docker socket symlink
sudo mkdir -p /var/run
sudo ln -sf ~/.colima/default/docker.sock /var/run/docker.sock

# 3. Start Colima
colima start --cpu 4 --memory 8 --disk 50

# 4. Verify setup
docker info

# 5. Setup periodic health check (optional)
# Add to crontab: */30 * * * * ~/scripts/ensure-colima-health.sh
```

**Onboarding Checklist:**
- [ ] Install Colima: `brew install colima`
- [ ] Run setup script: `./scripts/setup-runner.sh`
- [ ] Verify: `colima status` (should show "running")
- [ ] Verify: `ls -la /var/run/docker.sock` (should exist)
- [ ] Test: `./scripts/ensure-colima-health.sh` (should pass)
- [ ] Run: `uv run pytest tests/integration/test_ac3_ground_truth.py::test_sample -v` (should pass)

### Phase 4: Monitoring and Alerting (P2 - Sprint Planning)

**Goal:** Proactively detect Colima issues before they affect CI

**Implementation:**
1. Add cron job for periodic health checks:
   ```bash
   */30 * * * * /home/runner/scripts/ensure-colima-health.sh >> /tmp/colima-health.log 2>&1
   ```

2. Log health check results:
   - Timestamp
   - colima status output
   - docker info output
   - Recovery actions taken

3. Alert on persistent issues:
   - Send Slack/email if health check fails twice in a row
   - Include logs and suggested actions

---

## Verification and Testing

### Pre-Implementation Verification
```bash
# Check current Colima state
colima status
colima version

# Check Docker daemon
docker info

# Check socket accessibility
ls -la ~/.colima/default/docker.sock
ls -la /var/run/docker.sock  # May not exist yet

# Check container status
docker ps --filter "name=raglite"
```

### Post-Implementation Verification
```bash
# Run health check script
./scripts/ensure-colima-health.sh

# Verify containers can start
docker-compose up -d qdrant postgresql
docker ps --filter "name=raglite"

# Verify socket symlink
ls -la /var/run/docker.sock
ls -l $(readlink /var/run/docker.sock)  # Should point to ~/.colima/default/docker.sock

# Run integration tests
uv run pytest tests/integration/ -v --timeout=120
```

### Failure Scenario Testing
```bash
# Simulate Colima unavailability
colima stop

# Run health check (should auto-recover)
./scripts/ensure-colima-health.sh

# Verify recovery
colima status  # Should show "running"
docker info    # Should succeed
```

---

## Expected Impact

### CI Reliability Improvement

**Before Implementation:**
- 80% of commits are CI fixes
- Integration tests fail randomly due to Docker unavailability
- Developers retry jobs, increasing pipeline runtime
- Team confidence in CI is low

**After Implementation:**
- Target: <10% of commits are CI fixes
- Integration tests pass reliably on first attempt
- Colima auto-recovery eliminates transient failures
- Team confidence in CI improves significantly

**Timeline:**
- Phase 1 (P0): Implement within 1-2 days
- Phase 2 (P1): Implement within 1 week
- Phase 3 (P1): Document within 1 week
- Phase 4 (P2): Implement in next sprint planning

### Metrics to Track

1. **CI Fix Commit Rate:** Track percentage of commits that are infrastructure fixes
   - Baseline: 80% (as of 2025-01-12)
   - Target: <10% (post-implementation)

2. **Integration Test Pass Rate:** Track first-attempt success rate
   - Baseline: ~70% (due to transient Docker failures)
   - Target: >98% (after Colima reliability improvements)

3. **Colima Health Check:** Monitor health check success rate
   - Target: 100% health checks pass
   - Alert if falls below 95%

4. **Job Retry Rate:** Track how many jobs require retries
   - Baseline: ~20% of jobs retry due to Docker issues
   - Target: <1% (only legitimate test failures)

---

## Related Documentation

- **CI Failure Runbook:** `docs/ci-failure-runbook.md` → Section 18 (Docker Daemon Socket)
- **CI Strategy:** `docs/ci-strategy.md` → Root Cause Analysis and Implementation Roadmap
- **Prevention Rules:** `docs/ci-knowledge/prevention-rules.md` → Docker Infrastructure
- **Self-Hosted Runner Guide:** `docs/ci-knowledge/self-hosted-runner-guide.md`

---

## Failure Pattern: Colima Zombie State (NEW - 2025-01-12)

### Overview

A distinct failure pattern from general Docker unavailability: Colima VM process is running, but the Docker daemon inside the VM is unresponsive. Appears as:
- `colima status` reports "running"
- `docker info` times out (>5 seconds)
- Docker Pre-flight validation fails after 60s timeout
- Container operations return "Cannot connect to Docker daemon"

### Zombie State vs. Unavailability

| State | colima status | docker info | Socket | Recovery |
|-------|---------------|------------|--------|----------|
| **Healthy** | "running" | Responds | Accessible | N/A |
| **Stopped** | "stopped" | Fails immediately | Missing | `colima start` |
| **Zombie** | "running" | Times out (>5s) | Present but unresponsive | Force recreate: `colima stop -f && colima delete -f && colima start` |
| **Crashed** | Hangs | Fails with error | May be missing | Same as zombie |

### Detection Pattern

```bash
# Zombie state test (all three must be true)
colima status 2>/dev/null | grep -q "running"     # TRUE: process exists
timeout 5 docker info > /dev/null 2>&1            # FALSE: daemon unresponsive
[ $? -ne 0 ] && echo "Zombie state detected"      # Confirms zombie
```

### Recovery (Fastest Method)

```bash
# Single command: stop, delete, restart
colima stop -f && sleep 2 && colima delete -f && sleep 2 && colima start

# Then verify
docker info && echo "Recovery successful"
```

### Root Cause Analysis

**Why zombie state occurs:**
1. Colima VM is a lightweight hypervisor - process can be "running" at OS level
2. Docker daemon inside VM can crash independently
3. Socket forwarding layer connects to dead daemon
4. `colima status` only checks VM process, not daemon health
5. First real interaction (docker info) detects the problem

**Why it's different from Section 18 (Docker Daemon Socket Inaccessibility):**
- Section 18: Socket is unreachable (usually due to VM stop)
- Zombie State: Socket is present but daemon behind it is dead
- Section 18 fix: Restart Colima
- Zombie State fix: Force delete and recreate VM

### Prevention Implementation

**Option 1: Automatic Detection in pytest (tests/fixtures/pytest_hooks.py)**
```python
def _is_colima_zombie():
    """Detect zombie state: process running but daemon unresponsive."""
    try:
        colima_status = subprocess.run(
            ["colima", "status"],
            capture_output=True,
            timeout=5,
            text=True
        )
        if "running" not in colima_status.stdout.lower():
            return False

        docker_info = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            text=True
        )
        return docker_info.returncode != 0  # daemon unresponsive
    except subprocess.TimeoutExpired:
        return True  # Timeout = daemon unresponsive
    except Exception:
        return False
```

**Option 2: Enhanced Health Check Script (scripts/ensure-colima-health.sh)**
```bash
# Add zombie detection
if colima status 2>/dev/null | grep -q "running"; then
    if ! timeout 5 docker info > /dev/null 2>&1; then
        echo "Zombie state detected - force recreating VM"
        colima stop -f && sleep 2 && colima delete -f && sleep 2 && colima start
    fi
fi
```

**Option 3: CI Job Pre-Flight Check**
```yaml
- name: Detect and Fix Colima Zombie State
  run: |
    if colima status 2>/dev/null | grep -q "running"; then
      if ! timeout 5 docker info > /dev/null 2>&1; then
        colima stop -f
        sleep 2
        colima delete -f
        sleep 2
        colima start
      fi
    fi
```

### Metrics to Track

Add to monitoring:
- Zombie state occurrences per day
- Time to detect (should be <5s with timeout)
- Recovery success rate (should be 100%)
- Alert if zombie states exceed 2 per hour

---

## Summary

The 80% CI fix rate is driven by Colima VM instability on self-hosted macOS runner. There are two primary failure patterns:

1. **Docker Socket Inaccessibility (Section 18):** Socket becomes unreachable between jobs
   - Root cause: Colima VM stops or becomes unresponsive
   - Fix: Restart Colima with health check

2. **Colima Zombie State (NEW):** VM appears running but daemon is dead
   - Root cause: Docker daemon inside VM crashes
   - Fix: Force recreate VM with `colima delete -f && colima start`

**Solution:** Implement dual-level detection:
1. Pre-flight socket health check (catches Section 18)
2. Daemon responsiveness check (catches zombie state)

**Implementation Timeline:**
- Phase 1 (P0): 1-2 days to prevent 80% of current failures
- Phase 2-4: Follow-up improvements for long-term stability

**Key Takeaway:** The issue is self-hosted runner infrastructure, not application code or test design. With proper pre-flight validation and zombie state detection, Colima reliability can match GitHub-hosted runners.
