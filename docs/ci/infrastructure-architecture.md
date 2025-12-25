# CI Infrastructure Architecture

Comprehensive reference for RAGLite CI/CD system design and component interactions.

**Last Updated:** 2025-12-24
**Architecture Version:** 2.0 (Multi-container with isolation)
**CI Jobs:** 6 major workflows
**Containers:** 2 shared (production), 6+ ephemeral (CI)

---

## Executive Summary

RAGLite uses a **containerized CI strategy** with isolated databases for each job type and aggressive health checking to prevent race conditions. The architecture prioritizes **reliability over speed** through sequential test execution and explicit resource management.

### Key Principles

1. **Test Isolation** - Each CI job gets unique database ports
2. **Infrastructure-as-Code** - All setup defined in docker-compose.yml and .github/workflows
3. **Explicit over Implicit** - No magic; health checks validate every assumption
4. **Fail Fast** - Early validation prevents cascading failures

---

## Container Naming Convention

Standard container naming enables scripts to manage lifecycle and debugging.

### Production Containers (Always Running)

| Container Name | Service | Port | Purpose | Data Persistence |
|---|---|---|---|---|
| `raglite-qdrant` | Qdrant Vector DB | 6333 | Production vector search | Persistent (qdrant_storage/) |
| `raglite-postgresql` | PostgreSQL | 5432 | Production relational DB | Persistent (postgresql_data/) |

**Lifespan:** Started by `docker-compose up`, persist across CI runs

### Test Containers (CI Jobs)

| Container Name | Service | Port | Purpose | Data Persistence |
|---|---|---|---|---|
| `raglite-qdrant-test` | Qdrant Vector DB | 6335 | Integration/unit tests | Ephemeral (qdrant_storage_test/) |
| `raglite-postgresql-test` | PostgreSQL | 5433 | Integration/unit tests | Ephemeral (postgresql_data_test/) |

**Lifespan:** Created by `docker-compose up -d`, reused across test runs

### CI Job-Specific Containers (On Demand)

| Container Name | Service | Port | Job | Cleanup |
|---|---|---|---|---|
| `raglite-postgresql-discovery` | PostgreSQL | 5434 | Test Discovery | After job completes |
| `raglite-postgresql-burnin` | PostgreSQL | 5435 | Burn-in Loop | After job completes |
| `raglite-postgresql-agentic` | PostgreSQL | 5438 | Agentic Workflow | After job completes |

**Lifespan:** Created at job start, destroyed at job end

---

## Port Allocation Strategy

Centralized port mapping prevents conflicts and enables concurrent execution.

### Port Ranges

```
Standard PostgreSQL range: 5432-5438
Standard Qdrant range: 6333-6339
```

### Current Allocation

| Service | Environment | Port | Host Mapping | Purpose | Concurrency |
|---|---|---|---|---|---|
| **PostgreSQL** | | | | | |
| | Production | 5432 | localhost:5432 | Main database | -1 |
| | Test (default) | 5433 | localhost:5433 | Integration tests | 1 (sequential) |
| | Discovery job | 5434 | localhost:5434 | Pytest collection | 1 per run |
| | Burnin job | 5435 | localhost:5435 | Reliability testing | 1 per run |
| | Agentic job | 5438 | localhost:5438 | Agentic workflow | 1 per run |
| **Qdrant** | | | | | |
| | Production | 6333 | localhost:6333 | Main database | -1 |
| | Test (default) | 6335 | localhost:6335 | Integration tests | 1 (sequential) |
| | Discovery job | 6339 | localhost:6339 | Collection validation | 1 per run |

### Why Isolated Ports

1. **Parallel Job Safety** - Different jobs can't interfere
2. **Manual Testing** - Can run local tests while CI runs
3. **Container Reuse** - Default test containers persist between runs
4. **Explicit Resource Bounds** - Each job claims explicit ports upfront

---

## Health Check Mechanisms

All services must pass explicit health checks before tests run.

### PostgreSQL Health Checks

#### pg_isready (Connection Availability)

