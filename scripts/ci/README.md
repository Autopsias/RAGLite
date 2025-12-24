# CI Container Management Scripts

Unified container management for CI test infrastructure.

## Overview

These scripts provide centralized container lifecycle management for CI jobs, replacing ~600 lines of inline Docker commands with reusable, parameterized scripts.

## Scripts

### container-config.sh

Centralized configuration for container ports and names.

**Port Assignments:**

| Variant | Qdrant | PostgreSQL | Use Case |
|---------|--------|------------|----------|
| test | 6335 | 5433 | Integration, E2E, Epic6 tests |
| agentic | 6337 | 5438 | Agentic workflow tests |
| discovery | 6339 | 5434 | Test discovery validation |
| burnin | 6340 | 5435 | Burn-in flaky test detection |

**Usage:**
```bash
source scripts/ci/container-config.sh
get_qdrant_port test      # Returns: 6335
get_postgres_port agentic  # Returns: 5438
```

### start-test-containers.sh

Start test containers for a specific variant.

**Usage:**
```bash
./scripts/ci/start-test-containers.sh VARIANT [OPTIONS]
```

**VARIANT (required):**
- `test` - Integration, E2E, Epic6 tests (ports 6335/5433)
- `agentic` - Agentic workflow tests (ports 6337/5438)
- `discovery` - Test discovery validation (ports 6339/5434)
- `burnin` - Burn-in tests (ports 6340/5435)

**OPTIONS:**
- `--qdrant-only` - Start only Qdrant container
- `--postgresql-only` - Start only PostgreSQL container
- `--skip-cleanup` - Skip nuclear cleanup step (faster for local testing)

**Exit Codes:**
- 0 - Success
- 1 - Invalid arguments
- 2 - Docker unavailable
- 3 - Qdrant startup failed
- 4 - PostgreSQL startup failed

**Examples:**
```bash
# Start all containers for test variant
./scripts/ci/start-test-containers.sh test

# Start only PostgreSQL for E2E tests
./scripts/ci/start-test-containers.sh test --postgresql-only

# Start containers without cleanup (faster for local dev)
./scripts/ci/start-test-containers.sh test --skip-cleanup
```

### cleanup-test-containers.sh

Clean up test containers after CI runs.

**Usage:**
```bash
./scripts/ci/cleanup-test-containers.sh VARIANT|all [--force]
```

**VARIANT:**
- `test`, `agentic`, `discovery`, `burnin` - Clean specific variant
- `all` - Clean all CI test containers

**Options:**
- `--force` - Force cleanup even if containers are running

**Examples:**
```bash
# Clean up test variant containers
./scripts/ci/cleanup-test-containers.sh test

# Clean up all CI containers (end of workflow)
./scripts/ci/cleanup-test-containers.sh all --force
```

### wait-for-service.sh

Health check helper for container startup verification.

**Usage:**
```bash
./scripts/ci/wait-for-service.sh SERVICE CONTAINER_NAME TIMEOUT
```

**Examples:**
```bash
# Wait for PostgreSQL to be ready
./scripts/ci/wait-for-service.sh postgresql raglite-postgresql-test 90

# Wait for Qdrant to be ready
./scripts/ci/wait-for-service.sh qdrant raglite-qdrant-test 30
```

## Production Safety

**CRITICAL:** These scripts are designed for CI test infrastructure only.

- Production ports 6333/5432 are NEVER used by CI
- Production containers (`raglite-qdrant`, `raglite-postgresql`) are NEVER touched
- All CI containers use unique names with variant suffix (e.g., `raglite-qdrant-test`)
- Port validation occurs at script load time

## CI Job Usage

Example CI job step:
```yaml
- name: Start Test Containers
  run: |
    chmod +x scripts/ci/start-test-containers.sh
    ./scripts/ci/start-test-containers.sh test
    source .ci-env
```

The `.ci-env` file exports environment variables:
```bash
export QDRANT_PORT=6335
export POSTGRES_PORT=5433
export QDRANT_CONTAINER=raglite-qdrant-test
export POSTGRES_CONTAINER=raglite-postgresql-test
export VARIANT=test
export APP_ENV=test
```

## Troubleshooting

### Port Conflicts

If a port is already in use:
```bash
# Check what's using the port
lsof -i :6335

# Force cleanup of all CI containers
./scripts/ci/cleanup-test-containers.sh all --force
```

### Container Not Starting

Check container logs:
```bash
docker logs raglite-qdrant-test --tail 50
docker logs raglite-postgresql-test --tail 50
```

### UV Cache Corruption

If dependency installation fails with extraction errors:
```bash
rm -rf ~/.cache/uv
```

## Maintenance

When adding new test variants:

1. Add port assignments to `container-config.sh`
2. Test locally with `start-test-containers.sh <variant>`
3. Update this README with the new variant
