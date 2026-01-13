#!/usr/bin/env bash
# Start Test Containers - Parameterized CI Container Startup
# Replaces ~540 lines of duplication across 6 CI jobs
#
# Usage: start-test-containers.sh VARIANT [OPTIONS]
# VARIANT: test | agentic | discovery | burnin
# OPTIONS: --qdrant-only | --postgresql-only | --skip-cleanup
# Exit codes: 0=success, 1=invalid args, 2=docker unavailable, 3-4=startup failed

set -euo pipefail

# ============================================================
# Configuration
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Temporarily disable nounset for sourcing (arrays with 'test' key trigger false positive)
set +u
source "${SCRIPT_DIR}/container-config.sh"
set -u

# Command line options
SKIP_CLEANUP=false
QDRANT_ONLY=false
POSTGRESQL_ONLY=false

# ============================================================
# Argument Parsing
# ============================================================

if [[ $# -lt 1 ]]; then
    cat <<'USAGE'
Usage: start-test-containers.sh VARIANT [OPTIONS]

VARIANT (required):
  test       - Unit/integration tests (ports 6335/5433)
  agentic    - Agentic workflow tests (ports 6337/5438)
  discovery  - Discovery tests (ports 6339/5434)
  burnin     - Burn-in tests (ports 6340/5435)

OPTIONS:
  --qdrant-only       Start only Qdrant container
  --postgresql-only   Start only PostgreSQL container
  --skip-cleanup      Skip nuclear cleanup step

EXIT CODES:
  0 - Success
  1 - Invalid arguments
  2 - Docker unavailable
  3 - Qdrant startup failed
  4 - PostgreSQL startup failed

EXAMPLES:
  # Start all containers for test variant
  ./start-test-containers.sh test

  # Start only Qdrant for agentic variant
  ./start-test-containers.sh agentic --qdrant-only

  # Start without cleanup (faster for local testing)
  ./start-test-containers.sh test --skip-cleanup

USAGE
    exit 1
fi

VARIANT="$1"
shift

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-cleanup)
            SKIP_CLEANUP=true
            shift
            ;;
        --qdrant-only)
            QDRANT_ONLY=true
            shift
            ;;
        --postgresql-only)
            POSTGRESQL_ONLY=true
            shift
            ;;
        *)
            echo "❌ Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Validate variant
if ! validate_variant "$VARIANT"; then
    exit 1
fi

# Get configuration
QDRANT_PORT=$(get_qdrant_port "$VARIANT")
POSTGRES_PORT=$(get_postgres_port "$VARIANT")
QDRANT_CONTAINER=$(get_qdrant_container_name "$VARIANT")
POSTGRES_CONTAINER=$(get_postgres_container_name "$VARIANT")

echo "============================================================"
echo "Starting CI Containers: $VARIANT"
echo "============================================================"
echo "Qdrant:     $QDRANT_CONTAINER (port $QDRANT_PORT)"
echo "PostgreSQL: $POSTGRES_CONTAINER (port $POSTGRES_PORT)"
echo ""

# ============================================================
# Docker Availability Check
# ============================================================

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found in PATH" >&2
    exit 2
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker daemon not running" >&2
    exit 2
fi

# ============================================================
# Nuclear Cleanup
# ============================================================

cleanup_container() {
    local container_name="$1"

    if docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        echo "🧹 Removing existing container: $container_name"
        docker stop "$container_name" 2>/dev/null || true
        docker rm -f "$container_name" 2>/dev/null || true
    fi
}

if [[ "$SKIP_CLEANUP" == "false" ]]; then
    echo "------------------------------------------------------------"
    echo "[1/4] Nuclear Cleanup"
    echo "------------------------------------------------------------"

    if [[ "$POSTGRESQL_ONLY" == "false" ]]; then
        cleanup_container "$QDRANT_CONTAINER"
    fi

    if [[ "$QDRANT_ONLY" == "false" ]]; then
        cleanup_container "$POSTGRES_CONTAINER"
    fi

    # Kill processes on ports (macOS compatible)
    if [[ "$POSTGRESQL_ONLY" == "false" ]] && is_port_in_use "$QDRANT_PORT"; then
        echo "⚠️  Port $QDRANT_PORT in use, attempting to free..."
        lsof -ti :${QDRANT_PORT} | xargs kill -9 2>/dev/null || true
        sleep 1
    fi

    if [[ "$QDRANT_ONLY" == "false" ]] && is_port_in_use "$POSTGRES_PORT"; then
        echo "⚠️  Port $POSTGRES_PORT in use, attempting to free..."
        lsof -ti :${POSTGRES_PORT} | xargs kill -9 2>/dev/null || true
        sleep 1
    fi

    echo "✅ Cleanup complete"
fi

# ============================================================
# Start Qdrant
# ============================================================