```bash
# Basic readiness check
docker exec <container> pg_isready -U raglite_ci -d raglite_ci -h localhost

# Output: "accepting connections" = PASS
# Output: "rejecting connections" = FAIL
# Output: "no attempt" = FAIL
```

**When it's called:**
- Before each CI job
- During test container restart (auto-recovery fixture)
- In diagnostic scripts

**Timeout:** 30 attempts × 0.5s = 15 seconds

#### Connection String Test

```bash
# Verify credentials work
docker exec <container> psql -U raglite_ci -d raglite_ci -c "SELECT 1"

# Output: "1" = PASS
# Output: "error" = FAIL
```

**When it's called:**
- During database initialization
- In manual diagnostics
- Test startup (each test harness)

### Qdrant Health Checks

#### HTTP Health Endpoint

```bash
# REST API health check
curl -s http://localhost:6335/health

# Expected response: {"status":"ok", "version":"1.15.0", ...}
```

**When it's called:**
- Before integration test suite starts
- In diagnostic scripts
- Test startup (collection validation)

**Timeout:** 30 seconds

#### Collection Accessibility Check

```bash
# Verify collection can be queried
curl -s -X POST http://localhost:6335/collections/_test_financial_docs/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 1}'

# Expected: Point data returned
```

**When it's called:**
- During test setup
- After ingestion (baseline validation)
- Collection isolation fixture

---

## CI Job Dependency Graph

Workflows execute in strict order with health checks between stages.

### Workflow: `ci.yml` (Main CI)

```
┌─────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE VERIFICATION                                 │
├─────────────────────────────────────────────────────────────┤
│ [1] docker-health-check (5 min timeout)                     │
│     - Checks docker daemon                                  │
│     - Validates docker context                              │
│     └─ Outputs: docker-available=true/false                │
└─────────────────────────────────────────────────────────────┘
         │
         └─ If docker-available=false, all subsequent jobs SKIP
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ TEST DISCOVERY & VALIDATION                                 │
├─────────────────────────────────────────────────────────────┤
│ [2] test-discovery (20 min timeout)                         │
│     - pytest --collect-only                                 │
│     - Validates 300-5000 tests found                        │
│     - Checks markers (@pytest.mark.slow, etc)               │
│     └─ Dependency: docker-available=true                    │
└─────────────────────────────────────────────────────────────┘
         │
         └─ If collection fails (0 tests), job FAILS
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ UNIT TESTS                                                  │
├─────────────────────────────────────────────────────────────┤
│ [3] unit-tests (15 min timeout)                             │
│     - pytest tests/unit/                                    │
│     - 200+ pure unit tests                                  │
│     - No external dependencies                              │
│     └─ Dependency: docker-available=true                    │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ INTEGRATION TESTS (SEQUENTIAL)                              │
├─────────────────────────────────────────────────────────────┤
│ [4] integration-tests (45 min timeout)                      │
│     - docker-compose up qdrant-test postgresql-test        │
│     - pg_isready health check                               │
│     - qdrant /health check                                  │
│     - pytest tests/integration/ -n 0 (SEQUENTIAL!)          │
│     - 115+ tests with shared Qdrant collection              │
│     └─ Dependency: docker-available=true                    │
│     └─ Critical: -n 0 prevents pytest-xdist conflicts       │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ E2E TESTS                                                   │
├─────────────────────────────────────────────────────────────┤
│ [5] e2e-tests (30 min timeout)                              │
│     - pytest tests/e2e/                                     │
│     - 28+ end-to-end tests                                  │
│     - Full system validation                                │
│     └─ Dependency: docker-available=true                    │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ CODE QUALITY                                                │
├─────────────────────────────────────────────────────────────┤
│ [6] quality-checks (10 min timeout)                         │
│     - ruff lint / black format                              │
│     - mypy type checking                                    │
│     - bandit security scan                                  │
│     - Coverage validation (80%+)                            │
│     └─ Dependency: None (runs in parallel)                  │
└─────────────────────────────────────────────────────────────┘
```

### Parallel Execution Levels

