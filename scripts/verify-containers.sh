#!/bin/bash
# Verify Docker container volume mounts are correct for local development
# Run this when databases appear empty despite having data on disk

set -e

EXPECTED_PATH="$(cd "$(dirname "$0")/.." && pwd)"
QDRANT_CONTAINER="raglite-qdrant"
POSTGRES_CONTAINER="raglite-postgresql"

echo "=== Container Volume Mount Verification ==="
echo "Expected base path: $EXPECTED_PATH"
echo ""

check_container() {
    local container=$1
    local expected_subpath=$2

    if ! docker ps -q -f name="^${container}$" | grep -q .; then
        echo "⚠️  Container '$container' is not running"
        return 1
    fi

    local mount_source=$(docker inspect "$container" --format='{{range .Mounts}}{{.Source}}{{end}}' 2>/dev/null)

    if [[ "$mount_source" == *"$EXPECTED_PATH"* ]]; then
        echo "✅ $container: Mount is correct"
        echo "   Path: $mount_source"
        return 0
    else
        echo "❌ $container: WRONG MOUNT!"
        echo "   Current: $mount_source"
        echo "   Expected: $EXPECTED_PATH/$expected_subpath"
        echo ""
        echo "   FIX: Run these commands:"
        echo "   docker stop $container && docker rm $container"
        echo "   docker-compose up -d ${container#raglite-}"
        return 1
    fi
}

echo "Checking containers..."
echo ""

ERRORS=0
check_container "$QDRANT_CONTAINER" "qdrant_storage" || ((ERRORS++))
check_container "$POSTGRES_CONTAINER" "postgresql_data" || ((ERRORS++))

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ All container mounts are correct!"
else
    echo "❌ $ERRORS container(s) have incorrect mounts"
    echo ""
    echo "Quick fix for all containers:"
    echo "  docker-compose down && docker-compose up -d"
    exit 1
fi
