# CI Infrastructure Documentation

## Overview

This CI runs on self-hosted GitHub Actions runners using Colima VMs for Docker containerization. The infrastructure has been hardened to prevent recurring failures from VM conflicts, OOM errors, and network corruption.

## Architecture

### VM Profile Strategy

**CRITICAL FIX (2026-01-18):** Sequential VM startup prevents Lima network corruption

Previous attempts at parallel VM startup caused 80% of CI failures due to:
1. Lima network state corruption from simultaneous VM initialization
2. Race conditions in QEMU process creation
3. Socket file conflicts between profiles

**Current Solution:** Sequential startup in `docker-setup` job
1. Start `ci-postgresql` profile (4GB)
2. Verify full health with test container
3. Start `ci-other` profile (8GB)
4. Verify full health with test container
5. Pre-pull images to both VMs
6. Integration shards can now run in parallel using pre-started VMs

### VM Memory Allocation

| Profile | Memory | Purpose | Containers | Workers |
|---------|--------|---------|------------|---------|
| `ci-postgresql` | 4GB | PostgreSQL-focused tests | Qdrant + PostgreSQL | 4 |
| `ci-other` | 8GB | Remaining integration tests | Qdrant + PostgreSQL | 1 |

**Why this works:**
- PostgreSQL shard doesn't need the 2GB embedding model (uses fixture optimization)
- Other shard loads embedding model once (single worker prevents 4x model load)
- Total memory: 12GB fits in 24GB runner with headroom

### Container Port Isolation

All CI variants use unique ports to prevent conflicts:

| Variant | Qdrant Port | PostgreSQL Port | Use Case |
|---------|-------------|-----------------|----------|
| `test` | 6335 | 5433 | Unit/integration tests |
| `agentic` | 6337 | 5438 | Agentic workflow tests |
| `discovery` | 6339 | 5434 | Discovery tests |
| `burnin` | 6340 | 5435 | Burn-in tests |
| `shard-postgresql` | 6342 | 5437 | PostgreSQL integration shard |
| `shard-other` | 6343 | 5439 | Other integration shard |

**Source of truth:** `scripts/ci/container-config.sh`

## CI Workflow Jobs

### 1. lint-gate
- **Purpose:** Fast code quality checks
- **Duration:** <2 minutes
- **Runs on:** All pushes/PRs
- **Checks:** ruff, black, file sizes, mock coverage

### 2. validate
- **Purpose:** Unit tests + type checking
- **Duration:** <10 minutes
- **Runs on:** All pushes/PRs (after lint-gate)
- **Tests:** Unit tests only (no containers)

### 3. docker-setup (NEW)
- **Purpose:** Sequential Colima VM startup with health verification
- **Duration:** 5-10 minutes
- **Runs on:** Push to main + manual workflow_dispatch
- **Steps:**
  1. Pre-emptive cleanup (kill zombies, stop CI profiles)
  2. Start `ci-postgresql` VM with retry logic
  3. Verify VM health (Docker daemon + test container)
  4. Start `ci-other` VM with retry logic
  5. Verify VM health (Docker daemon + test container)
  6. Pre-pull images to both VMs
  7. Summary of running profiles

### 4. integration (Sharded)
- **Purpose:** Full integration tests
- **Duration:** 20-30 minutes (parallel)
- **Runs on:** Push to main + manual workflow_dispatch
- **Shards:**
  - `postgresql`: ~230 tests, 4 workers, no embedding model
  - `other`: ~660 tests, 1 worker, embedding model required

**Key Change:** No longer starts VMs (uses pre-started VMs from docker-setup)

### 5. integration-aggregate
- **Purpose:** Merge JUnit reports from shards
- **Duration:** <1 minute
- **Runs on:** After integration shards complete

### 6. accuracy-gate
- **Purpose:** NFR6/NFR7 validation (>=70% accuracy)
- **Duration:** ~45 minutes
- **Runs on:** Push to main + manual workflow_dispatch
- **Uses:** `ci-postgresql` profile (8GB)

## Common Failure Modes

### 1. Lima Network Corruption
**Symptoms:**
- `user-v2_ep.sock not found` errors
- Container network failures
- `docker run` hangs indefinitely

**Fix:**
```bash
rm -rf ~/.colima/_lima/_networks
colima restart -p <profile>
```

### 2. Zombie VM State
**Symptoms:**
- Socket exists but `docker info` hangs
- `colima status` shows "running" but VM is unresponsive
- Test containers fail to start

**Fix:**
```bash
# Use health verification script
scripts/ci/verify-colima-health.sh <profile>

# Force restart if zombie detected
colima stop -p <profile> -f
colima delete -p <profile> -f
colima start -p <profile> --cpu 2 --memory 8 --runtime docker
```