```
Parallelizable (no dependencies):
  - [1] docker-health-check
  - [6] quality-checks (parallel with everything)

Sequential (depends on docker availability):
  - [2] test-discovery
  - [3] unit-tests        } Can run parallel
  - [4] integration-tests } Separate jobs, same runner
  - [5] e2e-tests

Within Integration Tests:
  - Thread pool: 1 (sequential, no -n flag)
  - Async: Inherent concurrency within single event loop
  - Purpose: Prevent pytest-xdist worker conflicts
```

---

## Service Lifecycle Timeline

Sequence of events when CI job starts and how services reach steady state.

### Integration Test Job Timeline (Sample)

```
Time  Event                                Status
────────────────────────────────────────────────────────────────
 0s   Job starts on runner                 Queued
 +2s  Checkout code                        Checked out
 +5s  Setup UV                             Installed
 +10s docker-compose up postgresql-test    Starting
       docker-compose up qdrant-test

 +12s pg_isready check (retry 1/30)       Attempting...
 +13s pg_isready check (retry 2/30)       Attempting...
 +14s pg_isready check (retry 3/30)       Attempting...
 +15s pg_isready check (retry 4/30)       SUCCESS ✓

 +18s qdrant /health check (retry 1/30)   Attempting...
 +20s qdrant /health check (retry 2/30)   SUCCESS ✓

 +22s Initialize database schema           Executing...
 +25s pytest --collect-only                Validating collection

 +30s pytest tests/integration/ -n 0       Running tests...

 +60s Ingestion complete (PDF ingestion)   Baseline loaded
 +75s Read-only tests executing            Tests running...

+1200s (20m) Integration tests complete   PASS/FAIL
```

### Container Startup Sequence Detail

```
Step 1: docker-compose up command issued
        ├─ Container created from image
        ├─ Network configured
        ├─ Volumes mounted
        └─ Entrypoint script starts

Step 2: Container initialization (2-5 seconds)
        ├─ PostgreSQL: Data directory validation
        ├─ PostgreSQL: WAL recovery (if needed)
        ├─ PostgreSQL: Extension loading
        └─ Qdrant: Vector index initialization

Step 3: Service port binding (< 1 second)
        ├─ TCP socket binding
        ├─ Port allocation
        └─ Network interface ready

Step 4: Service startup (depends on service)
        ├─ PostgreSQL: LISTEN on 5433
        ├─ Qdrant: HTTP server on 6335
        └─ gRPC server (6336 for Qdrant)

Step 5: Health check passes (< 100ms per check)
        ├─ pg_isready returns "accepting connections"
        ├─ qdrant /health returns 200 OK
        └─ Test suite proceeds
```

---

## Environment Variable Configuration

Settings that control CI behavior, propagated to containers and test processes.

### Job-Level Environment (Inherited by All Steps)

```yaml
# In .github/workflows/ci.yml
jobs:
  test-job:
    env:
      APP_ENV: test                    # Forces test database ports
      CI: "true"                       # GitHub Actions flag
```

### Test Container Environment (docker-compose.yml)

```yaml
# PostgreSQL test service
postgresql-test:
  environment:
    - POSTGRES_DB=raglite_ci           # Database name
    - POSTGRES_USER=raglite_ci         # Username
    - POSTGRES_PASSWORD=raglite_ci     # Password (test-only!)
```

### Test Process Environment (tests/conftest.py)

```python
# Set BEFORE any raglite imports
os.environ["APP_ENV"] = "test"
os.environ["POSTGRES_PORT"] = "5433"
os.environ["POSTGRES_DB"] = "raglite_ci"
os.environ["POSTGRES_USER"] = "raglite_ci"
os.environ["POSTGRES_PASSWORD"] = "raglite_ci"
os.environ["TESTING"] = "true"
```

### Settings Singleton Initialization

```python
# In raglite/shared/config.py
class Settings(BaseSettings):
    def __init__(self):
        super().__init__()
        self.adjust_for_environment()  # Auto-adjust ports based on APP_ENV

    def adjust_for_environment(self):
        """Auto-adjust Qdrant port based on APP_ENV"""
        if self.app_env == "test":
            self.qdrant_port = 6335  # Override with test port
            self.qdrant_url = "http://localhost:6335"
```

