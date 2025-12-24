#!/usr/bin/env bash
# Cleanup Test Containers - Nuclear cleanup for CI test infrastructure
# Removes containers, networks, volumes safely with production protection
#
# Usage: cleanup-test-containers.sh VARIANT [OPTIONS]
# VARIANT: test | agentic | discovery | burnin | all
# OPTIONS: --force | --preserve-storage
# Exit codes: 0=success, 1=invalid args, 2=production protection triggered

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
FORCE=false
PRESERVE_STORAGE=false

# Production container names (NEVER cleaned by this script)
PRODUCTION_CONTAINERS=("raglite-qdrant" "raglite-postgresql")

# ============================================================
# Argument Parsing
# ============================================================

if [[ $# -lt 1 ]]; then
    cat <<'USAGE'
Usage: cleanup-test-containers.sh VARIANT [OPTIONS]

VARIANT (required):
  test       - Clean test containers only
  agentic    - Clean agentic containers only
  discovery  - Clean discovery containers only
  burnin     - Clean burnin containers only
  all        - Clean ALL test containers (recommended for CI)

OPTIONS:
  --force              Force cleanup even if containers are running critical tasks
  --preserve-storage   Keep storage directories (faster for local dev)

PRODUCTION PROTECTION:
  This script will NEVER touch production containers:
    - raglite-qdrant
    - raglite-postgresql

  Only removes containers with CI suffixes: -test, -agentic, -discovery, -burnin

EXIT CODES:
  0 - Success
  1 - Invalid arguments
  2 - Production protection triggered (attempted to clean production)

EXAMPLES:
  # Clean test variant containers
  ./cleanup-test-containers.sh test

  # Clean all test containers (recommended for CI)
  ./cleanup-test-containers.sh all

  # Clean but preserve storage for faster restart
  ./cleanup-test-containers.sh test --preserve-storage

  # Force cleanup
  ./cleanup-test-containers.sh all --force

USAGE
    exit 1
fi

VARIANT="$1"
shift

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)
            FORCE=true
            shift
            ;;
        --preserve-storage)
            PRESERVE_STORAGE=true
            shift
            ;;
        *)
            echo "❌ Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Determine which variants to clean
VARIANTS_TO_CLEAN=()

if [[ "$VARIANT" == "all" ]]; then
    VARIANTS_TO_CLEAN=("test" "agentic" "discovery" "burnin")
    echo "============================================================"
    echo "Nuclear Cleanup: ALL Test Containers"
    echo "============================================================"
else
    # Validate single variant
    if ! validate_variant "$VARIANT"; then
        exit 1
    fi
    VARIANTS_TO_CLEAN=("$VARIANT")
    echo "============================================================"
    echo "Cleanup: $VARIANT variant"
    echo "============================================================"
fi

echo "Variants to clean: ${VARIANTS_TO_CLEAN[*]}"
echo ""

# ============================================================
# Production Protection Check
# ============================================================

check_production_safety() {
    local container_name="$1"

    for prod_container in "${PRODUCTION_CONTAINERS[@]}"; do
        if [[ "$container_name" == "$prod_container" ]]; then
            echo "❌ CRITICAL: Attempted to clean PRODUCTION container: $container_name" >&2
            echo "   Production containers are NEVER cleaned by this script!" >&2
            echo "   If you need to clean production, use manual docker commands." >&2
            return 1
        fi
    done

    return 0
}

# ============================================================
# Cleanup Functions
# ============================================================

cleanup_container() {
    local container_name="$1"

    # Production protection
    if ! check_production_safety "$container_name"; then
        exit 2
    fi

    if docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        echo "  🧹 Stopping and removing: $container_name"
        docker stop "$container_name" 2>/dev/null || true
        docker rm -f "$container_name" 2>/dev/null || true
    else
        echo "  ℹ️  Container not found: $container_name (already clean)"
    fi
}

cleanup_network() {
    local network_name="$1"

    if docker network ls --format '{{.Name}}' | grep -q "^${network_name}$"; then
        echo "  🧹 Removing network: $network_name"
        docker network rm "$network_name" 2>/dev/null || true
    fi
}

cleanup_volume() {
    local volume_name="$1"

    if docker volume ls --format '{{.Name}}' | grep -q "^${volume_name}$"; then
        echo "  🧹 Removing volume: $volume_name"
        docker volume rm "$volume_name" 2>/dev/null || true
    fi
}