### 3. OOM Errors
**Symptoms:**
- Container exits with code 137
- Tests fail with "out of memory"
- VM becomes unresponsive during heavy load

**Prevention:**
- Container memory limits enforced in `docker-compose.yml`
- VM memory checked before starting tests
- PostgreSQL shard uses 4 workers (not 8) to reduce memory pressure

### 4. Port Conflicts
**Symptoms:**
- "port already in use" errors
- Containers fail to start with bind errors

**Fix:**
```bash
# Kill process using the port
lsof -ti :<port> | xargs kill -9

# Or use emergency stop
./scripts/ci/colima-emergency-stop.sh
```

## Maintenance Scripts

### Health Verification
```bash
scripts/ci/verify-colima-health.sh <profile>
```
Checks:
- Docker daemon responsiveness (zombie detection)
- VM memory usage
- Network connectivity
- Zombie process count

### Emergency Stop
```bash
scripts/ci/colima-emergency-stop.sh [--force]
```
Gracefully stops CI Colima profiles. Use `--force` to kill stuck QEMU processes.

### Container Cleanup
```bash
scripts/ci/cleanup-test-containers.sh <variant>
```
Stops and removes containers for a specific variant.

## CI Credentials

**Source of truth:** `scripts/ci/container-config.sh`

All CI jobs use these credentials (hardcoding in workflows is forbidden):
- User: `raglite_ci`
- Password: `raglite_ci`
- Database: `raglite_ci`

**Validation:**
```bash
source scripts/ci/container-config.sh
validate_ci_credentials .github/workflows/ci.yml
```

## Manual Workflow Dispatch

### Rerun Modes (Selective Execution)
- `full`: Run all jobs (default)
- `integration`: Only integration tests (skip lint/validate)
- `lint`: Only linting
- `validate`: Only unit tests + type checking
- `accuracy`: Only accuracy gate

### Integration Shard Selection
- `all`: Run all integration shards (default)
- `postgresql`: Only PostgreSQL-focused tests
- `other`: Only remaining integration tests
- `none`: Skip integration tests

## Performance Metrics

### Target Durations
| Job | Target | Actual (avg) |
|-----|--------|--------------|
| lint-gate | <2 min | ~1 min |
| validate | <10 min | ~8 min |
| docker-setup | <15 min | ~10 min |
| integration (postgresql) | 20-25 min | ~22 min |
| integration (other) | 25-30 min | ~27 min |
| accuracy-gate | <45 min | ~40 min |

### Memory Usage
| Profile | VM Memory | Container Limits | Actual Usage |
|---------|-----------|------------------|--------------|
| ci-postgresql | 4GB | Qdrant: 1GB, PG: 512MB | ~2.5GB |
| ci-other | 8GB | Qdrant: 1GB, PG: 512MB | ~4.5GB (with model) |

## Troubleshooting Guide

### CI is stuck at "Starting Colima..."
**Cause:** Lima network corruption or QEMU deadlock

**Diagnosis:**
```bash
# Check Colima status
colima list

# Check for zombie processes
ps aux | grep -i defunct

# Check Lima network
ls -la ~/.colima/_lima/_networks
```

**Fix:**
```bash
# Emergency stop
./scripts/ci/colima-emergency-stop.sh --force

# Clean network state
rm -rf ~/.colima/_lima/_networks

# Retry job
```

### Integration tests fail with "connection refused"
**Cause:** Container health check failed

**Diagnosis:**
```bash
# Check container status
docker ps -a

# Check container logs
docker logs <container-name>

# Check ports
lsof -i :<port>
```

**Fix:**
```bash
# Stop containers
./scripts/ci/cleanup-test-containers.sh <variant>

# Free ports if needed
lsof -ti :<port> | xargs kill -9

# Restart containers
./scripts/ci/start-test-containers.sh <variant>
```

### Tests fail with "out of memory"
**Cause:** Memory limit exceeded (VM or container)

**Diagnosis:**
```bash
# Check VM memory
docker info | grep "Total Memory"

# Check container limits
docker inspect <container> | grep -A 5 "Memory"

# Check macOS memory
vm_stat
```

**Fix:**
- Reduce worker count in CI workflow
- Increase VM memory allocation
- Reduce container memory limits in `docker-compose.yml`

## References

- **Main workflow:** `.github/workflows/ci.yml`
- **Container config:** `scripts/ci/container-config.sh`
- **Docker preflight:** `.github/actions/docker-preflight/action.yml`
- **Health verification:** `scripts/ci/verify-colima-health.sh`
- **Emergency stop:** `scripts/ci/colima-emergency-stop.sh`