### Environment Variable Flow

```
┌─────────────────────────────────────────┐
│ .github/workflows/ci.yml                │
│ env: { APP_ENV: test, CI: "true" }      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ GitHub Actions Step                     │
│ run: uv run pytest tests/               │
└──────────────┬──────────────────────────┘
               │ (inherits APP_ENV=test)
               ▼
┌─────────────────────────────────────────┐
│ tests/conftest.py (module level)        │
│ os.environ["APP_ENV"] = "test"          │
│ os.environ["POSTGRES_*"] = "raglite_ci" │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ raglite/shared/config.py                │
│ class Settings:                         │
│   qdrant_port = 6335 (test)            │
│   postgres_port = 5433 (test)          │
└─────────────────────────────────────────┘
```

---

## Database Schema and Initialization

Test databases must be initialized with all tables before integration tests run.

### Schema Initialization Script

Located at: `scripts/init-test-postgresql.py`

```python
# What it creates:
# 1. financial_chunks      - RAG document chunks
# 2. financial_tables      - Structured tabular data
# 3. entity_mappings       - Entity resolution cache
# 4. model_selection       - Story 7b-4 cache
# 5. model_weights         - Story 6.12 ensemble
# 6. external_data_sources - Regressors/features
# 7. model_registry        - Model metadata

# When it's called:
# 1. During CI job (before integration tests)
# 2. During container auto-restart (ensure_test_infrastructure fixture)
# 3. Manual setup: APP_ENV=test uv run python scripts/init-test-postgresql.py
```

### Database Connection Pool Configuration

```python
# In raglite/shared/database.py (pseudo-code)
if settings.app_env == "test":
    # Test config: smaller pools, aggressive cleanup
    pool_size = 5
    max_overflow = 10
    pool_recycle = 300  # Recycle connections every 5 minutes
    echo = False        # Disable SQL logging
else:
    # Production config: larger pools, persistent connections
    pool_size = 20
    max_overflow = 40
    pool_recycle = 3600  # Recycle every hour
    echo = False
```

---

## Container Resource Limits

Memory and CPU constraints to prevent resource exhaustion.

### Memory Limits (docker-compose.yml)

```yaml
# Test Qdrant (max 1GB)
qdrant-test:
  deploy:
    resources:
      limits:
        memory: 1G

# Test PostgreSQL (max 512MB, includes shared memory)
postgresql-test:
  deploy:
    resources:
      limits:
        memory: 512M
  shm_size: 256m  # Shared memory for VACUUM operations
```

### Justification

```
Runner Total Memory: 7 GB (M1 macOS)
├─ OS: ~1 GB
├─ Docker: ~500 MB
├─ Qdrant: 1 GB
├─ PostgreSQL: 512 MB
├─ Python/test process: ~2 GB
└─ Buffer: ~2 GB
```

### OOM Prevention

If test process gets OOM killed:

1. Check memory usage: `docker stats`
2. Reduce test parallelization (already at -n 0)
3. Split large test files
4. Enable memory limits on production containers

---

## Cleanup and Teardown

What happens when CI job completes.

### On Job Success

```yaml
- name: Stop test containers
  if: success() || failure()
  run: docker-compose down -v

# Removes: containers, volumes (ephemeral data)
# Preserves: images, production data
```

### On Job Failure

```yaml
- name: Collect logs on failure
  if: failure()
  run: |
    docker logs raglite-postgresql-test >> logs/postgresql.log
    docker logs raglite-qdrant-test >> logs/qdrant.log

- name: Clean up containers
  if: always()
  run: docker-compose down -v
```

### Volume Cleanup Strategy

```
✓ Ephemeral volumes (test data) - DELETED after job
  └─ qdrant_storage_test/
  └─ postgresql_data_test/

✗ Production volumes - PRESERVED after job
  └─ qdrant_storage/
  └─ postgresql_data/
```

---

## Concurrent Execution Model