cleanup_storage_dir() {
    local dir_name="$1"

    if [[ -d "$dir_name" ]]; then
        echo "  🧹 Removing storage directory: $dir_name"
        rm -rf "$dir_name"
    fi
}

kill_process_on_port() {
    local port="$1"

    if is_port_in_use "$port"; then
        echo "  🧹 Killing process on port $port"
        lsof -ti :${port} | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# ============================================================
# 8-Step Nuclear Cleanup Process
# ============================================================

perform_cleanup() {
    local variant="$1"

    echo "------------------------------------------------------------"
    echo "Cleaning variant: $variant"
    echo "------------------------------------------------------------"

    local qdrant_container=$(get_qdrant_container_name "$variant")
    local postgres_container=$(get_postgres_container_name "$variant")
    local qdrant_port=$(get_qdrant_port "$variant")
    local postgres_port=$(get_postgres_port "$variant")

    # Step 1: Stop and remove containers
    echo "[1/8] Stopping and removing containers..."
    cleanup_container "$qdrant_container"
    cleanup_container "$postgres_container"

    # Step 2: Remove Docker Compose containers with labels
    echo "[2/8] Removing Docker Compose labeled containers..."
    docker ps -a --filter "label=com.raglite.variant=${variant}" --format '{{.Names}}' | while read container; do
        if [[ -n "$container" ]]; then
            echo "  🧹 Removing labeled container: $container"
            check_production_safety "$container" || exit 2
            docker rm -f "$container" 2>/dev/null || true
        fi
    done

    # Step 3: Remove networks
    echo "[3/8] Removing networks..."
    cleanup_network "raglite-network-${variant}"

    # Step 4: Remove volumes
    echo "[4/8] Removing volumes..."
    cleanup_volume "raglite-qdrant-data-${variant}"
    cleanup_volume "raglite-postgresql-data-${variant}"

    # Step 5: Remove storage directories
    if [[ "$PRESERVE_STORAGE" == "false" ]]; then
        echo "[5/8] Removing storage directories..."
        cleanup_storage_dir "qdrant_storage_${variant}"
        cleanup_storage_dir "postgresql_data_${variant}"
    else
        echo "[5/8] Preserving storage directories (--preserve-storage)"
    fi

    # Step 6: Kill processes on ports (macOS compatible)
    echo "[6/8] Killing processes on ports..."
    kill_process_on_port "$qdrant_port"
    kill_process_on_port "$postgres_port"

    # Step 7: Remove orphaned containers
    echo "[7/8] Removing orphaned containers..."
    docker container prune -f --filter "label=com.raglite.type=test" >/dev/null 2>&1 || true

    # Step 8: Clean up dangling resources
    echo "[8/8] Cleaning dangling resources..."
    docker network prune -f --filter "label=com.raglite.type=test" >/dev/null 2>&1 || true

    echo "✅ Cleanup complete for variant: $variant"
    echo ""
}

# ============================================================
# Main Execution
# ============================================================

# Perform cleanup for each variant
for variant in "${VARIANTS_TO_CLEAN[@]}"; do
    perform_cleanup "$variant"
done

# ============================================================
# Final Verification
# ============================================================

echo "============================================================"
echo "Final Verification"
echo "============================================================"

# Check for any remaining test containers
remaining_containers=$(docker ps -a --filter "label=com.raglite.type=test" --format '{{.Names}}' | wc -l | tr -d ' ')

if [[ "$remaining_containers" -gt 0 ]]; then
    echo "⚠️  Warning: ${remaining_containers} test container(s) still exist:"
    docker ps -a --filter "label=com.raglite.type=test" --format '  - {{.Names}} ({{.Status}})'
else
    echo "✅ All test containers removed"
fi

# Verify production containers were never touched
echo ""
echo "Production Safety Check:"
for prod_container in "${PRODUCTION_CONTAINERS[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${prod_container}$"; then
        echo "  ✅ Production container preserved: $prod_container"
    else
        echo "  ℹ️  Production container not present: $prod_container"
    fi
done

echo ""
echo "============================================================"
echo "✅ Cleanup Complete"
echo "============================================================"

exit 0