start_qdrant() {
    echo "------------------------------------------------------------"
    echo "[2/4] Starting Qdrant Container"
    echo "------------------------------------------------------------"

    # Create storage directory
    local storage_dir="qdrant_storage_${VARIANT}"
    mkdir -p "$storage_dir"

    # Start container (raw docker run - bypass Compose corruption)
    # --pull=never: Images should be pre-pulled by docker-setup job to avoid keychain issues
    docker run -d \
        --pull=never \
        --name "$QDRANT_CONTAINER" \
        --label "com.raglite.variant=${VARIANT}" \
        --label "com.raglite.type=test" \
        -p "${QDRANT_PORT}:6333" \
        -p "$((QDRANT_PORT + 1)):6334" \
        -v "$(pwd)/${storage_dir}:/qdrant/storage" \
        --memory="${QDRANT_MEMORY}" \
        --cpus="${QDRANT_CPU_LIMIT}" \
        qdrant/qdrant:v1.15.0 > /dev/null

    # Health check with exponential backoff
    local attempt=1
    local wait_time=$HEALTH_CHECK_INTERVAL
    local max_wait=$QDRANT_READY_TIMEOUT
    local elapsed=0

    echo -n "⏳ Waiting for Qdrant to be ready"
    while [[ $elapsed -lt $max_wait ]]; do
        if curl -sf http://localhost:${QDRANT_PORT}/healthz > /dev/null 2>&1; then
            echo ""
            echo "✅ Qdrant ready (${elapsed}s)"
            return 0
        fi

        echo -n "."
        sleep "$wait_time"
        elapsed=$((elapsed + wait_time))
        wait_time=$(echo "$wait_time * $BACKOFF_MULTIPLIER" | bc | cut -d'.' -f1)
        ((attempt++))
    done

    echo ""
    echo "❌ Qdrant failed to start within ${max_wait}s" >&2
    docker logs "$QDRANT_CONTAINER" 2>&1 | tail -20
    return 1
}

# ============================================================
# Start PostgreSQL
# ============================================================

start_postgresql() {
    echo "------------------------------------------------------------"
    echo "[3/4] Starting PostgreSQL Container"
    echo "------------------------------------------------------------"

    # Create storage directory
    local storage_dir="postgresql_data_${VARIANT}"
    mkdir -p "$storage_dir"

    # Use consistent test credentials from centralized config
    # SINGLE SOURCE OF TRUTH: scripts/ci/container-config.sh
    local db_user="$CI_POSTGRES_USER"
    local db_password="$CI_POSTGRES_PASSWORD"
    local db_name="$CI_POSTGRES_DB"

    # Start container
    # --pull=never: Images should be pre-pulled by docker-setup job to avoid keychain issues
    docker run -d \
        --pull=never \
        --name "$POSTGRES_CONTAINER" \
        --label "com.raglite.variant=${VARIANT}" \
        --label "com.raglite.type=test" \
        -p "${POSTGRES_PORT}:5432" \
        -e POSTGRES_USER="${db_user}" \
        -e POSTGRES_PASSWORD="${db_password}" \
        -e POSTGRES_DB="${db_name}" \
        -v "$(pwd)/${storage_dir}:/var/lib/postgresql/data" \
        --memory="${POSTGRES_MEMORY}" \
        --shm-size="${POSTGRES_SHM}" \
        --cpus="${POSTGRES_CPU_LIMIT}" \
        postgres:16 > /dev/null

    # Health check with exponential backoff (using pg_isready)
    # ENHANCED: Add Docker daemon heartbeat every 10s during startup
    local attempt=1
    local wait_time=$HEALTH_CHECK_INTERVAL
    local max_wait=$POSTGRES_READY_TIMEOUT
    local elapsed=0
    local last_heartbeat=0

    echo -n "⏳ Waiting for PostgreSQL to be ready"
    while [[ $elapsed -lt $max_wait ]]; do
        # Check PostgreSQL health
        if docker exec "$POSTGRES_CONTAINER" pg_isready -U "${db_user}" > /dev/null 2>&1; then
            echo ""
            echo "✅ PostgreSQL ready (${elapsed}s)"
            return 0
        fi

        # Docker daemon heartbeat every 10s during startup
        if [[ $((elapsed - last_heartbeat)) -ge 10 ]]; then
            if ! timeout 5 docker info &> /dev/null; then
                echo ""
                echo "❌ Docker daemon became unresponsive during PostgreSQL startup" >&2
                echo "   Elapsed time: ${elapsed}s" >&2
                echo "   This indicates Colima VM entered zombie state during container operations" >&2
                echo "   Root cause: VM memory pressure or network degradation" >&2
                return 1
            fi
            last_heartbeat=$elapsed
        fi

        echo -n "."
        sleep "$wait_time"
        elapsed=$((elapsed + wait_time))
        wait_time=$(echo "$wait_time * $BACKOFF_MULTIPLIER" | bc | cut -d'.' -f1)
        ((attempt++))
    done

    echo ""
    echo "❌ PostgreSQL failed to start within ${max_wait}s" >&2
    docker logs "$POSTGRES_CONTAINER" 2>&1 | tail -20
    return 1
}

# ============================================================
# Main Execution
# ============================================================

if [[ "$POSTGRESQL_ONLY" == "false" ]]; then
    if ! start_qdrant; then
        echo "❌ Failed to start Qdrant" >&2
        exit 3
    fi
fi

if [[ "$QDRANT_ONLY" == "false" ]]; then
    if ! start_postgresql; then
        echo "❌ Failed to start PostgreSQL" >&2
        exit 4
    fi
fi

# ============================================================
# Export Environment
# ============================================================

echo "------------------------------------------------------------"
echo "[4/4] Exporting Environment"
echo "------------------------------------------------------------"

export_variant_ports "$VARIANT" ".ci-env"

# Set APP_ENV for test isolation
echo "export APP_ENV=test" >> .ci-env

echo ""
echo "============================================================"
echo "✅ Containers Started Successfully"
echo "============================================================"
echo "Source environment: source .ci-env"
echo ""
echo "Container Status:"
if [[ "$POSTGRESQL_ONLY" == "false" ]]; then
    docker ps --filter "name=$QDRANT_CONTAINER" --format "  {{.Names}}: {{.Status}}"
fi
if [[ "$QDRANT_ONLY" == "false" ]]; then
    docker ps --filter "name=$POSTGRES_CONTAINER" --format "  {{.Names}}: {{.Status}}"
fi
echo ""

exit 0