How multiple CI jobs interact without interference.

### Self-Hosted Runner Configuration

```yaml
# In .github/workflows/ci.yml
runs-on: [self-hosted, raglite]

# Runner label: "raglite" (dedicated to this project)
# Prevents: Cross-project resource contention
# Runner count: 2 raglite-dedicated runners
```

### Job Concurrency

```
Max concurrent jobs: 2 (per GitHub Actions plan)

Scenario 1: Main branch PR
  ├─ PR trigger: ci.yml runs
  └─ Push to main: ci.yml runs (queued if same runner busy)

Scenario 2: Multiple PRs
  ├─ PR #1 on runner-1
  ├─ PR #2 on runner-2
  └─ Jobs execute in parallel with isolated ports
```

### Resource Isolation Table

| Resource | Job 1 | Job 2 | Conflict? |
|----------|-------|-------|-----------|
| PostgreSQL port | 5433 | 5433 | No (same runner exclusive) |
| Qdrant port | 6335 | 6335 | No (same runner exclusive) |
| CPU cores | 4/8 | 4/8 | Possible (shared runner) |
| Memory | 2/7 GB | 2/7 GB | Possible (shared runner) |

**Key:** Jobs on same runner use same ports (sequential). Jobs on different runners use same ports (no conflict because different host).

---

## pytest Configuration

How test execution is configured in pytest.ini.

```ini
[pytest]
# Default markers (prevent unknown marker error)
markers =
    slow: marks tests as slow (excluded from default runs)
    integration: requires Qdrant/PostgreSQL
    manages_collection_state: test modifies collection
    preserve_collection: test is read-only
    asyncio: async test
    health_check: infrastructure health validation

# Default test discovery filters
addopts = -m "not slow and not health_check"

# Async configuration
asyncio_mode = auto

# Strict marker checking (unknown markers = error)
--strict-markers

# Verbose output
-v
```

### How It Affects Test Execution

```bash
# Default (local/CI): Excludes slow tests
uv run pytest tests/
# Runs: unit + integration (fast) + e2e
# Excludes: @pytest.mark.slow, @pytest.mark.health_check

# Include slow tests
uv run pytest tests/ -m ""
# Runs: ALL tests including slow

# Only slow tests
uv run pytest tests/ -m "slow"
# Runs: ONLY @pytest.mark.slow tests

# Override default markers
uv run pytest tests/ -m "not slow"
# Runs: Same as default
```

---

## Debugging and Observability

How to monitor and troubleshoot CI infrastructure.

### Log Locations

```
Container Logs:
  docker logs raglite-postgresql-test
  docker logs raglite-qdrant-test

pytest Output:
  STDOUT/STDERR in job logs
  --tb=short for readable tracebacks

GitHub Actions Artifacts:
  Uploaded by 'Upload logs on failure' step
  Available in 'Actions' tab
```

### Key Metrics to Monitor

1. **Container startup time**
   - Target: <5s total
   - Alarm: >15s indicates slow runner or Docker issue

2. **Test collection time**
   - Target: <10s
   - Alarm: >30s indicates import/conftest issues

3. **Integration test duration**
   - Target: <15 minutes (with 10-page PDF ingestion)
   - Alarm: >20 minutes indicates performance regression

4. **Health check pass rate**
   - Target: 100%
   - Alarm: <98% indicates flaky infrastructure

### Diagnostic Commands

```bash
# Container status
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Memory usage
docker stats --no-stream raglite-postgresql-test raglite-qdrant-test

# Network connectivity
docker network inspect bridge

# Process health
ps aux | grep -E "postgres|qdrant"

# Port occupancy
lsof -i :5433 -i :6335
```

---

## Architecture Decisions and Rationale

Why we made specific choices for CI infrastructure.

### Decision 1: Sequential Test Execution (pytest -n 0)

**Choice:** Sequential execution for integration tests

**Rationale:**
- pytest-xdist creates separate worker processes
- Session fixtures don't work across workers
- Qdrant collection state is not process-safe
- Sequential is slower but more reliable

**Alternative Rejected:** Parallel execution with pytest-xdist
- Faster (20% speedup)
- But requires worker-safe fixtures (complex)
- And requires process-safe collection (not guaranteed)

### Decision 2: Isolated Container Ports

**Choice:** Each CI job gets unique PostgreSQL port

**Rationale:**
- Prevents port conflicts between parallel jobs
- Enables concurrent execution on same runner
- Makes debugging easier (port → job mapping)
- No socket cleanup delays

**Alternative Rejected:** Port reuse with container cleanup
- Faster (no new container creation)
- But requires reliable cleanup
- Socket cleanup can take 10+ seconds (TIME_WAIT)
- More failure-prone

### Decision 3: Health Check Before Tests

**Choice:** Mandatory pg_isready and /health checks

**Rationale:**
- Prevents flaky test failures
- Clear failure point (infrastructure vs tests)
- Faster debugging (is container ready?)
- Cost: +5 seconds per job

**Alternative Rejected:** Implicit health assumptions
- Faster startup (no checks)
- But causes sporadic failures
- Hard to debug (network? container? test?)

### Decision 4: Persistent Test Containers

**Choice:** Keep test containers running between CI jobs

**Rationale:**
- Faster second run (no container startup)
- Reuse network configuration
- Preserve test database data for debugging
- Cost: Small disk/memory footprint

**Alternative Rejected:** Fresh containers per job
- Clean state (guarantees)
- But slower (30s+ container creation)
- Can't debug previous test runs
- Higher resource overhead

---

## Future Improvements

Potential enhancements to CI infrastructure.

### Short Term (Next 2 Months)

1. **Container restart as fixture**
   - Auto-restart if container stops mid-suite
   - Currently manual recovery required

2. **Distributed test execution**
   - Run tests on multiple runners
   - Requires shared database/Qdrant
   - Or test data partitioning

3. **Test performance dashboard**
   - Track CI timing trends
   - Alert on regressions (>20% slowdown)
   - Identify bottleneck tests

### Medium Term (2-4 Months)

1. **Container orchestration**
   - Use Docker Swarm or Kubernetes for CI
   - Better resource management
   - Automatic restart/recovery

2. **Smart test selection**
   - Run only affected tests (monorepo pattern)
   - Skip tests if code changes are doc-only

3. **Test result caching**
   - Cache test results for unchanged code
   - Reuse for dependent jobs

### Long Term (4+ Months)

1. **Cost optimization**
   - Analyze compute hours spent
   - Parallelize slow test suites
   - Reduce container startup overhead

2. **Developer experience**
   - Local CI simulation (run exact CI commands locally)
   - Faster feedback loop
   - Better error messages

3. **Production integration**
   - Deploy from CI (AWS ECS)
   - Infrastructure-as-Code for production
   - Automatic rollback on test failure

---

## Disaster Recovery

What to do if CI infrastructure breaks.

### Container Won't Start

```bash
# Check logs
docker logs raglite-postgresql-test

# Remove and recreate
docker rm raglite-postgresql-test
docker-compose up -d postgresql-test

# Initialize schema
APP_ENV=test uv run python scripts/init-test-postgresql.py
```

### Port Already in Use

```bash
# Find process
lsof -i :5433

# Kill it
kill -9 <PID>

# Wait and restart container
sleep 3
docker-compose up -d postgresql-test
```

### Docker Daemon Crashed

```bash
# Restart Docker
docker context ls  # Verify daemon is running

# Or on macOS
open -a Docker
sleep 30  # Wait for startup

# Verify containers
docker ps
```

### Lost Test Data

```bash
# Check volume
ls -la postgresql_data_test/

# If corrupted, delete and recreate
rm -rf postgresql_data_test/
docker rm raglite-postgresql-test
docker-compose up -d postgresql-test
APP_ENV=test uv run python scripts/init-test-postgresql.py
```

---

**Document Version:** 1.0
**Architecture Validated:** 2025-12-24
**Components Tested:** 12 major components
**Reliability Target:** 99% (1-2 unplanned restarts per month)
